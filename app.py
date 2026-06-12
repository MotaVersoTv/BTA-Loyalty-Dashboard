# BTA Loyalty Dashboard
# Interactive Streamlit dashboard for the BTA points / rewards dataset.
# Data: dim_users (main) + mart_user_rewards (activity dates for the trend).

import re
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import streamlit as st

# ----------------------------------------------------------------------
# Page config
# ----------------------------------------------------------------------
st.set_page_config(page_title="BTA Loyalty Dashboard", layout="wide")

# ----------------------------------------------------------------------
# Theme (dark) — colors used across the page
# ----------------------------------------------------------------------
BG     = "#0b1020"   # page background
PANEL  = "#161d2e"   # cards / chart background
FG     = "#e5e7eb"   # main text
MUTED  = "#94a3b8"   # secondary text
GRID   = "#2a3350"   # grid lines

# accent colors, one per KPI card (like the reference dashboard)
ACCENTS = ["#22d3ee", "#34d399", "#a78bfa", "#fbbf24", "#f472b6"]

# Custom CSS to get the dark look
st.markdown(
    f"""
    <style>
    .stApp {{ background-color: {BG}; color: {FG}; }}
    section[data-testid="stSidebar"] {{ background-color: {PANEL}; }}
    h1, h2, h3, h4 {{ color: {FG}; }}

    .kpi-card {{
        background-color: {PANEL};
        border: 1px solid {GRID};
        border-radius: 12px;
        padding: 18px 16px;
        text-align: center;
    }}
    .kpi-value {{ font-size: 30px; font-weight: 700; }}
    .kpi-label {{ font-size: 12px; color: {MUTED};
                  text-transform: uppercase; letter-spacing: 1px; margin-top: 4px; }}

    .stTabs [data-baseweb="tab-list"] {{ gap: 6px; }}
    .stTabs [data-baseweb="tab"] {{ color: {MUTED}; }}
    </style>
    """,
    unsafe_allow_html=True,
)


# ----------------------------------------------------------------------
# Data loading and cleaning
# ----------------------------------------------------------------------
REWARD_SLUGS = [
    "gift_cards", "event_tickets", "travel_giveaways", "product_samples",
    "tech_gear", "cannabis_accessories", "make_a_suggestion", "none",
]


def parse_rewards(value):
    # The column stores rewards either as PHP serialized text or as a JSON list.
    # In both cases the slugs appear inside quotes, so we just pull those out.
    if pd.isna(value):
        return []
    tokens = re.findall(r'"([a-z_]+)"', str(value))
    return [t for t in tokens if t in REWARD_SLUGS]


def clean_gender(value):
    if pd.isna(value):
        return "Undisclosed"
    s = str(value).strip().lower()
    if "female" in s:
        return "Female"
    if "male" in s:
        return "Male"
    return "Other"


@st.cache_data
def load_data():
    df = pd.read_csv("dim_users_202605121902.csv")

    # Points columns to numbers
    df["lifetime_points_earned"] = pd.to_numeric(df["lifetime_points_earned"], errors="coerce")
    df["current_points_balance"] = pd.to_numeric(df["current_points_balance"], errors="coerce")

    # Clean the corrupt outlier: cap at the 99th percentile (same as the notebook)
    cap = df["lifetime_points_earned"].quantile(0.99)
    df["earned_clean"]  = df["lifetime_points_earned"].clip(upper=cap)
    df["balance_clean"] = df["current_points_balance"].clip(lower=0, upper=cap)
    df["points_spent"]  = df["earned_clean"] - df["balance_clean"]
    df["utilization"]   = np.where(df["earned_clean"] > 0,
                                   df["points_spent"] / df["earned_clean"], np.nan)

    # Age groups
    bins   = [17, 24, 34, 44, 54, 200]
    labels = ["18-24", "25-34", "35-44", "45-54", "55+"]
    df["age_group"] = pd.cut(df["age_years"], bins=bins, labels=labels)

    # Gender cleanup (the raw column is very messy)
    df["gender_clean"] = df["gender"].apply(clean_gender)

    # Rewards: keep a parsed list for counting later
    df["rewards_list"] = df["preferred_rewards"].apply(parse_rewards)

    # Bring in the activity date from the rewards mart (for the trend over time)
    mart = pd.read_csv("mart_user_rewards_202605121902.csv")[["user_id", "first_activity"]]
    df = df.merge(mart, left_on="wp_user_id", right_on="user_id", how="left")
    df["first_activity"] = pd.to_datetime(df["first_activity"], errors="coerce", utc=True)

    return df


# ----------------------------------------------------------------------
# Chart helpers (dark styled)
# ----------------------------------------------------------------------
def new_fig(width=7, height=4):
    fig, ax = plt.subplots(figsize=(width, height))
    fig.patch.set_facecolor(PANEL)
    ax.set_facecolor(PANEL)
    ax.tick_params(colors=FG, labelsize=9)
    for spine in ax.spines.values():
        spine.set_color(GRID)
    ax.xaxis.label.set_color(FG)
    ax.yaxis.label.set_color(FG)
    ax.title.set_color(FG)
    ax.grid(True, color=GRID, alpha=0.4)
    return fig, ax


def chart_trend_over_time(df):
    fig, ax = new_fig()
    ts = df.dropna(subset=["first_activity"]).copy()
    if len(ts) == 0:
        ax.text(0.5, 0.5, "No activity dates for this selection",
                ha="center", va="center", color=MUTED, transform=ax.transAxes)
        return fig
    # Drop the timezone before grouping by month (we only need the month)
    ts["month"] = ts["first_activity"].dt.tz_localize(None).dt.to_period("M").dt.to_timestamp()
    monthly = ts.groupby("month").size()
    ax.plot(monthly.index, monthly.values, marker="o", color=ACCENTS[0], linewidth=2)
    ax.fill_between(monthly.index, monthly.values, color=ACCENTS[0], alpha=0.15)
    ax.set_title("New active users over time")
    ax.set_xlabel("Month")
    ax.set_ylabel("Users")
    fig.autofmt_xdate()
    return fig


def chart_points_distribution(df):
    fig, ax = new_fig()
    # Exclude the extreme values so the real shape is visible
    data = df[df["earned_clean"] <= 200_000]["earned_clean"]
    ax.hist(data, bins=40, color=ACCENTS[0], edgecolor=PANEL)
    ax.set_title("Points earned distribution")
    ax.set_xlabel("Points earned")
    ax.set_ylabel("Number of users")
    return fig


def chart_users_by_role(df):
    fig, ax = new_fig()
    counts = df["bta_user_role"].value_counts()
    ax.bar(counts.index.astype(str), counts.values, color=ACCENTS[2])
    ax.set_title("Users by role")
    ax.set_xlabel("Role")
    ax.set_ylabel("Number of users")
    return fig


def chart_users_by_province(df):
    fig, ax = new_fig()
    counts = df["province"].value_counts().head(10).sort_values()
    ax.barh(counts.index.astype(str), counts.values, color=ACCENTS[1])
    ax.set_title("Top provinces by number of users")
    ax.set_xlabel("Number of users")
    return fig


def chart_points_by_province(df):
    fig, ax = new_fig()
    top = df["province"].value_counts().head(10).index
    avg = (df[df["province"].isin(top)]
           .groupby("province")["earned_clean"].mean()
           .sort_values())
    ax.barh(avg.index.astype(str), avg.values, color=ACCENTS[3])
    ax.set_title("Average points earned by province")
    ax.set_xlabel("Average points earned")
    return fig


def chart_utilization_by_age(df):
    fig, ax = new_fig()
    util = df.groupby("age_group", observed=True)["utilization"].mean() * 100
    ax.bar(util.index.astype(str), util.values, color=ACCENTS[2])
    for x, y in zip(range(len(util)), util.values):
        if not np.isnan(y):
            ax.text(x, y + 0.05, f"{y:.1f}%", ha="center", va="bottom",
                    color=FG, fontsize=9)
    ax.set_title("Average utilization rate by age group")
    ax.set_xlabel("Age group")
    ax.set_ylabel("Utilization (%)")
    return fig


def chart_users_by_gender(df):
    fig, ax = new_fig()
    counts = df["gender_clean"].value_counts()
    ax.bar(counts.index.astype(str), counts.values, color=ACCENTS[4])
    ax.set_title("Users by gender")
    ax.set_xlabel("Gender")
    ax.set_ylabel("Number of users")
    return fig


def chart_preferred_rewards(df):
    fig, ax = new_fig()
    # Flatten all the reward lists and count them
    all_rewards = [r for sub in df["rewards_list"] for r in sub]
    counts = pd.Series(all_rewards).value_counts()
    labels = [s.replace("_", " ").title() for s in counts.index]
    ax.barh(labels[::-1], counts.values[::-1], color=ACCENTS[0])
    ax.set_title("Preferred rewards (overall)")
    ax.set_xlabel("Number of users")
    return fig


def chart_consumption_method(df):
    fig, ax = new_fig()
    counts = df["preferred_consumption_method"].value_counts().head(8).sort_values()
    ax.barh(counts.index.astype(str), counts.values, color=ACCENTS[1])
    ax.set_title("Top preferred consumption methods")
    ax.set_xlabel("Number of users")
    return fig


# ----------------------------------------------------------------------
# App body
# ----------------------------------------------------------------------
df = load_data()

st.title("BTA Loyalty Dashboard")
st.caption("Interactive view of the BTA points and rewards program. "
           "Use the filters on the left to explore the data.")

# ---- Sidebar filters ----
st.sidebar.header("Filters")

roles = sorted(df["bta_user_role"].dropna().unique())
sel_roles = st.sidebar.multiselect("Role", roles)

provinces = sorted(df["province"].dropna().unique())
sel_prov = st.sidebar.multiselect("Province", provinces)

age_groups = ["18-24", "25-34", "35-44", "45-54", "55+"]
sel_age = st.sidebar.multiselect("Age group", age_groups)

freqs = sorted(df["consumption_frequency"].dropna().unique())
sel_freq = st.sidebar.multiselect("Consumption frequency", freqs)

st.sidebar.caption("Tip: leave a filter empty to include everything.")

# ---- Apply filters (empty selection = no filter) ----
fdf = df.copy()
if sel_roles:
    fdf = fdf[fdf["bta_user_role"].isin(sel_roles)]
if sel_prov:
    fdf = fdf[fdf["province"].isin(sel_prov)]
if sel_age:
    fdf = fdf[fdf["age_group"].isin(sel_age)]
if sel_freq:
    fdf = fdf[fdf["consumption_frequency"].isin(sel_freq)]

# ---- KPI cards ----
total_users  = len(fdf)
active_users = int((fdf["earned_clean"] > 0).sum())
avg_earned   = fdf["earned_clean"].mean() if total_users else 0
avg_util     = fdf["utilization"].mean() * 100 if total_users else 0
provinces_n  = fdf["province"].nunique()

kpis = [
    (f"{total_users:,}",          "Total users"),
    (f"{active_users:,}",         "Active users"),
    (f"{avg_earned:,.0f}",        "Avg points earned"),
    (f"{avg_util:.1f}%",          "Avg utilization"),
    (f"{provinces_n}",            "Provinces"),
]

st.subheader("Key performance indicators")
cols = st.columns(5)
for col, (value, label), accent in zip(cols, kpis, ACCENTS):
    col.markdown(
        f"""
        <div class="kpi-card">
            <div class="kpi-value" style="color:{accent}">{value}</div>
            <div class="kpi-label">{label}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

st.write("")

# ---- Tabs ----
tab_trends, tab_geo, tab_analysis, tab_table = st.tabs(
    ["Trends", "Geography", "Analysis", "Data table"]
)

with tab_trends:
    st.markdown("#### Content trends over time")
    st.pyplot(chart_trend_over_time(fdf))
    c1, c2 = st.columns(2)
    with c1:
        st.pyplot(chart_points_distribution(fdf))
    with c2:
        st.pyplot(chart_users_by_role(fdf))

with tab_geo:
    c1, c2 = st.columns(2)
    with c1:
        st.pyplot(chart_users_by_province(fdf))
    with c2:
        st.pyplot(chart_points_by_province(fdf))

with tab_analysis:
    c1, c2 = st.columns(2)
    with c1:
        st.pyplot(chart_utilization_by_age(fdf))
        st.pyplot(chart_preferred_rewards(fdf))
    with c2:
        st.pyplot(chart_users_by_gender(fdf))
        st.pyplot(chart_consumption_method(fdf))

with tab_table:
    st.markdown("#### Filtered users")
    show_cols = [
        "user_key", "bta_user_role", "province", "age_years", "age_group",
        "gender_clean", "earned_clean", "points_spent", "utilization",
        "consumption_frequency", "preferred_consumption_method",
    ]
    table = fdf[show_cols].rename(columns={
        "gender_clean": "gender",
        "earned_clean": "points_earned",
    })
    st.dataframe(table, use_container_width=True)

    csv = table.to_csv(index=False).encode("utf-8")
    st.download_button("Download CSV", csv, "bta_filtered_users.csv", "text/csv")

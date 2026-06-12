# BTA Loyalty Dashboard

Interactive dashboard built with [Streamlit](https://streamlit.io/) for the BTA
points / rewards dataset.

## Features

- Sidebar filters: **role**, **province**, **age group** and **consumption frequency**
- Five KPI cards that update with the filters (total users, active users,
  average points earned, average utilization, provinces)
- Four tabs:
  - **Trends** – new active users over time, points distribution, users by role
  - **Geography** – users and average points by province
  - **Analysis** – utilization by age, gender, preferred rewards, consumption method
  - **Data table** – filtered table with a CSV download button

## Files

```
.
├── app.py                              # Streamlit app
├── dim_users_202605121902.csv          # main dataset
├── mart_user_rewards_202605121902.csv  # activity dates (for the trend chart)
├── requirements.txt                    # dependencies
└── README.md
```

The two CSV files must be in the **same folder** as `app.py`.

## How to run

1. Install the dependencies:

   ```
   pip install -r requirements.txt
   ```

2. Run the app:

   ```
   python -m streamlit run app.py
   ```

   The dashboard opens in the browser at `http://localhost:8501`.

   > Note: run it with `streamlit`, not `python app.py`. Streamlit needs its
   > own runner to start the web server.

## Notes on the data

- Points are cleaned the same way as in the notebook: the corrupt outlier is
  capped at the 99th percentile and negative balances are set to 0.
- Utilization rate = points spent / points earned (only for users who earned points).
- The `gender` column is normalized (the raw values are inconsistent).
- `preferred_rewards` is stored as serialized text, so it is parsed into a list
  before counting.

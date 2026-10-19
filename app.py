import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt

# -------------------------- Page Setup --------------------------
st.set_page_config(page_title="WDW Operations Dashboard", layout="wide")

# Fix matplotlib rendering
plt.rcParams["axes.unicode_minus"] = False

# Dashboard identity (assignment requirement: team name + one-line purpose)
st.title("Walt Disney World Operations Dashboard | Team Group 2")
st.caption("For Park Operations Managers | Supports staffing adjustment, crowd diversion and ride scheduling decisions")

# -------------------------- Data Loader --------------------------
@st.cache_data(show_spinner=False)
def load_data():
    df = pd.read_csv("calendar_enriched.csv")
    df["date"] = pd.to_datetime(df["date"])
    
    # Operational flags
    df["is_high_crowd"] = df["crowd_level_pct"] > 70
    df["is_critical_crowd"] = df["crowd_level_pct"] > 85
    
    # Day type classification
    def get_day_type(row):
        if row["is_holiday"]:
            return "Holiday"
        elif row["has_special_event"]:
            return "Special Event"
        elif row["is_weekend"]:
            return "Weekend"
        else:
            return "Regular Day"
    df["day_type"] = df.apply(get_day_type, axis=1)
    
    return df

df = load_data()
date_min = df["date"].min()
date_max = df["date"].max()

# -------------------------- Sidebar Filters --------------------------
with st.sidebar:
    st.header("Filters")
    
    # 1. Date range
    date_range = st.date_input(
        "Select date range",
        value=(date_min, date_max),
        min_value=date_min,
        max_value=date_max
    )
    start_dt = pd.to_datetime(date_range[0])
    end_dt = pd.to_datetime(date_range[1])
    
    # 2. Park selector
    park_list = sorted(df["park_name"].unique())
    selected_park = st.selectbox("Select park", park_list)
    
    # 3. Day type filter
    day_type_options = ["All days", "Weekend only", "Holiday only", "Special event only"]
    selected_day_type = st.selectbox("Filter by day type", day_type_options)

# -------------------------- Data Filtering --------------------------
# Base filter
filtered = df[
    (df["date"] >= start_dt) &
    (df["date"] <= end_dt) &
    (df["park_name"] == selected_park)
].copy()

# Apply day type filter
if selected_day_type == "Weekend only":
    filtered = filtered[filtered["is_weekend"] == True]
elif selected_day_type == "Holiday only":
    filtered = filtered[filtered["is_holiday"] == True]
elif selected_day_type == "Special event only":
    filtered = filtered[filtered["has_special_event"] == True]

# Aggregate to daily level for trend and period comparison
daily = filtered.groupby("date")["crowd_level_pct"].mean().reset_index()
n_days = len(daily)

# Calculate prior equivalent period (robust, handles missing days gracefully)
prev_end = start_dt - pd.Timedelta(days=1)
prev_start = start_dt - pd.Timedelta(days=n_days)
prev_daily = df[
    (df["date"] >= prev_start) &
    (df["date"] <= prev_end) &
    (df["park_name"] == selected_park)
].groupby("date")["crowd_level_pct"].mean().reset_index()

# -------------------------- Core KPIs (max 3, per assignment rule) --------------------------
st.subheader("Key Operational Metrics")
col1, col2, col3 = st.columns(3)

# KPI 1: Average crowd level + period-over-period delta
avg_crowd = daily["crowd_level_pct"].mean()
if len(prev_daily) > 0:
    prev_avg = prev_daily["crowd_level_pct"].mean()
    crowd_delta = avg_crowd - prev_avg
    delta_text = f"{crowd_delta:+.1f} pp vs. prior period"
else:
    delta_text = "N/A (no prior data)"

with col1:
    st.metric(
        label="Average Crowd Level",
        value=f"{avg_crowd:.1f}%",
        delta=delta_text,
        delta_color="inverse"
    )

# KPI 2: High-crowd day share
high_share = (filtered["is_high_crowd"].mean()) * 100
with col2:
    st.metric(
        label="High Crowd Share (>70%)",
        value=f"{high_share:.1f}%",
        help="Share of days above the operational alert threshold"
    )

# KPI 3: Average operating hours
avg_op_hours = (filtered["operating_minutes"].mean()) / 60
with col3:
    st.metric(
        label="Avg Operating Hours",
        value=f"{avg_op_hours:.1f}h"
    )

# -------------------------- Operational Recommendation (assignment: if X then Y) --------------------------
st.subheader("Operational Recommendation")

if avg_crowd < 55:
    st.success("**Crowd level: Low** — Standard staffing is sufficient. No diversion measures required.")
elif avg_crowd < 70:
    st.info("**Crowd level: Moderate** — Add 10–15% roving staff to high-traffic zones. Monitor queue times at top attractions.")
elif avg_crowd < 85:
    st.warning("**Crowd level: High** — Activate the standard crowd diversion plan. Add extra FastPass distribution points and adjust parade timing to spread foot traffic.")
else:
    st.error("**Crowd level: Critical** — Call in emergency staffing. Activate maximum diversion protocols and extend operating hours if feasible.")

# -------------------------- Supporting Charts (1–2, per assignment rule) --------------------------
st.subheader("Crowd Pattern Analysis")

# Chart 1: Daily trend with action thresholds
fig1, ax1 = plt.subplots(figsize=(10, 3.5))
ax1.plot(daily["date"], daily["crowd_level_pct"], color="#003366", linewidth=2)
ax1.axhline(y=70, color="#c82423", linestyle="--", label="70% High Alert")
ax1.axhline(y=85, color="#8b0000", linestyle=":", label="85% Critical Threshold")
ax1.set_ylabel("Crowd Level (%)")
ax1.set_title(f"Daily Crowd Trend — {selected_park}")
ax1.legend(loc="upper left")
ax1.grid(alpha=0.3)
st.pyplot(fig1)

# Chart 2: Day-of-week pattern
dow_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
dow_crowd = filtered.groupby("day_of_week")["crowd_level_pct"].mean().reindex(dow_order)

fig2, ax2 = plt.subplots(figsize=(10, 3.5))
bars = ax2.bar(dow_crowd.index, dow_crowd.values, color="#3b82f6")
ax2.axhline(y=70, color="#c82423", linestyle="--", label="High Alert Threshold")
ax2.set_ylabel("Average Crowd Level (%)")
ax2.set_title("Crowd Level by Day of Week")
ax2.bar_label(bars, fmt="%.1f%%", padding=3)
ax2.legend()
st.pyplot(fig2)

# -------------------------- Data Notes (Step 3 & Step 4 requirements) --------------------------
with st.expander("Data Notes & Production Refresh Plan"):
    st.markdown("""
    **Data Source**: Kaggle — Walt Disney World Wait Times and Crowd Calendar  
    **Coverage**: All 4 WDW theme parks, daily records from 2015 to 2026

    **What we removed, and why**:
    - Ride-level wait times: removed. Operations managers making staffing decisions do not need per-ride data at the top level. Granular ride data is for on-site team leads, not central operations.
    - Weather fields: removed. Weather correlates with crowd but does not directly drive staffing decisions. Adding it would add visual noise without improving operational decisions.

    **Production Refresh Schedule**:
    - Park-level crowd data: refreshed every 1 hour during operating hours. This matches the staffing decision cycle; real-time refresh would add cost without changing decisions.
    - Holiday and event calendar: updated weekly, every Monday.
    - Ride-level wait times: refreshed every 15 minutes for on-site teams (separate dashboard).

    **Action Triggers**:
    - Crowd level above 70%: activate standard crowd diversion plan
    - Crowd level above 85%: trigger emergency staffing and protocol escalation

    **Limitations**:
    - Crowd level is an estimated occupancy rate, not an exact visitor headcount
    - Temporary ride closures and extreme weather events are not fully reflected in this dataset
    - This is a historical snapshot dataset; production deployment would connect to live park systems
    """)

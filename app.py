import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt

# -------------------------- Page Configuration --------------------------
st.set_page_config(page_title="WDW Operations Dashboard", layout="wide")

# Fix matplotlib rendering compatibility
plt.rcParams["axes.unicode_minus"] = False

# Dashboard header
st.title("Walt Disney World Operations Dashboard | Team Group 2")
st.caption("Built for Park Operations Managers | Supports staffing, scheduling and crowd diversion decisions")

# -------------------------- Data Loading --------------------------
@st.cache_data(show_spinner=False)
def load_and_clean_data():
    """Load WDW crowd calendar data and derive operational fields"""
    df = pd.read_csv("calendar_enriched.csv")
    
    # Standardize date format
    df["date"] = pd.to_datetime(df["date"])
    
    # Flag high-crowd days (70% = operational alert threshold)
    df["is_high_crowd"] = df["crowd_level_pct"] > 70
    
    # Categorize day type for filtering
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
    
    date_min = df["date"].min()
    date_max = df["date"].max()
    
    return df, date_min, date_max

# Load dataset
df, date_min, date_max = load_and_clean_data()

# -------------------------- Sidebar Filters --------------------------
with st.sidebar:
    st.header("Filters")
    
    # 1. Date range selector
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
# Base filter: date range + selected park
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

# -------------------------- Core KPIs --------------------------
st.subheader("Key Operational Metrics")
col1, col2, col3 = st.columns(3)

# KPI 1: Average crowd level
avg_crowd = filtered["crowd_level_pct"].mean()
with col1:
    st.metric(
        label="Average Crowd Level",
        value=f"{avg_crowd:.1f}%",
        help="Average daily occupancy rate for the selected period"
    )

# KPI 2: Count of high-crowd days
high_crowd_count = int(filtered["is_high_crowd"].sum())
with col2:
    st.metric(
        label="High Crowd Days",
        value=high_crowd_count,
        help="Number of days with crowd level above the 70% operational threshold"
    )

# KPI 3: Average operating hours
avg_op_hours = (filtered["operating_minutes"].mean()) / 60
with col3:
    st.metric(
        label="Avg Operating Hours",
        value=f"{avg_op_hours:.1f}h",
        help="Average daily park operating hours"
    )

# -------------------------- Supporting Charts --------------------------
st.subheader("Crowd Pattern Analysis")

# Chart 1: Daily crowd level trend
daily_crowd = filtered.groupby("date")["crowd_level_pct"].mean().reset_index()

fig1, ax1 = plt.subplots(figsize=(10, 3.5))
ax1.plot(daily_crowd["date"], daily_crowd["crowd_level_pct"], color="#003366", linewidth=2)
ax1.axhline(y=70, color="#c82423", linestyle="--", label="70% Alert Threshold")
ax1.set_ylabel("Crowd Level (%)")
ax1.set_title(f"Daily Crowd Trend - {selected_park}")
ax1.legend()
ax1.grid(alpha=0.3)
st.pyplot(fig1)

# Chart 2: Crowd level by day of week
dow_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
dow_crowd = filtered.groupby("day_of_week")["crowd_level_pct"].mean().reindex(dow_order)

fig2, ax2 = plt.subplots(figsize=(10, 3.5))
bars = ax2.bar(dow_crowd.index, dow_crowd.values, color="#3b82f6")
ax2.axhline(y=70, color="#c82423", linestyle="--")
ax2.set_ylabel("Average Crowd Level (%)")
ax2.set_title("Crowd Level by Day of Week")
ax2.bar_label(bars, fmt="%.1f%%", padding=3)
st.pyplot(fig2)

# -------------------------- Data Notes --------------------------
with st.expander("Data Notes & Production Refresh Plan"):
    st.markdown("""
    **Data Source**: Kaggle - Walt Disney World Wait Times and Crowd Calendar  
    **Coverage**: All 4 WDW theme parks, daily records from 2015 to 2026

    **Production Refresh Schedule**:
    - Park-level crowd data: refreshed every 1 hour during operating hours
    - Holiday and event calendar: updated weekly, every Monday
    - Ride-level wait times: refreshed every 15 minutes for on-site teams

    **Limitations**:
    - Crowd level is an estimated occupancy rate, not exact visitor headcount
    - Temporary ride closures and extreme weather events are not fully reflected in this dataset
    - This is a historical snapshot dataset; production deployment would connect to live park systems
    """)

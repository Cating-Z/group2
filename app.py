import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt

# -------------------------- Page Configuration --------------------------
st.set_page_config(page_title="WDW Operations Dashboard", layout="wide")

# Fix matplotlib rendering compatibility
plt.rcParams["axes.unicode_minus"] = False

# Dashboard header
st.title("Walt Disney World Operations Dashboard | Team Group 2")
st.caption("For Park Operations Managers | Data-driven staffing, crowd diversion and ride scheduling decisions")

# -------------------------- Data Loading & Enrichment --------------------------
@st.cache_data(show_spinner=False)
def load_and_enrich_data():
    """Load crowd calendar data and derive operational fields for decision support"""
    df = pd.read_csv("calendar_enriched.csv")
    
    # Standardize date format
    df["date"] = pd.to_datetime(df["date"])
    
    # Operational flags
    df["is_high_crowd"] = df["crowd_level_pct"] > 70
    df["is_critical_crowd"] = df["crowd_level_pct"] > 85
    
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
df, date_min, date_max = load_and_enrich_data()

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

# Calculate prior period values for week-over-week comparison
prev_end = start_dt - pd.Timedelta(days=1)
prev_start = prev_end - pd.Timedelta(days=len(filtered)-1)
prev_filtered = df[
    (df["date"] >= prev_start) &
    (df["date"] <= prev_end) &
    (df["park_name"] == selected_park)
]

# -------------------------- Core Operational KPIs --------------------------
st.subheader("Key Operational Metrics")
col1, col2, col3 = st.columns(3)

# KPI 1: Average crowd level + WoW change
avg_crowd = filtered["crowd_level_pct"].mean()
prev_avg_crowd = prev_filtered["crowd_level_pct"].mean()
crowd_delta = avg_crowd - prev_avg_crowd

with col1:
    st.metric(
        label="Average Crowd Level",
        value=f"{avg_crowd:.1f}%",
        delta=f"{crowd_delta:+.1f} pp vs. prior period",
        delta_color="inverse"
    )

# KPI 2: High-crowd day count + WoW change
high_crowd_count = int(filtered["is_high_crowd"].sum())
prev_high_count = int(prev_filtered["is_high_crowd"].sum())
high_crowd_delta = high_crowd_count - prev_high_count

with col2:
    st.metric(
        label="High Crowd Days (>70%)",
        value=high_crowd_count,
        delta=f"{high_crowd_delta:+d} vs. prior period",
        delta_color="inverse"
    )

# KPI 3: Average operating hours
avg_op_hours = (filtered["operating_minutes"].mean()) / 60
prev_op_hours = (prev_filtered["operating_minutes"].mean()) / 60
op_hours_delta = avg_op_hours - prev_op_hours

with col3:
    st.metric(
        label="Avg Operating Hours",
        value=f"{avg_op_hours:.1f}h",
        delta=f"{op_hours_delta:+.1f}h vs. prior period"
    )

# -------------------------- Operational Recommendations --------------------------
st.subheader("Operational Recommendations")

if avg_crowd < 55:
    st.success("**Crowd level: Low** | Standard staffing levels are sufficient. No diversion measures needed.")
elif avg_crowd < 70:
    st.info("**Crowd level: Moderate** | Add 10-15% roving staff to high-traffic areas. Monitor queue trends at top attractions.")
elif avg_crowd < 85:
    st.warning("**Crowd level: High** | Activate crowd diversion plan. Add extra FastPass distribution points and adjust parade times to spread foot traffic.")
else:
    st.error("**Crowd level: Critical** | Emergency staffing boost required. Implement maximum diversion protocols and extend operating hours if possible.")

# -------------------------- Supporting Charts --------------------------
st.subheader("Crowd Pattern Analysis")

# Chart 1: Daily crowd level trend with alert thresholds
daily_crowd = filtered.groupby("date")["crowd_level_pct"].mean().reset_index()

fig1, ax1 = plt.subplots(figsize=(10, 3.5))
ax1.plot(daily_crowd["date"], daily_crowd["crowd_level_pct"], color="#003366", linewidth=2)
ax1.axhline(y=70, color="#c82423", linestyle="--", label="70% High Alert")
ax1.axhline(y=85, color="#8b0000", linestyle=":", label="85% Critical Threshold")
ax1.set_ylabel("Crowd Level (%)")
ax1.set_title(f"Daily Crowd Trend - {selected_park}")
ax1.legend(loc="upper left")
ax1.grid(alpha=0.3)
st.pyplot(fig1)

# Chart 2: Crowd level by day of week
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

# -------------------------- Data Notes & Refresh Plan --------------------------
with st.expander("Data Notes & Production Refresh Plan"):
    st.markdown("""
    **Data Source**: Kaggle - Walt Disney World Wait Times and Crowd Calendar  
    **Coverage**: All 4 WDW theme parks, daily records from 2015 to 2026

    **Production Refresh Schedule**:
    - Park-level crowd data: refreshed every 1 hour during operating hours
    - Holiday and event calendar: updated weekly, every Monday
    - Ride-level wait times: refreshed every 15 minutes for on-site teams

    **Action Trigger**:
    - Crowd level above 70%: activate standard crowd diversion plan
    - Crowd level above 85%: trigger emergency staffing and protocol escalation

    **Limitations**:
    - Crowd level is an estimated occupancy rate, not exact visitor headcount
    - Temporary ride closures and extreme weather events are not fully reflected in this dataset
    - This is a historical snapshot dataset; production deployment would connect to live park systems
    """)

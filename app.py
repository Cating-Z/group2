import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt

# -------------------------- 页面基础配置 --------------------------
st.set_page_config(page_title="WDW Operations Dashboard", layout="wide")

# 解决matplotlib显示问题
plt.rcParams["axes.unicode_minus"] = False

# 页面标题与定位
st.title("Walt Disney World Operations Dashboard")
st.caption("Built for Park Operations Managers | Support staffing, ride scheduling and crowd diversion decisions")

# -------------------------- 数据加载与清洗 --------------------------
@st.cache_data(show_spinner=False)
def load_and_clean_data():
    """加载并清洗乐园日历客流数据，返回处理好的DataFrame与日期边界"""
    df = pd.read_csv("calendar_enriched.csv")
    
    # 统一日期格式
    df["date"] = pd.to_datetime(df["date"])
    
    # 衍生字段：日期类型标签，用于筛选
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
    
    # 衍生字段：是否高峰日（拥挤度>70%定义为高峰）
    df["is_high_crowd"] = df["crowd_level_pct"] > 70
    
    date_min = df["date"].min()
    date_max = df["date"].max()
    
    return df, date_min, date_max

# 加载数据
df, date_min, date_max = load_and_clean_data()

# -------------------------- 侧边栏筛选器 --------------------------
with st.sidebar:
    st.header("Filters")
    
    # 1. 日期范围筛选
    date_range = st.date_input(
        "Select date range",
        value=(date_min, date_max),
        min_value=date_min,
        max_value=date_max
    )
    start_dt = pd.to_datetime(date_range[0])
    end_dt = pd.to_datetime(date_range[1])
    
    # 2. 乐园筛选
    park_list = sorted(df["park_name"].unique())
    selected_park = st.selectbox("Select park", park_list)
    
    # 3. 日期类型筛选
    day_type_options = ["All days", "Weekend only", "Holiday only", "Special event only"]
    selected_day_type = st.selectbox("Day type filter", day_type_options)

# -------------------------- 数据过滤 --------------------------
# 基础过滤：日期 + 乐园
filtered = df[
    (df["date"] >= start_dt) &
    (df["date"] <= end_dt) &
    (df["park_name"] == selected_park)
].copy()

# 日期类型二次过滤
if selected_day_type == "Weekend only":
    filtered = filtered[filtered["is_weekend"] == True]
elif selected_day_type == "Holiday only":
    filtered = filtered[filtered["is_holiday"] == True]
elif selected_day_type == "Special event only":
    filtered = filtered[filtered["has_special_event"] == True]

# -------------------------- 核心KPI指标 --------------------------
st.subheader("Key Operational Metrics")
col1, col2, col3 = st.columns(3)

# KPI 1：平均客流拥挤度
avg_crowd = filtered["crowd_level_pct"].mean()
with col1:
    st.metric(
        label="Average Crowd Level",
        value=f"{avg_crowd:.1f}%",
        help="Average daily crowd occupancy for the selected period"
    )

# KPI 2：高峰日占比
high_crowd_pct = (filtered["is_high_crowd"].mean()) * 100
with col2:
    st.metric(
        label="High Crowd Days",
        value=f"{high_crowd_pct:.1f}%",
        help="Share of days with crowd level above 70%"
    )

# KPI 3：平均运营时长
avg_op_hours = (filtered["operating_minutes"].mean()) / 60
with col3:
    st.metric(
        label="Avg Operating Hours",
        value=f"{avg_op_hours:.1f}h",
        help="Average daily park operating hours"
    )

# -------------------------- 可视化图表 --------------------------
st.subheader("Crowd Insights")

tab1, tab2 = st.tabs(["Daily Trend", "Day of Week Pattern"])

# 标签1：每日客流趋势
with tab1:
    daily_crowd = filtered.groupby("date")["crowd_level_pct"].mean().reset_index()
    
    fig, ax = plt.subplots(figsize=(10, 3.5))
    ax.plot(daily_crowd["date"], daily_crowd["crowd_level_pct"], 
            color="#003087", linewidth=2)
    ax.axhline(y=70, color="#d1232a", linestyle="--", label="70% Alert Threshold")
    ax.set_ylabel("Crowd Level (%)")
    ax.set_title(f"Daily Crowd Level — {selected_park}")
    ax.legend()
    ax.grid(alpha=0.3)
    st.pyplot(fig)

# 标签2：星期几分布模式
with tab2:
    dow_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    dow_crowd = filtered.groupby("day_of_week")["crowd_level_pct"].mean().reindex(dow_order)
    
    fig, ax = plt.subplots(figsize=(10, 3.5))
    bars = ax.bar(dow_crowd.index, dow_crowd.values, color="#4d8fbf")
    ax.axhline(y=70, color="#d1232a", linestyle="--")
    ax.set_ylabel("Average Crowd Level (%)")
    ax.set_title("Crowd Level by Day of Week")
    ax.bar_label(bars, fmt="%.1f%%", padding=3)
    st.pyplot(fig)

# -------------------------- 数据说明与刷新策略 --------------------------
st.divider()
with st.expander("Data Notes & Refresh Schedule"):
    st.markdown("""
    **Data Source**: Kaggle Walt Disney World Wait Times and Crowd Calendar dataset  
    **Coverage**: All 4 WDW theme parks, 2015 – 2026 daily records  

    **Production Refresh Plan**:
    - Core crowd & operating hours data: refreshed every 1 hour during park operating time
    - Special event & holiday calendar: updated once per week, every Monday
    - Ride-level wait times: refreshed every 15 minutes in production

    **Limitations**:
    - Crowd level is an estimated occupancy rate, not exact headcount
    - Weather disruptions and temporary ride closures are not fully reflected in this dataset
    """)

---

### 设计决策说明（对应作业评分点）
1.  **面向角色与决策支持**
    仪表盘专为乐园运营经理设计，核心支持三类决策：高峰日人员排班增补、热门项目开放时段调整、特殊活动期间客流分流。三个KPI直接对应运营核心关切：整体拥挤程度、高峰日占比、运营时长，无需多余信息。

2.  **展示与删减的理由**
    - 保留：日期范围、乐园、日期类型三类筛选，满足运营按周期、分园区、分场景查看的需求。
    - 删减：删除了细粒度项目级等待时间、天气等非核心字段。运营经理做全局排班调度时，首先关注园区级客流规律，项目级数据属于二级运营工具，放在主仪表盘会造成信息拥挤。
    - 布局：KPI置顶（5秒获取核心信息），图表用标签页切换，减少页面纵向长度，符合“小巧优于拥挤”的原则。

3.  **刷新频率的依据**
    客流数据每小时刷新即可满足排班与调度需求，无需实时秒级更新；活动日历每周更新一次符合运营排期节奏；项目级等待时间15分钟刷新，对应现场调度需求。分级刷新既保证时效性，也控制数据成本。

4.  **数据免责说明**
    明确标注数据为估算值、存在局限性，避免运营团队将其作为精确客流依据，符合业务沟通的严谨性要求。

---

### README.md（个人独立版本，可直接提交）
```markdown
# WDW Park Operations Dashboard

## Overview
This is a Streamlit dashboard built for Walt Disney World park operations managers. It supports daily staffing, ride scheduling and crowd diversion decisions based on historical crowd level, operating hours and special event data.

## Target User
Park Operations Managers at Walt Disney World Resort.

## Supported Decisions
1.  Adjust staffing levels based on expected crowd level
2.  Schedule ride operating hours and parade routes
3.  Prepare crowd diversion plans for holidays and special events

## Dashboard Structure
### Key Metrics
- **Average Crowd Level**: average daily occupancy percentage for the selected period
- **High Crowd Days**: share of days with crowd level above the 70% operational alert threshold
- **Avg Operating Hours**: average daily park operating hours

### Visualizations
- **Daily Trend**: line chart showing daily crowd level movement with the 70% alert threshold
- **Day of Week Pattern**: bar chart comparing average crowd level across each weekday

### Filters
- Date range selector
- Park selector (all 4 WDW theme parks)
- Day type filter: all days / weekend only / holiday only / special event only

## Data Source
Kaggle: Walt Disney World Wait Times and Crowd Calendar
- Coverage: 2015 – 2026, daily records for all 4 parks
- Fields: crowd level, operating hours, holiday flags, special event flags, weekend indicator

## Refresh Schedule (Production)
| Data Category | Refresh Frequency |
|---|---|
| Park-level crowd level | Every 1 hour during operating hours |
| Special event & holiday calendar | Weekly (every Monday) |
| Ride-level wait times | Every 15 minutes |

## Design Rationale
I kept the dashboard focused and minimal instead of packing in every available metric. Operations managers need 3 core numbers and 2 trend views to make high-level staffing and scheduling decisions. Adding too many granular charts would slow down daily checks and reduce decision efficiency.

Crowd level is presented as the primary metric because it directly drives staffing costs and guest experience. The 70% threshold is marked as the operational alert line, which is the standard trigger for extra staffing and crowd diversion measures.

## Limitations
- Crowd level is an estimated occupancy rate, not exact visitor count
- Temporary ride closures and extreme weather events are not fully reflected in the dataset
- This is a historical snapshot dataset; production deployment would connect to live park systems

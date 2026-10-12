import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

# ---------------------- 1. 页面基础配置（作业强制要求） ----------------------
# 解决matplotlib中文乱码问题
plt.rcParams['font.sans-serif'] = ['WenQuanYi Zen Hei']
plt.rcParams['axes.unicode_minus'] = False

# 页面标题+小组名称（替换成你们小组真实名称）
st.title("Disney World 乐园运营仪表盘 | 小组名称：1012-group2")
# 单行说明：面向角色+核心决策（贴合作业要求）
st.caption("面向角色：迪士尼乐园运营经理 | 支撑决策：根据客流拥挤度调整人力配置与设施开放计划")

# 数据周期+刷新频率标注（作业Step4要求，从Kaggle确认后替换202X为真实年份）
st.markdown(f"""
**数据说明**：
- 覆盖周期：202X年1月 - 202X年12月（Kaggle迪士尼乐园客流快照数据）
- 生产环境计划刷新频率：每1小时（同步实时客流、天气、活动信息）
""", unsafe_allow_html=True)


# ---------------------- 2. 加载数据（基于真实CSV字段，无假设字段） ----------------------
@st.cache_data  # 缓存数据，避免重复加载，提升页面速度
def load_real_data():
    # 加载3个核心CSV，使用真实字段名
    calendar_df = pd.read_csv("calendar_enriched.csv")  # 日历+客流数据
    ride_df = pd.read_csv("ride_stats.csv")              # 设施数据（假设含ride_name/ride_type/status）
    park_df = pd.read_csv("park_stats.csv")              # 园区数据（假设含daily_visitors）

    # 数据预处理：统一日期格式（使用calendar_df真实日期字段"date"）
    calendar_df["date"] = pd.to_datetime(calendar_df["date"])
    # 若ride_df有时间戳，也统一格式（无则注释）
    if "timestamp" in ride_df.columns:
        ride_df["timestamp"] = pd.to_datetime(ride_df["timestamp"])
    # park_df日期统一
    if "date" in park_df.columns:
        park_df["date"] = pd.to_datetime(park_df["date"])

    # 提取日期范围（用于筛选器）
    min_date = calendar_df["date"].min()
    max_date = calendar_df["date"].max()

    return calendar_df, ride_df, park_df, min_date, max_date


# 调用函数加载真实数据
calendar_df, ride_df, park_df, min_date, max_date = load_real_data()


# ---------------------- 3. 筛选器设计（仅保留运营经理需要的，无冗余） ----------------------
st.sidebar.header("运营筛选条件")  # 侧边栏放筛选器，不占主视觉

# 1. 日期范围筛选（运营经理需查看特定时段客流）
selected_dates = st.sidebar.date_input(
    "选择分析日期范围",
    value=[min_date, max_date],
    min_value=min_date,
    max_value=max_date
)
# 转换为datetime，匹配数据格式
start_date = pd.to_datetime(selected_dates[0])
end_date = pd.to_datetime(selected_dates[1])

# 2. 园区筛选（多园区场景，运营经理关注单个园区）
if "park_name" in calendar_df.columns:
    park_list = calendar_df["park_name"].unique()  # 使用calendar_df真实园区字段
    selected_park = st.sidebar.selectbox("选择目标园区", park_list, index=0)
else:
    selected_park = "Disney World 主园区"  # 无园区字段时默认值

# 3. 特殊日期筛选（运营经理需关注节假日/活动日）
special_date_options = ["全部日期", "仅周末", "仅节假日", "仅特殊活动日"]
selected_special_date = st.sidebar.selectbox("特殊日期筛选", special_date_options, index=0)


# ---------------------- 4. 数据过滤（基于筛选条件，仅保留需要的数据） ----------------------
# 基础过滤：日期+园区
filtered_calendar = calendar_df[
    (calendar_df["date"] >= start_date) &
    (calendar_df["date"] <= end_date) &
    (calendar_df["park_name"] == selected_park)
].copy()

# 特殊日期二次过滤（基于calendar_df真实字段）
if selected_special_date == "仅周末":
    filtered_calendar = filtered_calendar[filtered_calendar["is_weekend"] == True]
elif selected_special_date == "仅节假日":
    filtered_calendar = filtered_calendar[filtered_calendar["is_holiday"] == True]
elif selected_special_date == "仅特殊活动日":
    filtered_calendar = filtered_calendar[filtered_calendar["has_special_event"] == True]

# 设施数据过滤（若有）
if "park_name" in ride_df.columns:
    filtered_ride = ride_df[ride_df["park_name"] == selected_park].copy()
else:
    filtered_ride = ride_df  # 无园区字段时保留全部设施数据


# ---------------------- 5. 核心KPI计算（用真实字段，作业要求最多3个） ----------------------
st.subheader("核心运营KPI")
col1, col2, col3 = st.columns(3)  # 横向并列，5秒内可见

# KPI1：平均客流拥挤度（核心指标，用calendar_df真实字段"crowd_level_pct"）
avg_crowd = filtered_calendar["crowd_level_pct"].mean()
# 对比筛选期前7天的拥挤度（业务同比）
prev_week_end = start_date - pd.Timedelta(days=1)
prev_week_start = prev_week_end - pd.Timedelta(days=len(filtered_calendar)-1)
prev_week_crowd = calendar_df[
    (calendar_df["date"] >= prev_week_start) &
    (calendar_df["date"] <= prev_week_end) &
    (calendar_df["park_name"] == selected_park)
]["crowd_level_pct"].mean()
crowd_change = avg_crowd - prev_week_crowd

with col1:
    st.metric(
        label="平均客流拥挤度（%）",
        value=f"{avg_crowd:.0f}%",
        delta=f"{crowd_change:.0f}%（较上周同期）",
        delta_color="inverse"  # 拥挤度上升红，下降绿
    )

# KPI2：园区日均开放时长（用真实字段"operating_minutes"）
avg_operating_hours = (filtered_calendar["operating_minutes"].mean()) / 60  # 转小时
with col2:
    st.metric(
        label="园区日均开放时长",
        value=f"{avg_operating_hours:.1f}小时",
        delta=None
    )

# KPI3：设施正常运行率（用ride_df真实字段"status"）
if "status" in filtered_ride.columns:
    total_rides = filtered_ride["ride_name"].nunique()  # 假设设施名称字段"ride_name"
    operational_rides = filtered_ride[filtered_ride["status"] == "operational"]["ride_name"].nunique()
    operation_rate = (operational_rides / total_rides) * 100 if total_rides > 0 else 0
    with col3:
        st.metric(
            label="设施正常运行率",
            value=f"{operation_rate:.0f}%",
            delta=None
        )
else:
    # 无设施数据时替换为"日均入园人数"（用park_df真实字段）
    if "daily_visitors" in park_df.columns:
        filtered_park = park_df[
            (park_df["date"] >= start_date) &
            (park_df["date"] <= end_date) &
            (park_df["park_name"] == selected_park)
        ]
        avg_visitors = filtered_park["daily_visitors"].mean()
        with col3:
            st.metric(
                label="园区日均入园人数",
                value=f"{avg_visitors:.0f}人",
                delta=None
            )


# ---------------------- 6. 辅助图表（1-2个，解释KPI涨跌，用真实字段） ----------------------
st.subheader("客流洞察（解释KPI变动原因）")

# 图表1：拥挤度时间趋势（按日期，运营经理看客流变化规律）
st.markdown(f"### {selected_park} 拥挤度趋势（{start_date.date()} 至 {end_date.date()}）")
# 按日期分组计算日均拥挤度
daily_crowd = filtered_calendar.groupby(filtered_calendar["date"].dt.date)["crowd_level_pct"].mean().reset_index()
daily_crowd["date"] = pd.to_datetime(daily_crowd["date"])

# 绘制折线图
fig, ax = plt.subplots(figsize=(12, 4))
ax.plot(daily_crowd["date"], daily_crowd["crowd_level_pct"], marker="o", color="#1f77b4", linewidth=2)
# 添加拥挤度阈值线（运营目标：拥挤度≤70%）
ax.axhline(y=70, color="red", linestyle="--", label="运营警戒阈值（70%）")
# 标注周末/节假日（用真实字段）
for idx, row in daily_crowd.iterrows():
    date_str = row["date"].strftime("%Y-%m-%d")
    is_weekend = filtered_calendar[filtered_calendar["date"].dt.date == row["date"].date()]["is_weekend"].iloc[0]
    if is_weekend:
        ax.scatter(row["date"], row["crowd_level_pct"], color="orange", s=80, zorder=5)  # 周末标橙点

ax.set_xlabel("日期")
ax.set_ylabel("日均拥挤度（%）")
ax.set_title(f"{selected_special_date} 拥挤度变化趋势")
ax.legend()
ax.grid(True, alpha=0.3)
st.pyplot(fig)

# 图表2：拥挤度与影响因素关联（运营经理看什么导致拥挤）
st.markdown(f"### {selected_park} 拥挤度影响因素分析")
# 按"是否有特殊活动"分组，对比拥挤度
event_crowd = filtered_calendar.groupby("has_special_event")["crowd_level_pct"].agg(["mean", "count"]).reset_index()
event_crowd["has_special_event"] = event_crowd["has_special_event"].map({True: "有特殊活动", False: "无特殊活动"})

# 绘制柱状图
fig, ax = plt.subplots(figsize=(8, 4))
bars = ax.bar(event_crowd["has_special_event"], event_crowd["mean"], color=["#ff7f0e", "#2ca02c"])
ax.set_xlabel("是否有特殊活动")
ax.set_ylabel("平均拥挤度（%）")
ax.set_title("特殊活动对园区拥挤度的影响")

# 在柱子上标注数值和样本量
for bar, count in zip(bars, event_crowd["count"]):
    height = bar.get_height()
    ax.text(bar.get_x() + bar.get_width()/2., height + 1,
            f"{height:.0f}%\n(n={count})", ha="center", va="bottom")

st.pyplot(fig)


# ---------------------- 7. 数据免责说明（作业Step3要求，规避误导） ----------------------
st.markdown("""
---
**数据免责声明**：
1. 本仪表盘基于Kaggle快照数据，生产环境将每小时同步实时客流、天气、活动数据；
2. 拥挤度（crowd_level_pct）基于园区承载量估算，实际客流可能因临时闭园、极端天气波动；
3. 特殊活动数据（has_special_event）不包含临时加场活动，如需实时活动信息请参考园区公告。
""", unsafe_allow_html=True)

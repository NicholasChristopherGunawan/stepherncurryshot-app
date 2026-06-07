import os

import pandas as pd
import plotly.express as px
import streamlit as st


# ====================================
# PAGE CONFIG
# ====================================

st.title("🏀 Stephen Curry Shot Analysis")

st.markdown("""
### About This Project

Stephen Curry is widely recognized as one of the greatest shooters in NBA history.

This dashboard analyzes his shot attempts during the 2015-2016 NBA season to understand which factors contribute to successful shots. The analysis focuses on variables such as shot distance, defender pressure, dribbles, ball possession time, and game situations.

**Research Question:**
What makes a shot successful for Stephen Curry?
""")


# ====================================
# LOAD DATA
# ====================================

DEFAULT_CSV_PATH = r"C:\Users\NICHOLAS\Downloads\StephenCurryDashboard\cleaned_shot_logs.csv"


def period_label(period: int) -> str:
    if period <= 4:
        return f"Q{period}"
    return f"OT{period - 4}"


@st.cache_data
def load_data(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)

    df["player_name"] = df["player_name"].str.title()

    period_order = [
        period_label(period)
        for period in sorted(df["PERIOD"].dropna().unique())
    ]

    df["period_label"] = pd.Categorical(
        df["PERIOD"].apply(period_label),
        categories=period_order,
        ordered=True,
    )

    df["made"] = df["shot_made_flag"].astype(int)
    df["attempt"] = 1
    df["points_expected"] = df["PTS_TYPE"] * df["made"]
    df["is_three"] = df["PTS_TYPE"].eq(3)

    df["distance_bin"] = pd.cut(
        df["SHOT_DIST"],
        bins=[0, 5, 10, 16, 23.75, 30, 50],
        labels=["0-5", "5-10", "10-16", "16-23.75", "23.75-30", "30+"],
        include_lowest=True,
    )

    df["defender_bin"] = pd.cut(
        df["CLOSE_DEF_DIST"],
        bins=[0, 2, 4, 6, 8, 30],
        labels=["0-2 tight", "2-4", "4-6", "6-8", "8+ open"],
        include_lowest=True,
    )

    df["shot_clock_bin"] = pd.cut(
        df["SHOT_CLOCK"],
        bins=[0, 4, 8, 14, 20, 24],
        labels=["0-4", "4-8", "8-14", "14-20", "20-24"],
        include_lowest=True,
    )

    df["margin_group"] = pd.cut(
        df["FINAL_MARGIN"],
        bins=[-80, -11, -1, 0, 10, 80],
        labels=["Lost 11+", "Lost 1-10", "Tied", "Won 1-10", "Won 11+"],
    )

    return df


csv_path = DEFAULT_CSV_PATH if os.path.exists(DEFAULT_CSV_PATH) else "cleaned_shot_logs.csv"
df = load_data(csv_path)


# ====================================
# HELPER FUNCTIONS
# ====================================

def summarize(grouped: pd.DataFrame) -> pd.DataFrame:
    summary = (
        grouped.agg(
            attempts=("attempt", "sum"),
            makes=("made", "sum"),
            fg_pct=("made", "mean"),
            points=("points_expected", "sum"),
        )
        .reset_index()
    )

    summary["fg_pct"] = summary["fg_pct"] * 100
    summary["points_per_shot"] = summary["points"] / summary["attempts"]

    return summary


def show_metrics(data: pd.DataFrame) -> None:
    attempts = len(data)
    makes = int(data["made"].sum())

    fg_pct = data["made"].mean() * 100 if attempts else 0
    points = int(data["points_expected"].sum())
    points_per_shot = points / attempts if attempts else 0
    three_rate = data["is_three"].mean() * 100 if attempts else 0

    if attempts:
        efg_pct = (
            data["made"].sum()
            + 0.5 * data.loc[data["is_three"], "made"].sum()
        ) / attempts * 100
    else:
        efg_pct = 0

    col1, col2, col3, col4, col5, col6 = st.columns(6)

    col1.metric("Attempts", f"{attempts:,}")
    col2.metric("Makes", f"{makes:,}")
    col3.metric("FG%", f"{fg_pct:.1f}%")
    col4.metric("eFG%", f"{efg_pct:.1f}%")
    col5.metric("Pts/Shot", f"{points_per_shot:.2f}")
    col6.metric("3PA Rate", f"{three_rate:.1f}%")


def efficiency_bar(data: pd.DataFrame, x_col: str, title: str):
    summary = summarize(data.groupby(x_col, observed=True))

    fig = px.bar(
        summary,
        x=x_col,
        y="fg_pct",
        text="attempts",
        color="points_per_shot",
        color_continuous_scale="RdYlGn",
        title=title,
        labels={
            "fg_pct": "FG%",
            "points_per_shot": "Points per Shot",
            "attempts": "Attempts",
        },
    )

    fig.update_traces(
        texttemplate="%{text} attempts",
        textposition="outside",
    )

    fig.update_layout(
        yaxis_ticksuffix="%",
        uniformtext_minsize=10,
        uniformtext_mode="hide",
    )

    return fig


# ====================================
# TITLE
# ====================================

st.title("🏀 NBA Shot Quality Dashboard")
st.markdown("Analyze shot selection, defender pressure, timing, and scoring efficiency.")


# ====================================
# SIDEBAR FILTERS
# ====================================

st.sidebar.header("Filters")

players = sorted(df["player_name"].dropna().unique())
default_player_index = players.index("Stephen Curry") if "Stephen Curry" in players else 0

selected_player = st.sidebar.selectbox(
    "Select Player",
    players,
    index=default_player_index,
)

selected_periods = st.sidebar.multiselect(
    "Period",
    list(df["period_label"].cat.categories),
    default=list(df["period_label"].cat.categories),
)

selected_shot_types = st.sidebar.multiselect(
    "Shot Type",
    [2, 3],
    default=[2, 3],
    format_func=lambda x: f"{x}PT",
)

selected_locations = st.sidebar.multiselect(
    "Location",
    ["H", "A"],
    default=["H", "A"],
    format_func=lambda x: "Home" if x == "H" else "Away",
)

min_distance = float(df["SHOT_DIST"].min())
max_distance = float(df["SHOT_DIST"].max())

selected_distance = st.sidebar.slider(
    "Shot Distance",
    min_distance,
    max_distance,
    (min_distance, max_distance),
    step=0.5,
)


filtered_df = df[
    (df["player_name"] == selected_player)
    & (df["period_label"].isin(selected_periods))
    & (df["PTS_TYPE"].isin(selected_shot_types))
    & (df["LOCATION"].isin(selected_locations))
    & (df["SHOT_DIST"].between(selected_distance[0], selected_distance[1]))
].copy()


# ====================================
# KPI METRICS
# ====================================

show_metrics(filtered_df)


# ====================================
# TABS
# ====================================

tab1, tab2, tab3, tab4, tab5 = st.tabs(
    [
        "Overview",
        "Shot Profile",
        "Defender Pressure",
        "Game Situation",
        "Data",
    ]
)


# ====================================
# TAB 1: OVERVIEW
# ====================================

with tab1:
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Shot Result by Shot Type")

        shot_mix = summarize(
            filtered_df.groupby(["PTS_TYPE", "SHOT_RESULT"], observed=True)
        )

        fig = px.sunburst(
            shot_mix,
            path=["PTS_TYPE", "SHOT_RESULT"],
            values="attempts",
            color="fg_pct",
            color_continuous_scale="RdYlGn",
            title="Shot Attempts by Type and Result",
        )

        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.subheader("Home vs Away Efficiency")

        location_summary = summarize(
            filtered_df.groupby("LOCATION", observed=True)
        )

        location_summary["LOCATION"] = location_summary["LOCATION"].map(
            {
                "H": "Home",
                "A": "Away",
            }
        )

        fig = px.bar(
            location_summary,
            x="LOCATION",
            y="points_per_shot",
            color="fg_pct",
            text="attempts",
            color_continuous_scale="RdYlGn",
            title="Efficiency by Location",
            labels={
                "points_per_shot": "Points per Shot",
                "fg_pct": "FG%",
            },
        )

        fig.update_traces(
            texttemplate="%{text} attempts",
            textposition="outside",
        )

        st.plotly_chart(fig, use_container_width=True)


# ====================================
# TAB 2: SHOT PROFILE
# ====================================

with tab2:
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Shot Distance Distribution")

        fig = px.histogram(
            filtered_df,
            x="SHOT_DIST",
            color="SHOT_RESULT",
            nbins=35,
            barmode="overlay",
            opacity=0.75,
            title="Shot Distance Distribution",
            labels={
                "SHOT_DIST": "Shot Distance",
            },
        )

        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.subheader("Efficiency by Distance Zone")

        fig = efficiency_bar(
            filtered_df,
            "distance_bin",
            "FG% and Points per Shot by Distance Zone",
        )

        st.plotly_chart(fig, use_container_width=True)

    distance_trend = (
        filtered_df.assign(distance_round=filtered_df["SHOT_DIST"].round())
        .groupby("distance_round", observed=True)
        .agg(
            fg_pct=("made", "mean"),
            attempts=("attempt", "sum"),
        )
        .reset_index()
    )

    distance_trend = distance_trend[distance_trend["attempts"] >= 5]
    distance_trend["fg_pct"] = distance_trend["fg_pct"] * 100

    fig = px.scatter(
        distance_trend,
        x="distance_round",
        y="fg_pct",
        size="attempts",
        trendline="lowess",
        title="FG% Trend by Shot Distance",
        labels={
            "distance_round": "Shot Distance",
            "fg_pct": "FG%",
            "attempts": "Attempts",
        },
    )

    fig.update_layout(yaxis_ticksuffix="%")

    st.plotly_chart(fig, use_container_width=True)


# ====================================
# TAB 3: DEFENDER PRESSURE
# ====================================

with tab3:
    st.subheader("Shot Distance vs Defender Distance")

    heatmap_data = summarize(
        filtered_df.groupby(["distance_bin", "defender_bin"], observed=True)
    )

    fig = px.density_heatmap(
        heatmap_data,
        x="distance_bin",
        y="defender_bin",
        z="fg_pct",
        histfunc="avg",
        text_auto=".1f",
        color_continuous_scale="RdYlGn",
        title="FG% Heatmap by Shot Distance and Defender Distance",
        labels={
            "distance_bin": "Shot Distance Zone",
            "defender_bin": "Closest Defender Distance",
            "fg_pct": "FG%",
        },
    )

    st.plotly_chart(fig, use_container_width=True)

    st.subheader("Toughest Defenders Faced")

    defender_summary = summarize(
        filtered_df.groupby("CLOSEST_DEFENDER", observed=True)
    )

    defender_summary = (
        defender_summary[defender_summary["attempts"] >= 5]
        .sort_values("points_per_shot")
        .head(15)
    )

    fig = px.bar(
        defender_summary.sort_values("points_per_shot", ascending=True),
        x="points_per_shot",
        y="CLOSEST_DEFENDER",
        orientation="h",
        color="fg_pct",
        text="attempts",
        color_continuous_scale="RdYlGn",
        title="Lowest Points per Shot Against Defender",
        labels={
            "points_per_shot": "Points per Shot",
            "CLOSEST_DEFENDER": "Defender",
            "fg_pct": "FG%",
        },
    )

    fig.update_traces(
        texttemplate="%{text} attempts",
        textposition="outside",
    )

    st.plotly_chart(fig, use_container_width=True)


# ====================================
# TAB 4: GAME SITUATION
# ====================================

with tab4:
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Efficiency by Period")

        fig = efficiency_bar(
            filtered_df,
            "period_label",
            "FG% and Points per Shot by Period",
        )

        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.subheader("Efficiency by Shot Clock")

        shot_clock_df = filtered_df.dropna(subset=["shot_clock_bin"])

        fig = efficiency_bar(
            shot_clock_df,
            "shot_clock_bin",
            "FG% and Points per Shot by Shot Clock",
        )

        st.plotly_chart(fig, use_container_width=True)

    st.subheader("Shot Distance in Wins vs Losses")

    fig = px.box(
        filtered_df,
        x="W",
        y="SHOT_DIST",
        color="SHOT_RESULT",
        title="Shot Distance Distribution in Wins and Losses",
        labels={
            "W": "Game Result",
            "SHOT_DIST": "Shot Distance",
        },
    )

    st.plotly_chart(fig, use_container_width=True)

    st.subheader("Efficiency by Final Margin")

    margin_summary = summarize(
        filtered_df.groupby("margin_group", observed=True)
    )

    fig = px.bar(
        margin_summary,
        x="margin_group",
        y="points_per_shot",
        color="fg_pct",
        text="attempts",
        color_continuous_scale="RdYlGn",
        title="Points per Shot by Final Margin",
        labels={
            "margin_group": "Final Margin",
            "points_per_shot": "Points per Shot",
            "fg_pct": "FG%",
        },
    )

    fig.update_traces(
        texttemplate="%{text} attempts",
        textposition="outside",
    )

    st.plotly_chart(fig, use_container_width=True)


# ====================================
# TAB 5: DATA
# ====================================

with tab5:
    st.subheader("Filtered Shot Log")

    st.dataframe(
        filtered_df[
            [
                "MATCHUP",
                "period_label",
                "GAME_CLOCK",
                "SHOT_CLOCK",
                "DRIBBLES",
                "TOUCH_TIME",
                "SHOT_DIST",
                "PTS_TYPE",
                "SHOT_RESULT",
                "CLOSEST_DEFENDER",
                "CLOSE_DEF_DIST",
                "PTS",
            ]
        ].sort_values(
            [
                "MATCHUP",
                "period_label",
                "GAME_CLOCK",
            ]
        ),
        use_container_width=True,
        hide_index=True,
    )


# ====================================
# INSIGHT
# ====================================

st.divider()

if not filtered_df.empty:
    best_zone = (
        summarize(filtered_df.groupby("distance_bin", observed=True))
        .sort_values("points_per_shot", ascending=False)
        .iloc[0]
    )

    st.success(
        f"Best scoring zone for {selected_player}: "
        f"{best_zone['distance_bin']} ft, "
        f"{best_zone['points_per_shot']:.2f} points per shot "
        f"across {int(best_zone['attempts'])} attempts."
    )
else:
    st.warning("No shots match the selected filters.")

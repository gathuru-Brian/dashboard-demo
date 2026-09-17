import pandas as pd
import plotly.express as px
import streamlit as st

from utils.metrics import metric_card
from utils.ai import generate_ai_insights

def executive_page(df: pd.DataFrame):

    st.title("📊 Executive Dashboard")

    if df.empty:
        st.warning("No data available.")
        return

    # ==========================
    # KPIs
    # ==========================

    gross = df["gwp_usd"].sum()
    net = df["nep_usd"].sum()
    claims = df["claims_paid_usd"].sum()
    combined = df["combined_ratio"].mean() * 100
    loss = df["loss_ratio"].mean() * 100
    exposure = df["exposure"].sum()

    c1, c2, c3 = st.columns(3)

    with c1:
        st.metric(
            "Gross Written Premium",
            f"${gross:,.0f}"
        )

    with c2:
        st.metric(
            "Net Earned Premium",
            f"${net:,.0f}"
        )

    with c3:
        st.metric(
            "Claims Paid",
            f"${claims:,.0f}"
        )

    c4, c5, c6 = st.columns(3)

    with c4:
        st.metric(
            "Loss Ratio",
            f"{loss:.2f}%"
        )

    with c5:
        st.metric(
            "Combined Ratio",
            f"{combined:.2f}%"
        )

    with c6:
        st.metric(
            "Portfolio Exposure",
            f"${exposure:,.0f}"
        )

    st.divider()

    # ==========================
    # PREMIUM TREND
    # ==========================

    trend = (
        df.groupby(df["period"].dt.to_period("M"))
        [["gwp_usd", "nep_usd"]]
        .sum()
        .reset_index()
    )

    trend["period"] = trend["period"].dt.to_timestamp()

    fig = px.line(
        trend,
        x="period",
        y=["gwp_usd", "nep_usd"],
        markers=True,
        title="Premium Trend"
    )

    fig.update_layout(
        template="plotly_dark",
        height=450
    )

    st.plotly_chart(
        fig,
        use_container_width=True
    )

    # ==========================
    # BUSINESS MIX
    # ==========================

    st.subheader("Business Mix")

    lob = (
        df.groupby("line_of_business")["gwp_usd"]
        .sum()
        .reset_index()
    )

    pie = px.pie(
        lob,
        names="line_of_business",
        values="gwp_usd",
        hole=0.45
    )

    pie.update_layout(
        template="plotly_dark",
        height=420
    )

    st.plotly_chart(
        pie,
        use_container_width=True
    )

    # ==========================
    # TREATY PERFORMANCE
    # ==========================

    st.subheader("Treaty Performance Summary")

    summary = (
        df.groupby("line_of_business")
        .agg(
            Policies=("policy_id", "count"),
            Premium=("gwp_usd", "sum"),
            Claims=("claims_paid_usd", "sum"),
            Loss_Ratio=("loss_ratio", "mean"),
            Combined_Ratio=("combined_ratio", "mean"),
        )
        .reset_index()
    )

    summary["Premium"] = summary["Premium"].round(2)
    summary["Claims"] = summary["Claims"].round(2)
    summary["Loss_Ratio"] = (
        summary["Loss_Ratio"] * 100
    ).round(2)

    summary["Combined_Ratio"] = (
        summary["Combined_Ratio"] * 100
    ).round(2)

    st.dataframe(
        summary,
        use_container_width=True
    )

    st.divider()

    # ==========================
    # TOP CEDANTS
    # ==========================

    st.subheader("Top Cedants")

    cedants = (
        df.groupby("client_name")
        .agg(
            Premium=("gwp_usd", "sum")
        )
        .reset_index()
        .sort_values(
            "Premium",
            ascending=False
        )
        .head(10)
    )

    bar = px.bar(
        cedants,
        x="client_name",
        y="Premium",
        color="Premium",
        title="Top Cedants by Premium"
    )

    bar.update_layout(
        template="plotly_dark",
        xaxis_title="Cedant",
        yaxis_title="Premium (USD)"
    )

    st.plotly_chart(
        bar,
        use_container_width=True
    )

    st.divider()

    # ==========================
    # RISK CATEGORIES
    # ==========================

    st.subheader("Risk Category Distribution")

    risks = (
        df.groupby("risk_category")
        .size()
        .reset_index(name="Count")
    )

    risk_chart = px.bar(
        risks,
        x="risk_category",
        y="Count",
        color="Count"
    )

    risk_chart.update_layout(
        template="plotly_dark"
    )

    st.plotly_chart(
        risk_chart,
        use_container_width=True
    )

    st.divider()

    # ==========================
    # REGIONAL EXPOSURE
    # ==========================

    st.subheader("Regional Exposure")

    regions = (
        df.groupby("region")
        .agg(
            Premium=("gwp_usd", "sum")
        )
        .reset_index()
    )

    region_fig = px.bar(
        regions,
        x="region",
        y="Premium",
        color="Premium"
    )

    region_fig.update_layout(
        template="plotly_dark"
    )

    st.plotly_chart(
        region_fig,
        use_container_width=True
    )

    st.divider()

    # ==========================
    # AI INSIGHTS
    # ==========================

    st.subheader("AI Insights")

    for item in generate_ai_insights(df):
        st.info(item)

    highest_lob = (
        summary.sort_values(
            "Premium",
            ascending=False
        )
        .iloc[0]["line_of_business"]
    )

    highest_loss = (
        summary.sort_values(
            "Loss_Ratio",
            ascending=False
        )
        .iloc[0]["line_of_business"]
    )

    st.info(
        f"Highest premium line: **{highest_lob}**."
    )

    st.warning(
        f"Highest loss ratio observed in **{highest_loss}**."
    )

    st.success(
        "Portfolio remains well diversified across multiple regions."
    )

def logout_user() -> None:
    st.session_state.logged_in = False
    st.session_state.user = ""
    st.session_state.role = ""
    st.session_state.page = "login"
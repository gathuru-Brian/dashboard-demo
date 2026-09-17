import pandas as pd
import plotly.express as px
import streamlit as st


def market_intelligence_page(df: pd.DataFrame):

    st.title("🌍 Market Intelligence")

    if df.empty:
        st.warning("No market data available.")
        return

    st.subheader("Regional Premium Distribution")

    region = (
        df.groupby("region")
        .agg(
            Premium=("gwp_usd", "sum")
        )
        .reset_index()
    )

    fig = px.bar(
        region,
        x="region",
        y="Premium",
        color="Premium",
        title="Gross Written Premium by Region"
    )

    fig.update_layout(template="plotly_dark")

    st.plotly_chart(
        fig,
        use_container_width=True
    )

    st.divider()

    st.subheader("World Exposure")

    world = px.choropleth(
        region,
        locations="region",
        locationmode="country names",
        color="Premium"
    )

    world.update_layout(template="plotly_dark")

    st.plotly_chart(
        world,
        use_container_width=True
    )

    st.divider()

    st.subheader("Currency Exposure")

    currency = (
        df.groupby("currency")
        .agg(
            Premium=("gwp_usd", "sum")
        )
        .reset_index()
    )

    fig2 = px.pie(
        currency,
        names="currency",
        values="Premium",
        hole=0.45
    )

    fig2.update_layout(template="plotly_dark")

    st.plotly_chart(
        fig2,
        use_container_width=True
    )

    st.divider()

    st.subheader("Market Highlights")

    st.success("Global reinsurance pricing remains firm.")

    st.info("Natural catastrophe exposures continue increasing.")

    st.warning("Climate risks remain the largest emerging threat.")

    st.info("Agricultural insurance demand continues to rise.")
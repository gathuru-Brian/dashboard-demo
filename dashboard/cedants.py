"""
Cedants Dashboard
RMIP-DSS
---------------------------------
Cedant relationship and portfolio-concentration analytics. Gated on the
"cedants" permission (Chief Underwriter, Underwriting Manager, Underwriter,
Administrator).
"""

import pandas as pd
import plotly.express as px
import streamlit as st


def show_cedants_dashboard(df: pd.DataFrame, period_label: str) -> None:
    st.title("Cedants")
    st.caption(f"{period_label} • {len(df):,} records")

    if df.empty:
        st.warning("No records match the current filters.")
        return
    if "client_name" not in df.columns:
        st.info("Upload data with a `client_name` column to see cedant analytics.")
        return

    agg_kwargs = {"policy_count": ("policy_id", "nunique")}
    if "gwp_usd" in df.columns:
        agg_kwargs["premium"] = ("gwp_usd", "sum")
    if "claims_paid_usd" in df.columns:
        agg_kwargs["claims"] = ("claims_paid_usd", "sum")
    if "combined_ratio" in df.columns:
        agg_kwargs["combined_ratio"] = ("combined_ratio", "mean")
    if "premium_rate" in df.columns:
        agg_kwargs["avg_rate"] = ("premium_rate", "mean")

    cedants = df.groupby("client_name", as_index=False).agg(**agg_kwargs)
    if "premium" in cedants.columns:
        cedants = cedants.sort_values("premium", ascending=False)
    if "combined_ratio" in cedants.columns:
        cedants["combined_ratio"] = (cedants["combined_ratio"] * 100).round(1)

    concentration = (cedants["premium"].head(5).sum() / cedants["premium"].sum() * 100) if "premium" in cedants.columns and cedants["premium"].sum() else 0
    col1, col2, col3 = st.columns(3)
    col1.metric("Active cedants", f"{df['client_name'].nunique():,}", border=True)
    if "premium" in cedants.columns:
        col2.metric("Total premium", f"USD {cedants['premium'].sum() / 1e6:,.1f}M", border=True)
        col3.metric("Top 5 concentration", f"{concentration:.1f}%", delta="Monitor dependency" if concentration >= 50 else "Diversified", delta_color="inverse", border=True)

    st.markdown("**Cedant portfolio summary**")
    st.caption("Ranked by premium contribution across the current portfolio scope.")
    display_cols = {"client_name": "Cedant", "policy_count": "Policies"}
    if "premium" in cedants.columns:
        display_cols["premium"] = "Premium (USD)"
    if "claims" in cedants.columns:
        display_cols["claims"] = "Claims (USD)"
    if "combined_ratio" in cedants.columns:
        display_cols["combined_ratio"] = "Combined ratio (%)"
    if "avg_rate" in cedants.columns:
        display_cols["avg_rate"] = "Avg premium rate"

    st.dataframe(
        cedants[list(display_cols.keys())].rename(columns=display_cols),
        hide_index=True, width='stretch',
    )

    if "premium" in cedants.columns:
        st.markdown("**Top cedants by premium**")
        top = cedants.head(15)
        fig = px.bar(top, x="client_name", y="premium", color="premium",
                     labels={"client_name": "Cedant", "premium": "Premium (USD)"})
        st.plotly_chart(fig, width='stretch')

    if "combined_ratio" in cedants.columns and "premium" in cedants.columns:
        st.markdown("**Cedant profitability vs. scale**")
        fig2 = px.scatter(
            cedants, x="combined_ratio", y="premium", size="policy_count",
            hover_name="client_name",
            labels={"combined_ratio": "Combined ratio (%)", "premium": "Premium (USD)"},
        )
        st.plotly_chart(fig2, width='stretch')

    with st.expander("Select cedants to compare directly"):
        selected = st.multiselect(
            "Cedants", cedants["client_name"].tolist(),
            default=cedants["client_name"].head(5).tolist(),
        )
        if selected:
            comparison = cedants[cedants["client_name"].isin(selected)]
            st.dataframe(
                comparison[list(display_cols.keys())].rename(columns=display_cols),
                hide_index=True, width='stretch',
            )

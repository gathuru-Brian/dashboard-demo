"""
Pricing Analytics Dashboard
RMIP-DSS
---------------------------------
Pricing adequacy analysis and a standalone premium simulator. Gated on the
"pricing" permission (Executive, Pricing Manager, Pricing Analyst, Chief
Underwriter, Underwriting Manager, Data Scientist, Administrator).
"""

import pandas as pd
import plotly.express as px
import streamlit as st


def show_pricing_dashboard(df: pd.DataFrame, period_label: str) -> None:
    st.title("Pricing Analytics")
    st.caption(f"{period_label} • {len(df):,} records")

    if df.empty:
        st.warning("No records match the current filters.")
        return
    if "line_of_business" not in df.columns:
        st.info("Upload data with a `line_of_business` column to see pricing analytics.")
        return

    agg_kwargs = {}
    if "gwp_usd" in df.columns:
        agg_kwargs["premium"] = ("gwp_usd", "sum")
    if "loss_ratio" in df.columns:
        agg_kwargs["loss_ratio"] = ("loss_ratio", "mean")
    if "combined_ratio" in df.columns:
        agg_kwargs["combined_ratio"] = ("combined_ratio", "mean")
    if "premium_rate" in df.columns:
        agg_kwargs["avg_rate"] = ("premium_rate", "mean")

    if not agg_kwargs:
        st.info("Upload data with premium, loss ratio, or combined ratio fields to enable pricing analysis.")
        return

    pricing = df.groupby("line_of_business", as_index=False).agg(**agg_kwargs)
    if "loss_ratio" in pricing.columns:
        pricing["loss_ratio"] = (pricing["loss_ratio"] * 100).round(1)
    if "combined_ratio" in pricing.columns:
        pricing["combined_ratio"] = (pricing["combined_ratio"] * 100).round(1)

    premium_total = pricing["premium"].sum() if "premium" in pricing.columns else 0
    average_combined = pricing["combined_ratio"].mean() if "combined_ratio" in pricing.columns else None
    action_lines = int((pricing["combined_ratio"] >= 100).sum()) if "combined_ratio" in pricing.columns else 0
    kpi_cols = st.columns(4)
    kpi_cols[0].metric("Portfolio premium", f"USD {premium_total / 1e6:,.1f}M", border=True)
    kpi_cols[1].metric("Lines of business", f"{len(pricing):,}", border=True)
    kpi_cols[2].metric("Average combined ratio", f"{average_combined:.1f}%" if average_combined is not None else "N/A", border=True)
    kpi_cols[3].metric("Lines requiring action", f"{action_lines:,}", delta="At or above 100%" if action_lines else "Within threshold", delta_color="inverse", border=True)

    display_cols = {"line_of_business": "Line of business"}
    if "premium" in pricing.columns:
        display_cols["premium"] = "Premium (USD)"
    if "loss_ratio" in pricing.columns:
        display_cols["loss_ratio"] = "Loss ratio (%)"
    if "combined_ratio" in pricing.columns:
        display_cols["combined_ratio"] = "Combined ratio (%)"
    if "avg_rate" in pricing.columns:
        display_cols["avg_rate"] = "Avg premium rate"

    with st.container(border=True):
        st.markdown("**Pricing summary by line of business**")
        st.caption("Use the combined ratio to identify segments requiring underwriting or rate action.")
        st.dataframe(pricing[list(display_cols.keys())].rename(columns=display_cols), hide_index=True, width='stretch')

    if "loss_ratio" in pricing.columns and "combined_ratio" in pricing.columns:
        with st.container(border=True):
            st.markdown("**Loss ratio vs. combined ratio**")
            size_col = "premium" if "premium" in pricing.columns else None
            fig = px.scatter(pricing, x="loss_ratio", y="combined_ratio", size=size_col, color="line_of_business", labels={"loss_ratio": "Loss ratio (%)", "combined_ratio": "Combined ratio (%)"})
            fig.add_hline(y=100, line_dash="dash", line_color="gray", annotation_text="Break-even (100%)")
            st.plotly_chart(fig, width='stretch')

    st.divider()
    st.subheader("Premium simulator")
    st.caption(
        "Estimate a rate change for a single policy or block of business based on "
        "expected loss ratio, expense ratio, and target profit margin."
    )

    with st.form("standalone_pricing_simulator"):
        col1, col2 = st.columns(2)
        with col1:
            lines_available = sorted(df["line_of_business"].dropna().unique())
            selected_line = st.selectbox("Line of business", lines_available)
            current_premium = st.number_input("Current premium (USD)", min_value=0.0, value=100_000.0, step=1000.0)
        with col2:
            expected_loss_ratio = st.slider("Expected loss ratio (%)", 0, 150, 62)
            expense_ratio = st.slider("Expense ratio (%)", 0, 60, 25)
            profit_margin = st.slider("Target profit margin (%)", 0, 30, 10)
        calculate = st.form_submit_button("Calculate", type="primary")

    if calculate:
        required_combined = expected_loss_ratio + expense_ratio + profit_margin
        rate_change_pct = required_combined - 100
        new_premium = current_premium * (1 + rate_change_pct / 100)

        col1, col2, col3 = st.columns(3)
        col1.metric("Indicated rate change", f"{rate_change_pct:+.1f}%")
        col2.metric("Projected premium", f"${new_premium:,.2f}")
        col3.metric("Required combined ratio", f"{required_combined:.1f}%")

        if rate_change_pct <= 0:
            st.success(f"Current pricing appears adequate for {selected_line}.")
        else:
            st.warning(f"A rate increase is indicated for {selected_line} to meet target margin.")

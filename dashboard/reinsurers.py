"""
Reinsurers Dashboard
RMIP-DSS
---------------------------------
Surfaces treaty and reinsurance-specific analytics:
  - Reinsurer performance and market share (ceded premium)
  - Treaty type mix (Quota Share, XoL, Surplus, Facultative, Stop Loss)
  - Retention vs. ceded premium by line of business
  - Broker / commission overview

Gracefully informs the user when the active dataset doesn't include
reinsurance-specific fields (ceded_premium, retention, treaty_type,
reinsurer, commission, broker), rather than crashing.
"""

import pandas as pd
import plotly.express as px
import streamlit as st

REQUIRED_FOR_THIS_TAB = {"ceded_premium", "retention", "treaty_type", "reinsurer"}


def _has_column(df: pd.DataFrame, column: str) -> bool:
    return column in df.columns and df[column].notna().any()


def _missing_data_notice(df: pd.DataFrame) -> bool:
    """Returns True (and shows a notice) if the dataset lacks reinsurance fields."""
    present = {col for col in REQUIRED_FOR_THIS_TAB if _has_column(df, col)}
    if not present:
        st.info(
            "The active dataset doesn't include reinsurance-specific fields "
            "(`ceded_premium`, `retention`, `treaty_type`, `reinsurer`). "
            "Upload a dataset with these columns -- or use the generated "
            "global reinsurance sample -- to populate this workspace."
        )
        return True
    return False


def show_reinsurer_overview(df: pd.DataFrame, period_label: str) -> None:
    st.subheader("Reinsurer Overview")
    if df.empty:
        st.warning("No records available for the selected filters.")
        return
    if _missing_data_notice(df):
        return

    total_ceded = df.ceded_premium.sum() if _has_column(df, "ceded_premium") else 0
    total_retention = df.retention.sum() if _has_column(df, "retention") else 0
    total_gwp = (total_ceded + total_retention) if (total_ceded or total_retention) else df.get("gwp_usd", pd.Series(dtype=float)).sum()
    cession_rate = (total_ceded / total_gwp * 100) if total_gwp else 0

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total ceded premium", f"USD {total_ceded / 1e6:,.1f}M", border=True)
    col2.metric("Total retention", f"USD {total_retention / 1e6:,.1f}M", border=True)
    col3.metric("Cession rate", f"{cession_rate:.1f}%", border=True)
    if _has_column(df, "reinsurer"):
        col4.metric("Active reinsurers", f"{df.reinsurer.nunique():,}", border=True)

    left, right = st.columns(2)
    with left:
        if _has_column(df, "reinsurer"):
            st.markdown("**Top reinsurers by ceded premium**")
            by_reinsurer = df.groupby("reinsurer")["ceded_premium"].sum().sort_values(ascending=False).head(10)
            st.plotly_chart(
                px.bar(by_reinsurer, orientation="h", labels={"value": "Ceded premium (USD)", "index": "Reinsurer"}),
                width='stretch',
            )
    with right:
        if _has_column(df, "treaty_type"):
            st.markdown("**Treaty type mix**")
            treaty_mix = df.groupby("treaty_type")["ceded_premium"].sum().reset_index()
            st.plotly_chart(
                px.pie(treaty_mix, names="treaty_type", values="ceded_premium", hole=0.5),
                width='stretch',
            )

    if _has_column(df, "broker"):
        st.markdown("**Ceded premium by broker**")
        by_broker = df.groupby("broker")["ceded_premium"].sum().sort_values(ascending=False)
        st.bar_chart(by_broker)


def show_treaty_structure(df: pd.DataFrame, period_label: str) -> None:
    st.subheader("Treaty Structure")
    if df.empty:
        st.warning("No records available for the selected filters.")
        return
    if _missing_data_notice(df):
        return

    if _has_column(df, "line_of_business") and _has_column(df, "treaty_type"):
        st.markdown("**Treaty type by line of business**")
        pivot = (
            df.groupby(["line_of_business", "treaty_type"])["ceded_premium"]
            .sum().reset_index()
        )
        st.plotly_chart(
            px.bar(
                pivot, x="line_of_business", y="ceded_premium", color="treaty_type",
                barmode="stack",
                labels={"ceded_premium": "Ceded premium (USD)", "line_of_business": "Line of business"},
            ),
            width='stretch',
        )

    if _has_column(df, "line_of_business"):
        st.markdown("**Retention vs. ceded premium by line of business**")
        by_line = df.groupby("line_of_business", as_index=False).agg(
            ceded_premium=("ceded_premium", "sum") if "ceded_premium" in df.columns else ("policy_id", "count"),
            retention=("retention", "sum") if "retention" in df.columns else ("policy_id", "count"),
        )
        melted = by_line.melt(
            id_vars="line_of_business", value_vars=["ceded_premium", "retention"],
            var_name="Type", value_name="USD",
        )
        st.plotly_chart(
            px.bar(melted, x="line_of_business", y="USD", color="Type", barmode="group"),
            width='stretch',
        )

    if _has_column(df, "commission"):
        st.markdown("**Commission summary**")
        col1, col2 = st.columns(2)
        col1.metric("Total commission (USD)", f"{df.commission.sum():,.0f}")
        if _has_column(df, "ceded_premium") and df.ceded_premium.sum():
            avg_rate = df.commission.sum() / df.ceded_premium.sum() * 100
            col2.metric("Average commission rate", f"{avg_rate:.1f}%")


def show_reinsurer_performance(df: pd.DataFrame, period_label: str) -> None:
    st.subheader("Reinsurer Performance")
    if df.empty:
        st.warning("No records available for the selected filters.")
        return
    if _missing_data_notice(df):
        return
    if not _has_column(df, "reinsurer"):
        st.info("Upload data with a `reinsurer` column to compare performance across reinsurers.")
        return

    agg_kwargs = {"ceded_premium": ("ceded_premium", "sum")}
    if "claims_paid_usd" in df.columns:
        agg_kwargs["claims_paid_usd"] = ("claims_paid_usd", "sum")
    if "policy_id" in df.columns:
        agg_kwargs["policy_count"] = ("policy_id", "nunique")

    summary = df.groupby("reinsurer", as_index=False).agg(**agg_kwargs)
    if "claims_paid_usd" in summary.columns:
        summary["loss_share"] = (summary["claims_paid_usd"] / summary["ceded_premium"].replace(0, pd.NA) * 100).round(1)
    summary = summary.sort_values("ceded_premium", ascending=False)

    st.dataframe(
        summary.rename(columns={
            "reinsurer": "Reinsurer",
            "ceded_premium": "Ceded premium (USD)",
            "claims_paid_usd": "Claims paid (USD)",
            "policy_count": "Policies",
            "loss_share": "Loss share (%)",
        }),
        hide_index=True, width='stretch',
    )

    selected = st.multiselect(
        "Compare reinsurers",
        summary["reinsurer"].tolist(),
        default=summary["reinsurer"].head(5).tolist(),
    )
    if selected:
        comparison = summary[summary["reinsurer"].isin(selected)]
        st.plotly_chart(
            px.bar(comparison, x="reinsurer", y="ceded_premium", labels={"ceded_premium": "Ceded premium (USD)"}),
            width='stretch',
        )


def show_reinsurers_dashboard(df: pd.DataFrame, period_label: str) -> None:
    st.title("Reinsurers")
    st.caption(f"{period_label} • {len(df):,} records")

    sections = ["Reinsurer Overview", "Treaty Structure", "Reinsurer Performance"]
    choice = st.selectbox("Reinsurers section", sections)

    section_map = {
        "Reinsurer Overview": show_reinsurer_overview,
        "Treaty Structure": show_treaty_structure,
        "Reinsurer Performance": show_reinsurer_performance,
    }
    section_map[choice](df, period_label)

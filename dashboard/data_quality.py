"""Portfolio data-quality controls for the active reporting scope."""

from __future__ import annotations

import pandas as pd
import streamlit as st


REQUIRED_FIELDS = [
    "policy_id", "period", "region", "line_of_business", "gwp_usd",
    "nep_usd", "claims_paid_usd", "loss_ratio", "combined_ratio",
]


def _issue(issue_type: str, severity: str, affected: int, recommendation: str) -> dict[str, object]:
    return {
        "Control": issue_type,
        "Severity": severity,
        "Affected records": int(affected),
        "Recommendation": recommendation,
    }


def show_data_quality_dashboard(df: pd.DataFrame, period_label: str) -> None:
    """Render practical checks without altering the active portfolio data."""
    st.title("Data quality centre")
    st.caption(f"Quality controls for the active portfolio scope • {period_label}")

    if df.empty:
        st.warning("No records are available for the current scope.")
        return

    issues: list[dict[str, object]] = []
    missing_fields = [column for column in REQUIRED_FIELDS if column not in df.columns]
    if missing_fields:
        issues.append(_issue("Required fields", "High", len(df), f"Supply: {', '.join(missing_fields)}."))

    available_required = [column for column in REQUIRED_FIELDS if column in df.columns]
    nulls = df[available_required].isna().sum().sort_values(ascending=False)
    null_count = int(nulls.sum())
    if null_count:
        issues.append(_issue("Missing required values", "High", null_count, "Resolve missing values before portfolio decisions or exports."))

    duplicate_count = int(df["policy_id"].duplicated(keep=False).sum()) if "policy_id" in df.columns else 0
    if duplicate_count:
        issues.append(_issue("Duplicate policy identifiers", "Medium", duplicate_count, "Confirm whether duplicates are valid endorsements or remove duplicate records."))

    invalid_periods = int(pd.to_datetime(df["period"], errors="coerce").isna().sum()) if "period" in df.columns else 0
    if invalid_periods:
        issues.append(_issue("Invalid reporting dates", "High", invalid_periods, "Use a valid ISO date or reporting-period value."))

    unmapped_regions = int((df.get("continent", pd.Series("Other", index=df.index)) == "Other").sum())
    if unmapped_regions:
        issues.append(_issue("Unmapped regions", "Medium", unmapped_regions, "Map the source regions to a supported continent."))

    negative_values = 0
    for column in ("gwp_usd", "nep_usd", "claims_paid_usd", "exposure"):
        if column in df.columns:
            negative_values += int((pd.to_numeric(df[column], errors="coerce") < 0).sum())
    if negative_values:
        issues.append(_issue("Negative financial values", "High", negative_values, "Validate reversals, corrections, and currency signs with the data owner."))

    controls = max(1, len(df) * max(1, len(available_required)))
    deductions = null_count + duplicate_count + invalid_periods + unmapped_regions + negative_values + len(missing_fields) * len(df)
    score = max(0, round(100 * (1 - deductions / controls)))
    score_status = "Ready for decision use" if score >= 95 else "Use with review" if score >= 80 else "Remediation required"

    metrics = st.columns(4)
    metrics[0].metric("Data quality score", f"{score}%", score_status, delta_color="normal", border=True)
    metrics[1].metric("Records in scope", f"{len(df):,}", border=True)
    metrics[2].metric("Controls requiring attention", f"{len(issues):,}", "No issues" if not issues else "Review findings", delta_color="inverse", border=True)
    metrics[3].metric("Field completeness", f"{100 * (1 - null_count / controls):.1f}%", border=True)

    left, right = st.columns([1.25, 1])
    with left:
        with st.container(border=True):
            st.subheader("Control findings")
            if issues:
                findings = pd.DataFrame(issues)
                st.dataframe(findings, hide_index=True, width="stretch")
                st.download_button(
                    "Export quality findings", findings.to_csv(index=False), "portfolio_quality_findings.csv",
                    "text/csv", icon=":material/download:", width="stretch",
                )
            else:
                st.success("All configured quality controls passed for the active portfolio scope.", icon=":material/check_circle:")
    with right:
        with st.container(border=True):
            st.subheader("Completeness by field")
            completeness = pd.DataFrame({
                "Field": available_required,
                "Completeness (%)": [(1 - int(df[field].isna().sum()) / len(df)) * 100 for field in available_required],
            }).sort_values("Completeness (%)")
            st.bar_chart(completeness, x="Field", y="Completeness (%)", horizontal=True)

    with st.container(border=True):
        st.subheader("Source and reconciliation context")
        summary = pd.DataFrame([
            {"Check": "Reporting period", "Value": period_label},
            {"Check": "Date coverage", "Value": f"{pd.to_datetime(df.period, errors='coerce').min():%d %b %Y} – {pd.to_datetime(df.period, errors='coerce').max():%d %b %Y}" if "period" in df.columns else "Unavailable"},
            {"Check": "Gross written premium", "Value": f"USD {df.gwp_usd.sum():,.0f}" if "gwp_usd" in df.columns else "Unavailable"},
            {"Check": "Claims-to-NEP ratio", "Value": f"{(df.claims_paid_usd.sum() / df.nep_usd.sum() * 100):.1f}%" if "claims_paid_usd" in df.columns and "nep_usd" in df.columns and df.nep_usd.sum() else "Unavailable"},
        ])
        st.dataframe(summary, hide_index=True, width="stretch")

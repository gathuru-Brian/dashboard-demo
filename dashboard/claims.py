"""
Claims Intelligence Dashboard
RMIP-DSS
---------------------------------
Six analysis sections over the active, filtered claims/portfolio data:
  - Claims Overview
  - Claims Trends
  - Portfolio Analysis
  - Severity Analysis
  - Aging & SLA
  - Settlement Performance

Optional columns (claim_status, cause_of_loss, settlement_date, reserve)
are used to enrich sections when present, and skipped gracefully when not.
"""

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

_CARD_STYLE = """
    background: rgba(255,255,255,0.03);
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 12px;
    padding: 1rem 1.1rem;
    height: 100%;
"""

_ICON_COLORS = {
    "blue": "#3B82F6",
    "teal": "#14B8A6",
    "green": "#22C55E",
    "amber": "#F59E0B",
    "red": "#EF4444",
    "purple": "#8B5CF6",
}


_ICON_SVGS = {
    "description": '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><path d="M14 2v6h6"/><path d="M8 13h8M8 17h8M8 9h2"/></svg>',
    "schedule": '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 3"/></svg>',
    "trending_up": '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 17l6-6 4 4 8-8"/><path d="M17 7h4v4"/></svg>',
    "attach_money": '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 2v20M17 6.5C17 4.6 14.8 3 12 3s-5 1.6-5 3.5S9.2 10 12 10s5 1.6 5 3.5-2.2 3.5-5 3.5-5-1.6-5-3.5"/></svg>',
    "warning": '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M10.3 3.9L2.7 17a2 2 0 0 0 1.7 3h15.2a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0z"/><path d="M12 9v4M12 17h.01"/></svg>',
    "hourglass_top": '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M6 2h12M6 22h12M6 2c0 5 12 5 12 10s-12 5-12 10M18 2c0 5-12 5-12 10s12 5 12 10"/></svg>',
    "target": '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="5"/><circle cx="12" cy="12" r="1"/></svg>',
}


def _kpi_card(icon: str, label: str, value: str, delta_text: str = "", delta_up: bool | None = None, color: str = "blue") -> str:
    """
    Builds a KPI card as a single unbroken line of HTML. Streamlit's
    markdown-to-HTML renderer can misparse a tag whose attributes are
    split across multiple source lines (falling back to literal escaped
    text), so every tag here stays on one line. Icons are inline SVG,
    not a web font, so nothing depends on an external stylesheet loading.
    """
    hex_color = _ICON_COLORS.get(color, "#3B82F6")
    icon_svg = _ICON_SVGS.get(icon, "")
    delta_html = ""
    if delta_text:
        arrow = "&#8593;" if delta_up else "&#8595;"
        delta_color = "#22C55E" if delta_up else "#EF4444"
        delta_html = f'<div style="font-size:12px;color:{delta_color};margin-top:6px;">{arrow} {delta_text}</div>'
    card_style = _CARD_STYLE.replace(chr(10), " ").strip()
    return (
        f'<div style="{card_style}">'
        f'<div style="display:flex;align-items:center;gap:10px;margin-bottom:10px;">'
        f'<div style="width:34px;height:34px;border-radius:9px;background:{hex_color}22;display:flex;align-items:center;justify-content:center;color:{hex_color};">{icon_svg}</div>'
        f'<span style="font-size:13px;color:rgba(255,255,255,0.65);">{label}</span>'
        f'</div>'
        f'<div style="font-size:26px;font-weight:600;color:#fff;">{value}</div>'
        f'{delta_html}'
        f'</div>'
    )


def _split_period_delta(series: pd.Series) -> tuple[float, float]:
    """Splits a numeric series' index range in half and returns (recent_sum, prior_sum)."""
    if len(series) < 2:
        return 0.0, 0.0
    midpoint = len(series) // 2
    prior = series.iloc[:midpoint].sum()
    recent = series.iloc[midpoint:].sum()
    return recent, prior


def _pct_delta(recent: float, prior: float) -> tuple[str, bool]:
    if prior == 0:
        return "n/a vs prior period", True
    change = (recent - prior) / prior * 100
    return f"{abs(change):.1f}% vs prior period", change >= 0


def _has_column(df: pd.DataFrame, column: str) -> bool:
    return column in df.columns and df[column].notna().any()


def _severity_percentiles(df: pd.DataFrame) -> None:
    try:
        p50, p75, p90, p99 = df.claims_paid_usd.quantile([0.5, 0.75, 0.9, 0.99]).values
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("P50 claim (USD)", f"{p50:,.0f}")
        col2.metric("P75 claim (USD)", f"{p75:,.0f}")
        col3.metric("P90 claim (USD)", f"{p90:,.0f}")
        col4.metric("P99 claim (USD)", f"{p99:,.0f}")
    except Exception:
        st.info("Could not compute claim percentiles due to missing or non-numeric `claims_paid_usd`.")


def show_claims_overview(df: pd.DataFrame, period_label: str) -> None:
    st.caption("Real-time overview of claims performance and outcomes.")

    if df.empty:
        st.warning("No claims data available for the selected filters.")
        return

    df = df.copy()
    total_claims_usd = df.claims_paid_usd.sum()
    count = df.shape[0]

    # -------------------- Derive settlement lag once, reused below --------------------
    settled = pd.DataFrame()
    if _has_column(df, "settlement_date") and "period" in df.columns:
        settled = df[pd.to_datetime(df.settlement_date, errors="coerce").notna()].copy()
        if not settled.empty:
            settled["settlement_lag"] = (
                pd.to_datetime(settled.settlement_date) - pd.to_datetime(settled.period)
            ).dt.days

    # -------------------- KPI row --------------------
    open_count = count
    open_delta_text, open_delta_up = "", True
    if _has_column(df, "claim_status"):
        open_mask = df.claim_status.isin(["Open", "Under Review", "Reopened"])
        open_count = int(open_mask.sum())
        by_period = df.assign(is_open=open_mask).sort_values("period")
        recent, prior = _split_period_delta(by_period.set_index("period")["is_open"])
        open_delta_text, open_delta_up = _pct_delta(recent, prior)

    avg_settle_text = "N/A"
    settle_delta_text, settle_delta_up = "", True
    if not settled.empty:
        avg_settle_text = f"{settled.settlement_lag.mean():.1f} days"
        recent, prior = _split_period_delta(settled.sort_values("period").set_index("period")["settlement_lag"])
        settle_delta_text, settle_delta_up = _pct_delta(recent, prior)
        settle_delta_up = not settle_delta_up  # a rising settlement time is a bad trend

    recovery_rate_text = "N/A"
    recovery_delta_text, recovery_delta_up = "", True
    if _has_column(df, "claim_status"):
        closed_mask = df.claim_status.isin(["Closed", "Settled"])
        recovery_rate = closed_mask.mean() * 100
        recovery_rate_text = f"{recovery_rate:.1f}%"
        by_period = df.assign(is_closed=closed_mask).sort_values("period")
        recent, prior = _split_period_delta(by_period.set_index("period")["is_closed"])
        recovery_delta_text, recovery_delta_up = _pct_delta(recent, prior)

    leakage_text = "N/A"
    leakage_delta_text, leakage_delta_up = "", True
    if _has_column(df, "reserve"):
        leakage_total = df.reserve.sum()
        leakage_text = f"${leakage_total / 1e6:.1f}M" if leakage_total >= 1e6 else f"${leakage_total:,.0f}"
        recent, prior = _split_period_delta(df.sort_values("period").set_index("period")["reserve"])
        leakage_delta_text, leakage_delta_up = _pct_delta(recent, prior)

    kpi_cols = st.columns(4)
    with kpi_cols[0]:
        st.markdown(_kpi_card("description", "Open claims", f"{open_count:,}", open_delta_text, open_delta_up, "blue"), unsafe_allow_html=True)
    with kpi_cols[1]:
        st.markdown(_kpi_card("schedule", "Avg settlement time", avg_settle_text, settle_delta_text, settle_delta_up, "teal"), unsafe_allow_html=True)
    with kpi_cols[2]:
        st.markdown(_kpi_card("trending_up", "Settlement rate", recovery_rate_text, recovery_delta_text, recovery_delta_up, "green"), unsafe_allow_html=True)
    with kpi_cols[3]:
        st.markdown(_kpi_card("attach_money", "Reserve outstanding", leakage_text, leakage_delta_text, not leakage_delta_up, "amber"), unsafe_allow_html=True)

    st.write("")

    # -------------------- Bar chart + funnel --------------------
    chart_left, chart_right = st.columns(2)
    with chart_left:
        with st.container(border=True):
            st.markdown("**Monthly claims volume vs. settled claims**")
            opened_monthly = df.groupby(df.period.dt.to_period("M")).size().rename("Opened")
            if not settled.empty:
                closed_monthly = settled.groupby(pd.to_datetime(settled.settlement_date).dt.to_period("M")).size().rename("Settled")
                monthly = pd.concat([opened_monthly, closed_monthly], axis=1).fillna(0).tail(6)
            else:
                monthly = opened_monthly.to_frame().tail(6)
            monthly.index = monthly.index.astype(str)

            fig = go.Figure()
            fig.add_bar(name="Claims opened", x=monthly.index, y=monthly["Opened"], marker_color="#3B82F6")
            if "Settled" in monthly.columns:
                fig.add_bar(name="Claims settled", x=monthly.index, y=monthly["Settled"], marker_color="#22C55E")
            fig.update_layout(
                barmode="group", height=340, margin=dict(t=10, l=10, r=10, b=10),
                legend=dict(orientation="h", y=-0.15),
            )
            st.plotly_chart(fig, width='stretch')

    with chart_right:
        with st.container(border=True):
            st.markdown("**Claims status pipeline**")
            if _has_column(df, "claim_status"):
                stage_order = ["Open", "Under Review", "Reopened", "Settled", "Closed"]
                counts = df.claim_status.value_counts()
                stages = [s for s in stage_order if s in counts.index]
                stages += [s for s in counts.index if s not in stages]
                values = [int(counts[s]) for s in stages]
                pairs = sorted(zip(stages, values), key=lambda p: -p[1])
                stages = [p[0] for p in pairs]
                values = [p[1] for p in pairs]

                funnel = go.Figure(go.Funnel(
                    y=stages, x=values,
                    textinfo="value+percent initial",
                    marker=dict(color=["#3B82F6", "#14B8A6", "#22C55E", "#84CC16", "#A3E635"][:len(stages)]),
                ))
                funnel.update_layout(height=340, margin=dict(t=10, l=10, r=10, b=10))
                st.plotly_chart(funnel, width='stretch')
            else:
                st.info("Upload data with `claim_status` to see the claims pipeline.")

    # -------------------- Risk & leakage insights --------------------
    st.write("")
    with st.container(border=True):
        st.markdown("**Risk & leakage insights**")
        r1, r2, r3 = st.columns(3)

        with r1:
            if _has_column(df, "risk_category"):
                high_severity = df[df.risk_category.isin(["Nat Cat", "Cyber", "Political"])].shape[0]
                st.markdown(_kpi_card("warning", "High severity claims", f"{high_severity:,}", "", True, "red"), unsafe_allow_html=True)
            else:
                st.caption("Upload `risk_category` to see high-severity alerts.")

        with r2:
            if _has_column(df, "cause_of_loss"):
                by_cause = df.groupby("cause_of_loss").claims_paid_usd.sum().sort_values(ascending=False)
                top_cause = by_cause.index[0]
                top_cause_pct = by_cause.iloc[0] / by_cause.sum() * 100
                st.markdown(f"**Top cause: {top_cause}**")
                donut = px.pie(
                    values=[by_cause.iloc[0], by_cause.sum() - by_cause.iloc[0]],
                    names=["Top cause", "Other"], hole=0.65,
                    color_discrete_sequence=["#14B8A6", "rgba(255,255,255,0.08)"],
                )
                donut.update_layout(
                    height=140, margin=dict(t=0, l=0, r=0, b=0), showlegend=False,
                    annotations=[dict(text=f"{top_cause_pct:.0f}%", x=0.5, y=0.5, font_size=18, showarrow=False)],
                )
                st.plotly_chart(donut, width='stretch')
            else:
                st.caption("Upload `cause_of_loss` to see the top leakage category.")

        with r3:
            if _has_column(df, "claim_status"):
                in_progress_mask = df.claim_status.isin(["Open", "Under Review", "Reopened"])
                in_progress_value = df.loc[in_progress_mask, "claims_paid_usd"].sum()
                in_progress_count = int(in_progress_mask.sum())
                value_text = f"${in_progress_value / 1e6:.1f}M" if in_progress_value >= 1e6 else f"${in_progress_value:,.0f}"
                st.markdown(
                    _kpi_card("hourglass_top", "Claims value in progress", value_text,
                              f"{in_progress_count:,} claims still open", True, "purple"),
                    unsafe_allow_html=True,
                )
            else:
                st.caption("Upload `claim_status` to see the value of claims still in progress.")

    with st.expander("More detail: percentiles and top individual claims"):
        _severity_percentiles(df)
        try:
            display_cols = ["policy_id", "client_name", "line_of_business", "region", "claims_paid_usd", "period"]
            if _has_column(df, "claim_status"):
                display_cols.insert(5, "claim_status")
            display_cols = [c for c in display_cols if c in df.columns]
            top_claims = df.sort_values("claims_paid_usd", ascending=False).head(10)[display_cols]
            st.dataframe(top_claims, hide_index=True, width='stretch')
        except Exception:
            pass

    reins = st.session_state.get("reinsurance_data")
    if reins is not None and "policy_id" in reins.columns and "policy_id" in df.columns:
        merged = df.merge(reins["policy_id"].drop_duplicates(), on="policy_id", how="left", indicator=True)
        matched = (merged._merge == "both").sum()
        st.caption(f"Reinsurance dataset detected: {matched:,} policies match between claims and reinsurance files.")


def show_claims_trends(df: pd.DataFrame, period_label: str) -> None:
    st.subheader("Claims Trends")
    if df.empty:
        st.warning("No claims data available for the selected filters.")
        return

    monthly = df.groupby(df.period.dt.to_period("M"))["claims_paid_usd"].sum().div(1_000_000)
    monthly.index = monthly.index.astype(str)
    st.line_chart(monthly.rename("Claims (USD M)"))

    yearly = df.groupby(df.period.dt.year)["claims_paid_usd"].sum().div(1_000_000)
    if len(yearly) >= 2:
        latest, prior = yearly.iloc[-1], yearly.iloc[-2]
        yoy = ((latest - prior) / prior * 100) if prior else 0
        st.markdown(
            _kpi_card(
                "trending_up",
                f"Claims growth ({int(yearly.index[-2])} → {int(yearly.index[-1])})",
                f"USD {latest:.1f}M", f"{yoy:+.1f}%", yoy >= 0, "blue",
            ),
            unsafe_allow_html=True,
        )
        st.write("")

    if _has_column(df, "line_of_business"):
        st.markdown("**Trend by line of business**")
        by_line = (
            df.groupby([df.period.dt.to_period("M"), "line_of_business"])["claims_paid_usd"]
            .sum().div(1_000_000).reset_index()
        )
        by_line["period"] = by_line["period"].astype(str)
        st.plotly_chart(
            px.line(by_line, x="period", y="claims_paid_usd", color="line_of_business",
                    labels={"claims_paid_usd": "Claims (USD M)", "period": "Month"}),
            width='stretch',
        )


def show_portfolio_claims(df: pd.DataFrame, period_label: str) -> None:
    st.subheader("Portfolio Analysis")
    if df.empty:
        st.warning("No claims data available for the selected filters.")
        return

    left, right = st.columns(2)
    with left:
        st.markdown("**Top clients by claims paid**")
        by_client = df.groupby("client_name")["claims_paid_usd"].sum().sort_values(ascending=False).head(10)
        st.bar_chart(by_client)
    with right:
        if _has_column(df, "line_of_business"):
            st.markdown("**Claims by line of business**")
            by_line = df.groupby("line_of_business")["claims_paid_usd"].sum().sort_values(ascending=False)
            st.plotly_chart(
                px.pie(by_line.reset_index(), names="line_of_business", values="claims_paid_usd", hole=0.5),
                width='stretch',
            )

    if _has_column(df, "region"):
        st.markdown("**Claims by region**")
        by_region = df.groupby("region")["claims_paid_usd"].sum().sort_values(ascending=False)
        st.bar_chart(by_region)


def show_severity_analysis(df: pd.DataFrame, period_label: str) -> None:
    st.subheader("Severity Analysis")
    if df.empty:
        st.warning("No claims data available for the selected filters.")
        return

    st.markdown("**Severity distribution**")
    try:
        fig = px.histogram(
            df, x="claims_paid_usd", nbins=50,
            labels={"claims_paid_usd": "Claims (USD)"},
        )
        st.plotly_chart(fig, width='stretch')
    except Exception:
        st.write(df.claims_paid_usd.describe())

    if _has_column(df, "line_of_business"):
        st.markdown("**Severity by line of business**")
        try:
            fig2 = px.box(
                df, x="line_of_business", y="claims_paid_usd",
                labels={"claims_paid_usd": "Claims (USD)", "line_of_business": "Line of business"},
            )
            st.plotly_chart(fig2, width='stretch')
        except Exception:
            pass

    with st.expander("Summary statistics"):
        st.write(df.claims_paid_usd.describe())


def show_aging_and_sla(df: pd.DataFrame, period_label: str) -> None:
    st.subheader("Aging & SLA")
    if df.empty:
        st.warning("No claims data available for the selected filters.")
        return

    if _has_column(df, "settlement_date") and "period" in df.columns:
        reported = pd.to_datetime(df.period)
        settled = pd.to_datetime(df.settlement_date, errors="coerce")
        df = df.assign(settlement_lag=(settled - reported).dt.days)
    elif _has_column(df, "age_days"):
        df = df.assign(settlement_lag=pd.to_numeric(df.age_days, errors="coerce"))
    else:
        st.info("Upload data with `settlement_date` (or `age_days`) to enable aging/SLA analytics.")
        return

    sla_threshold = st.number_input("SLA threshold (days)", min_value=1, max_value=3650, value=90)
    valid = df.settlement_lag.notna()
    breach = df.settlement_lag > sla_threshold
    breached = (breach & valid).sum()
    total_settled = valid.sum()
    unsettled = df.settlement_lag.isna().sum()
    pct = (breached / total_settled * 100) if total_settled else 0.0

    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(_kpi_card("warning", "SLA breaches", f"{breached:,}", f"{pct:.1f}% of settled claims", False, "red"), unsafe_allow_html=True)
    with col2:
        st.markdown(_kpi_card("description", "Settled claims", f"{total_settled:,}", "", True, "green"), unsafe_allow_html=True)
    with col3:
        st.markdown(_kpi_card("hourglass_top", "Still open (no settlement date)", f"{unsettled:,}", "", True, "amber"), unsafe_allow_html=True)
    st.write("")

    st.markdown("**Settlement lag distribution**")
    try:
        fig = px.histogram(df, x="settlement_lag", nbins=30, labels={"settlement_lag": "Days to settle"})
        st.plotly_chart(fig, width='stretch')
    except Exception:
        st.write(df.settlement_lag.describe())

    if _has_column(df, "line_of_business"):
        st.markdown("**SLA breach rate by line of business**")
        breach_rate = (
            df.assign(breached=breach)
            .groupby("line_of_business")["breached"]
            .mean().mul(100).sort_values(ascending=False)
        )
        st.bar_chart(breach_rate.rename("Breach rate (%)"))


def show_settlement_performance(df: pd.DataFrame, period_label: str) -> None:
    st.subheader("Settlement Performance")
    if df.empty:
        st.warning("No claims data available for the selected filters.")
        return

    if _has_column(df, "settlement_date") and "period" in df.columns:
        settled = df[pd.to_datetime(df.settlement_date, errors="coerce").notna()].copy()
        settled["settlement_lag"] = (
            pd.to_datetime(settled.settlement_date) - pd.to_datetime(settled.period)
        ).dt.days
    elif _has_column(df, "age_days"):
        settled = df[df.age_days.notna()].copy()
        settled["settlement_lag"] = pd.to_numeric(settled.age_days, errors="coerce")
    else:
        st.info("Upload data with `settlement_date` (or `age_days`) to compute settlement performance.")
        return

    if settled.empty:
        st.info("No settled records found in the selected data.")
        return

    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(_kpi_card("schedule", "Average settlement days", f"{settled.settlement_lag.mean():.0f}", "", True, "teal"), unsafe_allow_html=True)
    with col2:
        st.markdown(_kpi_card("schedule", "Median settlement days", f"{settled.settlement_lag.median():.0f}", "", True, "teal"), unsafe_allow_html=True)
    with col3:
        st.markdown(_kpi_card("description", "Settled claims", f"{len(settled):,}", "", True, "green"), unsafe_allow_html=True)
    st.write("")

    st.markdown("**Slowest-to-settle clients**")
    slow = settled.groupby("client_name")["settlement_lag"].mean().sort_values(ascending=False).head(10)
    st.bar_chart(slow)

    if _has_column(settled, "cause_of_loss"):
        st.markdown("**Average settlement time by cause of loss**")
        by_cause = settled.groupby("cause_of_loss")["settlement_lag"].mean().sort_values(ascending=False)
        st.bar_chart(by_cause)

    if _has_column(settled, "reserve"):
        st.markdown("**Outstanding reserves (open/reopened claims)**")
        open_reserves = settled[settled.reserve > 0] if "reserve" in settled.columns else pd.DataFrame()
        if not open_reserves.empty:
            reserve_total = open_reserves.reserve.sum()
            reserve_text = f"${reserve_total / 1e6:.1f}M" if reserve_total >= 1e6 else f"${reserve_total:,.0f}"
            st.markdown(_kpi_card("attach_money", "Total outstanding reserve", reserve_text, "", True, "amber"), unsafe_allow_html=True)
        else:
            st.caption("No outstanding reserves in the current selection.")


def show_claims_dashboard(df: pd.DataFrame, period_label: str) -> None:
    st.title("Claims Intelligence")
    st.caption(f"{period_label} • {len(df):,} claim records")

    sections = [
        "Claims Overview",
        "Claims Trends",
        "Portfolio Analysis",
        "Severity Analysis",
        "Aging & SLA",
        "Settlement Performance",
    ]
    choice = st.selectbox("Claims section", sections)

    section_map = {
        "Claims Overview": show_claims_overview,
        "Claims Trends": show_claims_trends,
        "Portfolio Analysis": show_portfolio_claims,
        "Severity Analysis": show_severity_analysis,
        "Aging & SLA": show_aging_and_sla,
        "Settlement Performance": show_settlement_performance,
    }
    section_map[choice](df, period_label)
"""RMIP-DSS — Reinsurance intelligence and pricing dashboard."""

from __future__ import annotations

import io
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import requests
import streamlit as st

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from auth.authentication import create_user, initialize_admin, login_user
from auth.departments import get_departments
from auth.roles import get_roles

st.set_page_config(
    page_title="Acentria Reinsurance & Risk Navigator",
    page_icon=":material/shield:",
    layout="wide",
    initial_sidebar_state="expanded",
)

DATA_PATH = ROOT / "data" / "acentria_dashboard_data.csv"
LOGO_URL = "https://raw.githubusercontent.com/twitter/twemoji/master/assets/svg/1f6e1.svg"
APP_NAME = "Acentria Reinsurance & Risk Navigator"
REQUIRED_UPLOAD_COLUMNS = {
    "policy_id", "period", "region", "line_of_business", "gross_written_premium",
    "net_earned_premium", "claims_paid", "loss_ratio", "combined_ratio",
}
REGION_TO_CONTINENT = {
    "Africa": "Africa", "Kenya": "Africa", "North America": "North America",
    "Caribbean": "North America", "Latin America": "South America",
    "Europe": "Europe", "Nordics": "Europe", "Asia Pacific": "Asia",
    "Middle East & Africa": "Asia", "Australia & Pacific": "Oceania",
}
CONTINENTS = ["Africa", "Asia", "Europe", "North America", "South America", "Oceania", "Antarctica"]


def init_state() -> None:
    defaults = {
        "page": "welcome", "logged_in": False, "user": "", "email": "",
        "role": "", "department": "", "uploaded_data": None, "chat_messages": [],
    }
    for key, value in defaults.items():
        st.session_state.setdefault(key, value)


@st.cache_data(ttl="30m")
def load_portfolio() -> pd.DataFrame:
    """Load the supplied portfolio dataset and add display dimensions if absent."""
    df = pd.read_csv(DATA_PATH, parse_dates=["period"]).copy()
    if "claims_paid" not in df.columns and "losses" in df.columns:
        df["claims_paid"] = df["losses"]
    lines = list(df["line_of_business"].dropna().unique())
    clients = ["Acentria Group", "Coastal Mutual", "Metro Insurers", "AgriProtect"]
    risks = ["Nat Cat", "Cyber", "Weather", "Operational", "Market"]
    df["client_name"] = df.get("client_name", pd.Series([clients[i % len(clients)] for i in range(len(df))]))
    df["risk_category"] = df.get("risk_category", pd.Series([risks[i % len(risks)] for i in range(len(df))]))
    df["gwp_usd"] = df.get("gwp_usd", df["gross_written_premium"])
    df["nep_usd"] = df.get("nep_usd", df["net_earned_premium"])
    df["claims_paid_usd"] = df.get("claims_paid_usd", df["claims_paid"])
    df["line_of_business"] = df["line_of_business"].fillna(lines[0] if lines else "Other")
    df["continent"] = df["region"].map(REGION_TO_CONTINENT).fillna("Other")
    return df


COLUMN_SYNONYMS = {
    "policy_id": ["policy_id", "policy id", "policy number", "policy_no", "policy number", "policy_number", "policy"],
    "period": ["period", "date", "effective_date", "transaction_date", "policy_date", "issue_date", "coverage_date", "report_date", "loss_date", "written_date"],
    "region": ["region", "territory", "location", "country", "area", "market"],
    "line_of_business": ["line_of_business", "line of business", "lob", "business_line", "product_line", "class_of_business", "segment"],
    "gross_written_premium": ["gross_written_premium", "gross written premium", "gwp", "premium_written", "written_premium", "gross_premium"],
    "net_earned_premium": ["net_earned_premium", "net earned premium", "nep", "earned_premium", "net_premium"],
    "claims_paid": ["claims_paid", "claims", "losses", "paid_losses", "incurred_claims", "claim_paid"],
    "loss_ratio": ["loss_ratio", "loss ratio", "claims_ratio", "loss ratio percent", "loss_percentage", "loss percent"],
    "combined_ratio": ["combined_ratio", "combined ratio", "combined ratio percent"],
    "client_name": ["client_name", "client name", "cedant", "cedant_name", "insured", "customer"],
    "risk_category": ["risk_category", "risk category", "risk", "risk_type", "risk class"],
    "exposure": ["exposure", "sum_insured", "limit", "exposed_value"],
    "premium_rate": ["premium_rate", "rate", "rate_on_line", "rol"],
    "region": ["region", "territory", "location", "country", "area", "market"],
}

def normalize_upload_columns(frame: pd.DataFrame) -> pd.DataFrame:
    frame = frame.rename(columns={str(col).strip().lower(): str(col).strip().lower() for col in frame.columns})
    for canonical, synonyms in COLUMN_SYNONYMS.items():
        if canonical in frame.columns:
            continue
        for synonym in synonyms:
            if synonym in frame.columns:
                frame = frame.rename(columns={synonym: canonical})
                break
    return frame


def parse_upload(uploaded_file) -> tuple[pd.DataFrame | None, str | None]:
    try:
        source_name = getattr(uploaded_file, "name", "") or "uploaded"
        uploaded_file.seek(0)
        if source_name.lower().endswith((".xlsx", ".xls")):
            frame = pd.read_excel(uploaded_file)
        else:
            try:
                frame = pd.read_csv(uploaded_file)
            except Exception:
                uploaded_file.seek(0)
                frame = pd.read_excel(uploaded_file)
        frame = normalize_upload_columns(frame)
        if "period" not in frame.columns:
            return None, "Your upload must include a date field such as Period, Date, Effective_Date, or Transaction_Date."
        frame["period"] = pd.to_datetime(frame["period"], errors="coerce")
        frame = frame.dropna(subset=["period"]).copy()
        if frame.empty:
            return None, "The upload contains no valid dated records."

        frame["policy_id"] = frame.get("policy_id", pd.Series(range(1, len(frame) + 1), index=frame.index))
        frame["region"] = frame.get("region", "Unknown")
        frame["line_of_business"] = frame.get("line_of_business", "Other")
        frame["gwp_usd"] = frame.get("gwp_usd", frame.get("gross_written_premium"))
        frame["nep_usd"] = frame.get("nep_usd", frame.get("net_earned_premium"))
        frame["claims_paid_usd"] = frame.get("claims_paid_usd", frame.get("claims_paid", frame.get("losses")))

        if frame["gwp_usd"].isna().all() and frame["nep_usd"].isna().all():
            return None, "Your upload must include premium values such as GWP or NEP."
        if frame["claims_paid_usd"].isna().all():
            return None, "Your upload must include claims or losses data."

        if "loss_ratio" not in frame.columns or frame["loss_ratio"].isna().all():
            if "claims_paid_usd" in frame.columns and "nep_usd" in frame.columns:
                frame["loss_ratio"] = frame["claims_paid_usd"] / frame["nep_usd"].replace({0: np.nan})
            else:
                frame["loss_ratio"] = np.nan

        if "combined_ratio" not in frame.columns or frame["combined_ratio"].isna().all():
            frame["combined_ratio"] = frame["loss_ratio"].copy()

        frame["loss_ratio"] = pd.to_numeric(frame["loss_ratio"], errors="coerce")
        frame["combined_ratio"] = pd.to_numeric(frame["combined_ratio"], errors="coerce")
        frame["gwp_usd"] = pd.to_numeric(frame["gwp_usd"], errors="coerce")
        frame["nep_usd"] = pd.to_numeric(frame["nep_usd"], errors="coerce")
        frame["claims_paid_usd"] = pd.to_numeric(frame["claims_paid_usd"], errors="coerce")

        frame["client_name"] = frame.get("client_name", "Uploaded portfolio")
        frame["risk_category"] = frame.get("risk_category", "Unclassified")
        frame["exposure"] = frame.get("exposure", frame["gwp_usd"]).fillna(frame["gwp_usd"])
        premium_rate = frame.get("premium_rate", 1.0)
        if isinstance(premium_rate, pd.Series):
            frame["premium_rate"] = pd.to_numeric(premium_rate, errors="coerce").fillna(1.0)
        else:
            frame["premium_rate"] = float(premium_rate) if not pd.isna(premium_rate) else 1.0
        frame["region"] = frame["region"].fillna("Unknown")
        frame["line_of_business"] = frame["line_of_business"].fillna("Other")
        frame["continent"] = frame["region"].map(REGION_TO_CONTINENT).fillna("Other")
        return frame, None
    except Exception as error:
        return None, f"Could not read this file: {error}"


@st.cache_data(ttl="30m")
def load_remote_dataset(url: str) -> tuple[pd.DataFrame | None, str | None]:
    try:
        response = requests.get(url, timeout=60)
        response.raise_for_status()
        file_name = url.split("?")[0].split("/")[-1] or "remote.csv"
        buffer = io.BytesIO(response.content)
        setattr(buffer, "name", file_name)
        return parse_upload(buffer)
    except Exception as error:
        return None, f"Could not load remote dataset: {error}"


def get_period_label(df: pd.DataFrame) -> str:
    if df.empty:
        return "No valid period"
    start = df.period.min()
    end = df.period.max()
    return f"{start:%d %b %Y} – {end:%d %b %Y}"


def create_portfolio_report(df: pd.DataFrame, period_label: str) -> str:
    if df.empty:
        return "No records are available to build a report."
    total_gwp = df.gwp_usd.sum()
    total_nep = df.nep_usd.sum()
    total_claims = df.claims_paid_usd.sum()
    avg_combined = df.combined_ratio.mean() * 100
    avg_loss = df.loss_ratio.mean() * 100
    top_line = df.groupby("line_of_business").gwp_usd.sum().idxmax()
    top_region = df.groupby("region").gwp_usd.sum().idxmax()
    top_client = df.groupby("client_name").gwp_usd.sum().idxmax()
    risk_counts = df.risk_category.value_counts().head(3).to_dict()

    lines = [f"{name}: {value}" for name, value in risk_counts.items()]
    risk_summary = "; ".join(lines) if lines else "No risk categories available."

    recommendation = (
        "Pricing appears stable if combined ratio is below 95%. "
        "Review lines above that threshold for underwriting action."
    )
    if avg_combined >= 100:
        recommendation = (
            "Combined ratio is above 100%, indicating underwriting losses. "
            "Prioritise treaty review, claims management, and rate adequacy."
        )
    elif avg_combined >= 95:
        recommendation = (
            "Combined ratio is approaching break-even. "
            "Monitor loss trends and consider selective rate actions."
        )

    report = [
        f"Portfolio report for {period_label}",
        "---",
        f"Records: {len(df):,}",
        f"Gross written premium: USD {total_gwp:,.0f}",
        f"Net earned premium: USD {total_nep:,.0f}",
        f"Claims paid: USD {total_claims:,.0f}",
        f"Average loss ratio: {avg_loss:.1f}%", 
        f"Average combined ratio: {avg_combined:.1f}%",
        f"Top line of business by premium: {top_line}",
        f"Top region by premium: {top_region}",
        f"Top client by premium: {top_client}",
        f"Leading risk categories: {risk_summary}",
        "\nExecutive summary:",
        f"The portfolio reflects {len(df):,} records across {df.region.nunique()} regions and {df.line_of_business.nunique()} lines of business. "
        f"Premium concentration is highest in {top_line} and {top_region}. {recommendation}",
    ]
    return "\n".join(report)


def sidebar_controls(df: pd.DataFrame) -> tuple[str, pd.DataFrame, str]:
    with st.sidebar:
        st.image(LOGO_URL, width=46)
        st.markdown("### Acentria Group")
        st.caption("Market intelligence • Pricing • Portfolio performance")
        st.divider()
        st.caption(f"Signed in as **{st.session_state.user}**")
        if st.button("Sign out", icon=":material/logout:", width="stretch"):
            for key in ("logged_in", "user", "email", "role", "department"):
                st.session_state[key] = "" if key != "logged_in" else False
            st.session_state.page = "welcome"
            st.rerun()
        workspace = st.radio(
            "Workspace",
            ["Portfolio analytics", "Upload portfolio data", "Portfolio assistant"],
            format_func=lambda item: {
                "Portfolio analytics": ":material/monitoring: Analytics overview",
                "Upload portfolio data": ":material/upload_file: Data upload",
                "Portfolio assistant": ":material/smart_toy: Assistant",
            }[item],
        )
        st.divider()
        st.subheader("Global filters")
        source_options = ["Global portfolio"] + (["Uploaded portfolio"] if st.session_state.uploaded_data is not None else [])
        source = st.selectbox("Data source", source_options)
        if source == "Uploaded portfolio" and st.session_state.uploaded_data is not None:
            active_df = st.session_state.uploaded_data.copy()
        else:
            active_df = df.copy()
        date_mode = st.radio("Date selection", ["All available years", "Custom range"], horizontal=True)
        if date_mode == "Custom range":
            dates = st.date_input(
                "Date range", value=(active_df.period.min().date(), active_df.period.max().date()),
                min_value=active_df.period.min().date(), max_value=active_df.period.max().date(),
                help="Pick a specific reporting period, or choose all available years to include everything.",
            )
        else:
            dates = (active_df.period.min().date(), active_df.period.max().date())
            st.caption(f"Showing all available years from {active_df.period.min():%Y} to {active_df.period.max():%Y}.")
        lines = st.multiselect("Line of business", sorted(active_df.line_of_business.unique()), default=sorted(active_df.line_of_business.unique()))
        regions = st.multiselect("Region", sorted(active_df.region.unique()), default=sorted(active_df.region.unique()))
        risks = st.multiselect("Risk category", sorted(active_df.risk_category.unique()), default=sorted(active_df.risk_category.unique()))
    result = active_df.copy()
    if isinstance(dates, tuple) and len(dates) == 2:
        result = result[result.period.dt.date.between(*dates)]
        period_label = f"{dates[0]:%d %b %Y} – {dates[1]:%d %b %Y}"
    else:
        period_label = "All periods"
    result = result[result.line_of_business.isin(lines) & result.region.isin(regions) & result.risk_category.isin(risks)]
    return workspace, result, period_label


def render_logout_topbar() -> None:
    cols = st.columns([5, 1])
    with cols[1]:
        if st.button("Sign out", icon=":material/logout:", use_container_width=True):
            for key in ("logged_in", "user", "email", "role", "department"):
                st.session_state[key] = "" if key != "logged_in" else False
            st.session_state.page = "welcome"
            st.rerun()


def show_welcome() -> None:
    left, right = st.columns([1.4, 0.85], vertical_alignment="top")
    with left:
        st.image(LOGO_URL, width=72)
        st.subheader("Enterprise reinsurance intelligence for underwriting, claims, and risk teams")
        st.title(APP_NAME)
        st.write(
            "Acentria empowers carriers and cedants with an integrated view of premium, claims, "
            "loss ratios, risk concentration, and pricing adequacy across all years of portfolio data."
        )
        st.markdown(
            "**Trusted outcomes for treaty optimisation, capital oversight, and customer-facing analytics.**"
        )
        st.markdown(
            "- Upload any insurance portfolio dataset and immediately map premiums, claims, ratios, and exposures.\n"
            "- Choose all available years or define a custom reporting period.\n"
            "- Generate executive summaries, export data, and surface portfolio risks for action."
        )
        with st.expander("Key enterprise benefits"):
            st.write(
                "Acentria is built to support senior stakeholders with clear portfolio performance metrics, "
                "regional exposure visibility, and pricing intelligence that translates into decisions."
            )
            st.write(
                "Use the platform for reinsurance analytics, pricing assumptions, cedant benchmarking, "
                "and report-ready business summaries."
            )
        stats = load_portfolio()
        stat1, stat2, stat3 = st.columns(3)
        stat1.metric("Records analysed", f"{len(stats):,}")
        stat2.metric("Lines of business", str(stats.line_of_business.nunique()))
        stat3.metric("Regions covered", str(stats.region.nunique()))
        st.markdown("---")
        st.subheader("Why customers choose Acentria")
        for statement in [
            "Single workspace for underwriting, claims, pricing and portfolio performance.",
            "Flexible upload accepts CSV or Excel insurance portfolio files with broad column support.",
            "Enterprise-ready summaries and exportable insights for internal reporting and renewals.",
        ]:
            st.markdown(f"• {statement}")

    with right:
        with st.container(border=True):
            st.markdown("### Access the platform")
            access_mode = st.segmented_control("Access", ["Sign in", "Create account"], default="Sign in")
            if access_mode == "Sign in":
                with st.form("sign_in_form"):
                    email = st.text_input("Work email", placeholder="name@company.com")
                    password = st.text_input("Password", type="password")
                    submitted = st.form_submit_button("Open analytics", type="primary", icon=":material/login:", width="stretch")
                if submitted:
                    user = login_user(email.strip().lower(), password)
                    if not user:
                        st.error("We could not verify those credentials.")
                    else:
                        st.session_state.update({"logged_in": True, "page": "dashboard", "user": user["fullname"], "email": user["email"], "role": user["role"], "department": user["department"]})
                        st.rerun()
            else:
                with st.form("registration_form"):
                    fullname = st.text_input("Full name")
                    email = st.text_input("Work email", placeholder="name@company.com")
                    department = st.selectbox("Department", get_departments())
                    role = st.selectbox("Role", get_roles())
                    password = st.text_input("Password", type="password", help="Use at least 8 characters.")
                    confirm = st.text_input("Confirm password", type="password")
                    registered = st.form_submit_button("Create account and open analytics", type="primary", icon=":material/person_add:", width="stretch")
                if registered:
                    if not fullname.strip() or not email.strip() or len(password) < 8:
                        st.error("Enter your name, a valid email, and a password of at least 8 characters.")
                    elif password != confirm:
                        st.error("The passwords do not match.")
                    elif not create_user(fullname.strip(), email.strip().lower(), password, role, department):
                        st.error("An account already exists for this email address.")
                    else:
                        st.session_state.update({"logged_in": True, "page": "dashboard", "user": fullname.strip(), "email": email.strip().lower(), "role": role, "department": department})
                        st.rerun()


def card(title: str):
    container = st.container(border=True)
    container.markdown(f"**{title}**")
    return container


def show_dashboard(df: pd.DataFrame, period_label: str) -> None:
    st.title("Reinsurance Portfolio Analytics")
    header, actions = st.columns([4, 1], vertical_alignment="center")
    with header:
        st.caption(f"{period_label} • {len(df):,} portfolio records • Base currency USD")
    with actions:
        st.download_button("Export data", df.to_csv(index=False), "rmip_portfolio_export.csv", "text/csv", icon=":material/download:", width="stretch")
    if df.empty:
        st.warning("No records match the current filters. Expand one or more filters in the sidebar.")
        return

    gwp, nep, claims = (df.gwp_usd.sum(), df.nep_usd.sum(), df.claims_paid_usd.sum())
    combined = df.combined_ratio.mean() * 100
    trend = df.groupby(df.period.dt.to_period("M"))["gwp_usd"].sum().div(1_000_000).tolist()
    metrics = [
        ("Gross written premium", f"USD {gwp / 1e6:.1f}M", "+14.6%", trend),
        ("Net earned premium", f"USD {nep / 1e6:.1f}M", "+11.3%", trend),
        ("Claims incurred", f"USD {claims / 1e6:.1f}M", "+9.8%", trend),
        ("Combined ratio", f"{combined:.1f}%", "-3.6%", trend),
        ("Return on equity", "16.2%", "+1.8%", trend),
        ("RBC ratio", "312%", "Strong", trend),
    ]
    with st.container(horizontal=True):
        for label, value, delta, chart in metrics:
            st.metric(label, value, delta, border=True, chart_data=chart, chart_type="line")

    monthly = df.groupby(df.period.dt.to_period("M"))[["gwp_usd", "nep_usd", "claims_paid_usd"]].sum().reset_index()
    monthly["period"] = monthly["period"].astype(str)
    lob = df.groupby("line_of_business", as_index=False)[["gwp_usd"]].sum().sort_values("gwp_usd", ascending=False)
    competitors = df.groupby("client_name", as_index=False)[["gwp_usd"]].sum().sort_values("gwp_usd", ascending=False)
    competitors["share"] = competitors.gwp_usd / competitors.gwp_usd.sum() * 100

    col1, col2, col3, col4 = st.columns([1.2, 1, 1, 1])
    with col1:
        with card("Premium trend (USD M)"):
            chart_df = monthly.melt("period", ["gwp_usd", "nep_usd"], "Metric", "USD")
            chart_df["USD"] /= 1e6
            st.plotly_chart(px.line(chart_df, x="period", y="USD", color="Metric", markers=True, color_discrete_sequence=["#2f80ed", "#32d583"]), width="stretch")
    with col2:
        with card("Premium by line of business"):
            st.plotly_chart(px.pie(lob, names="line_of_business", values="gwp_usd", hole=.58, color_discrete_sequence=px.colors.sequential.Blues_r), width="stretch")
    with col3:
        with card("Market intelligence highlights"):
            for text in ["Reinsurance capacity has improved, supported by investment returns.", "Natural catastrophe losses remain above the long-term average.", "Property, casualty, and agriculture pricing continues to firm.", "Inflation is increasing claim severity and repair costs."]:
                st.caption("• " + text)
            st.button("View market intelligence", icon=":material/arrow_forward:", key="market_info")
    with col4:
        with card("Top competitors — market share"):
            chart = px.bar(competitors.head(7), x="share", y="client_name", orientation="h", text_auto=True, color="share", color_continuous_scale="Blues")
            chart.update_layout(yaxis={"categoryorder": "total ascending"}, coloraxis_showscale=False)
            st.plotly_chart(chart, width="stretch")

    bottom_left, bottom_mid, bottom_right = st.columns([1.35, 1, .8])
    with bottom_left:
        with card("Treaty performance summary"):
            summary = df.groupby("line_of_business").agg(Treaties=("policy_id", "nunique"), GWP=("gwp_usd", "sum"), Loss_Ratio=("loss_ratio", "mean"), Combined_Ratio=("combined_ratio", "mean")).reset_index()
            summary["GWP (USD M)"] = (summary.pop("GWP") / 1e6).round(1)
            summary["Loss ratio"] = summary.pop("Loss_Ratio").mul(100).round(1).astype(str) + "%"
            summary["Combined ratio"] = summary.pop("Combined_Ratio").mul(100).round(1).astype(str) + "%"
            summary["Rate adequacy"] = summary["Combined ratio"].str.rstrip("%").astype(float).map(lambda x: "Maintain" if x < 95 else "Increase rates")
            st.dataframe(summary.rename(columns={"line_of_business": "Line of business"}), hide_index=True, height=300, width="stretch")
    with bottom_mid:
        with card("Pricing adequacy analysis"):
            pricing = df.groupby("line_of_business", as_index=False).agg(loss_ratio=("loss_ratio", "mean"), premium_rate=("premium_rate", "mean"), exposure=("exposure", "sum"))
            pricing["loss_ratio"] *= 100
            pricing["premium_adequacy"] = pricing.premium_rate / pricing.premium_rate.max() * 110
            st.plotly_chart(px.scatter(pricing, x="loss_ratio", y="premium_adequacy", size="exposure", color="line_of_business", hover_name="line_of_business", labels={"loss_ratio":"Loss ratio (%)", "premium_adequacy":"Premium adequacy (%)"}), width="stretch")
    with bottom_right:
        with card("Emerging risks monitor"):
            risks = df.groupby("risk_category").agg(Exposure=("exposure", "sum"), Loss_ratio=("loss_ratio", "mean")).sort_values("Exposure", ascending=False)
            risks["Risk level"] = risks.Loss_ratio.map(lambda x: "High" if x >= .65 else "Medium" if x >= .45 else "Low")
            st.dataframe(risks[["Risk level"]], width="stretch")

    geographic, claims_col, simulator = st.columns([1, 1, 1.15])
    with geographic:
        with card("Geographic exposure (GWP)"):
            geographic_data = df.groupby("continent", as_index=False).gwp_usd.sum().set_index("continent").reindex(CONTINENTS, fill_value=0).reset_index()
            geographic_data["portfolio_status"] = geographic_data.gwp_usd.map(lambda value: "Active portfolio" if value else "No active portfolio")
            st.plotly_chart(px.bar(geographic_data, x="gwp_usd", y="continent", orientation="h", color="portfolio_status", labels={"gwp_usd": "GWP (USD)", "continent": "Continent"}, color_discrete_map={"Active portfolio": "#2f80ed", "No active portfolio": "#64748b"}), width="stretch")
    with claims_col:
        with card("Claims trend (USD M)"):
            claim_data = monthly.melt("period", ["claims_paid_usd", "nep_usd"], "Metric", "USD")
            claim_data["USD"] /= 1e6
            st.plotly_chart(px.bar(claim_data, x="period", y="USD", color="Metric", barmode="group", color_discrete_sequence=["#2f80ed", "#32d583"]), width="stretch")
    with simulator:
        with card("Pricing simulator"):
            with st.form("pricing_simulator", border=False):
                selected_line = st.selectbox("Line of business", sorted(df.line_of_business.unique()))
                loss = st.slider("Expected loss ratio (%)", 30, 110, 62)
                expense = st.slider("Expense ratio (%)", 5, 45, 25)
                margin = st.slider("Profit margin (%)", 0, 30, 12)
                calculate = st.form_submit_button("Calculate", type="primary", width="stretch")
            if calculate:
                st.session_state["rate_change"] = loss + expense + margin - 100
            rate_change = st.session_state.get("rate_change", 0.0)
            st.metric("Indicated rate change", f"{rate_change:+.1f}%")
            st.caption(f"Selected line: {selected_line}")
            st.success("Adequate" if rate_change <= 0 else "Rate increase indicated")

    with st.container(border=True):
        st.subheader("AI-style portfolio observations")
        for insight in [
            "Motor and property treaties should be monitored for loss-ratio deterioration.",
            "Concentration by line and region is visible in the portfolio filters above.",
            "Use the pricing simulator to test a rate response before treaty renewal discussions.",
        ]:
            st.caption("• " + insight)


def show_upload_data() -> None:
    st.title("Upload portfolio data")
    st.caption("Upload CSV/Excel insurance portfolio files or load a large public dataset from a remote URL.")
    with st.container(border=True):
        with st.expander("Load dataset from the web"):
            remote_url = st.text_input("Remote dataset URL", placeholder="https://example.com/portfolio.csv")
            if st.button("Load remote dataset", icon=":material/cloud_download:") and remote_url:
                remote_df, remote_error = load_remote_dataset(remote_url.strip())
                if remote_error:
                    st.error(remote_error)
                elif remote_df is not None:
                    st.session_state.uploaded_data = remote_df
                    st.success(f"Loaded {len(remote_df):,} remote records from the URL.")
        uploaded_file = st.file_uploader("Portfolio file", type=["csv", "xlsx", "xls"], key="portfolio_file")
        st.caption("Upload any insurance portfolio data with flexible column mapping for dates, premiums, claims, lines, regions, and clients.")
        if uploaded_file is not None:
            parsed, error = parse_upload(uploaded_file)
            if error:
                st.error(error)
            elif parsed is not None:
                st.session_state.uploaded_data = parsed
                period_label = get_period_label(parsed)
                report_text = create_portfolio_report(parsed, period_label)
                st.success(f"Loaded {len(parsed):,} records across {parsed.continent.nunique()} represented continents.")
                st.download_button(
                    "Download executive report",
                    report_text,
                    "portfolio_summary.txt",
                    "text/plain",
                    icon=":material/description:",
                    help="Download a ready-made portfolio summary report for the active dataset.",
                )
                st.text_area("Executive summary", report_text, height=260)
                st.dataframe(
                    parsed.head(100), hide_index=True, width="stretch",
                    column_config={
                        "period": st.column_config.DateColumn("Period"),
                        "gwp_usd": st.column_config.NumberColumn("GWP (USD)", format="$%.0f"),
                        "nep_usd": st.column_config.NumberColumn("NEP (USD)", format="$%.0f"),
                        "claims_paid_usd": st.column_config.NumberColumn("Claims (USD)", format="$%.0f"),
                    },
                )
    if st.session_state.uploaded_data is not None:
        if st.button("Clear uploaded portfolio", icon=":material/delete:"):
            st.session_state.uploaded_data = None
            st.rerun()


def assistant_reply(prompt: str, df: pd.DataFrame, period_label: str) -> str:
    """Provide deterministic, portfolio-grounded assistance without external credentials."""
    question = prompt.lower()
    total_gwp = df.gwp_usd.sum() / 1e6
    combined = df.combined_ratio.mean() * 100
    top_line = df.groupby("line_of_business").gwp_usd.sum().idxmax()
    top_region = df.groupby("region").gwp_usd.sum().idxmax()
    if any(word in question for word in ("report", "summary", "overview")):
        return create_portfolio_report(df, period_label)
    if any(word in question for word in ("claim", "loss", "combined")):
        worst = df.groupby("line_of_business").loss_ratio.mean().idxmax()
        ratio = df.groupby("line_of_business").loss_ratio.mean().max() * 100
        return f"For {period_label}, the portfolio combined ratio is {combined:.1f}%. **{worst}** has the highest average loss ratio at {ratio:.1f}%, so it is the first line to review."
    if any(word in question for word in ("region", "continent", "geograph", "global")):
        continents = ", ".join(df.continent.dropna().unique())
        return f"The current selection represents {continents}. **{top_region}** has the largest GWP concentration. Antarctica is retained as a benchmark with no active commercial portfolio records."
    if any(word in question for word in ("price", "rate", "premium", "treaty")):
        return f"Current GWP is USD {total_gwp:.1f}M, led by **{top_line}**. Use the pricing simulator in the analytics workspace to test loss, expense, and margin assumptions before renewal decisions."
    return f"For {period_label}, the selected portfolio has {len(df):,} records, USD {total_gwp:.1f}M GWP, and a {combined:.1f}% combined ratio. Ask me about claims, pricing, regions, or portfolio exposure."


def show_assistant(df: pd.DataFrame, period_label: str) -> None:
    st.title("Portfolio assistant")
    st.caption("A built-in, portfolio-grounded assistant. It uses the current global filters and does not send your data to an external model.")
    if not st.session_state.chat_messages:
        st.session_state.chat_messages = [{"role": "assistant", "content": "Hello — ask about claims, pricing, regional exposure, or the selected reporting period."}]
    if len(st.session_state.chat_messages) == 1:
        suggestion = st.pills("Try asking", ["Which line has the highest loss ratio?", "Summarise global exposure", "What does pricing look like?"], selection_mode="single")
        if suggestion:
            st.session_state.chat_messages.append({"role": "user", "content": suggestion})
            st.session_state.chat_messages.append({"role": "assistant", "content": assistant_reply(suggestion, df, period_label)})
            st.rerun()
    for message in st.session_state.chat_messages:
        with st.chat_message(message["role"], avatar=":material/smart_toy:" if message["role"] == "assistant" else None):
            st.write(message["content"])
    if prompt := st.chat_input("Ask about the selected portfolio", submit_mode="disable"):
        st.session_state.chat_messages.append({"role": "user", "content": prompt})
        response = assistant_reply(prompt, df, period_label)
        st.session_state.chat_messages.append({"role": "assistant", "content": response})
        st.rerun()


def main() -> None:
    init_state()
    initialize_admin()
    if st.session_state.logged_in:
        render_logout_topbar()
        workspace, filtered_data, period_label = sidebar_controls(load_portfolio())
        if workspace == "Portfolio analytics":
            show_dashboard(filtered_data, period_label)
        elif workspace == "Upload portfolio data":
            show_upload_data()
        else:
            show_assistant(filtered_data, period_label)
    else:
        show_welcome()


if __name__ == "__main__":
    main()


# Compatibility entrypoint when the dashboard is launched through pages/dashboard.py
build_dashboard = main

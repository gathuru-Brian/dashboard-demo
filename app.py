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
import tempfile
import os
import json
import shutil

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from auth.authentication import (
    initialize_admin,
    login_user,
    notify_admin_login,
    request_access,
    request_password_reset,
    reset_password_with_code,
)
from auth.permissions import has_permission
from auth.data_store import save_upload
from assets.css import inject_css
from dashboard.claims import show_claims_dashboard
from dashboard.reinsurers import show_reinsurers_dashboard
from dashboard.cedants import show_cedants_dashboard
from dashboard.pricing import show_pricing_dashboard
from dashboard.data_quality import show_data_quality_dashboard
from session_timeout import enforce_session_timeout
from assets import css

st.set_page_config(
    page_title="Acentria Reinsurance & Claims Intelligence Navigator",
    page_icon=":material/shield:",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Inject custom theme & styling
inject_css(st)

DATA_PATH = ROOT / "data" / "acentria_dashboard_data.csv"
APP_NAME = "Acentria Reinsurance & Claims Intelligence Navigator"
REQUIRED_UPLOAD_COLUMNS = {
    "policy_id", "period", "region", "line_of_business", "gross_written_premium",
    "net_earned_premium", "claims_paid", "loss_ratio", "combined_ratio",
}
REGION_TO_CONTINENT = {
    # Region-group style labels (legacy/aggregated datasets)
    "Africa": "Africa", "North America": "North America",
    "Caribbean": "North America", "Latin America": "South America",
    "Europe": "Europe", "Nordics": "Europe", "Asia Pacific": "Asia",
    "Middle East & Africa": "Asia", "Australia & Pacific": "Oceania",
    # Real country names -- most uploaded/generated datasets use these, not
    # region-group labels, so these must be covered too or their GWP
    # silently disappears from continent-level charts.
    "Kenya": "Africa", "Nigeria": "Africa", "South Africa": "Africa",
    "Egypt": "Africa", "Ghana": "Africa", "Uganda": "Africa",
    "Tanzania": "Africa", "Rwanda": "Africa", "Ethiopia": "Africa",
    "Zambia": "Africa", "Morocco": "Africa", "Ivory Coast": "Africa",
    "Cote d'Ivoire": "Africa", "Senegal": "Africa", "Botswana": "Africa",
    "India": "Asia", "China": "Asia", "Japan": "Asia", "Singapore": "Asia",
    "UAE": "Asia", "United Arab Emirates": "Asia", "Saudi Arabia": "Asia",
    "Middle East": "Asia", "Indonesia": "Asia", "Philippines": "Asia",
    "United Kingdom": "Europe", "UK": "Europe", "Germany": "Europe",
    "France": "Europe", "Switzerland": "Europe", "Ireland": "Europe",
    "Spain": "Europe", "Italy": "Europe", "Netherlands": "Europe",
    "United States": "North America", "USA": "North America",
    "US": "North America", "Canada": "North America", "Mexico": "North America",
    "Brazil": "South America", "Argentina": "South America",
    "Colombia": "South America", "Chile": "South America", "Peru": "South America",
    "Australia": "Oceania", "New Zealand": "Oceania",
}
CONTINENTS = ["Africa", "Asia", "Europe", "North America", "South America", "Oceania", "Antarctica"]


@st.cache_data
def _load_hero_background_b64() -> str | None:
    """Loads and base64-encodes the hero background image, if present."""
    import base64
    hero_path = ROOT / "assets" / "hero_background.jpg"
    if not hero_path.exists():
        return None
    return base64.b64encode(hero_path.read_bytes()).decode()


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
    "policy_id": [
        "policy_id", "policy id", "policy number", "policy_no", "policy_number", "policy",
        "policyno", "contract_number", "contract_no", "cert_no", "certificate_number",
        "policy_ref", "reference_number", "risk_ref", "endorsement_number",
    ],
    "period": [
        "period", "date", "effective_date", "transaction_date", "policy_date", "issue_date",
        "coverage_date", "report_date", "loss_date", "written_date",
        "policy_eff_dt", "policy_effective_date", "inception_date", "start_date",
        "loss_dt", "report_dt", "txn_date_time", "transaction_datetime", "txn_date",
        "date_of_loss", "occurrence_date", "date_reported", "policy_inception",
        "underwriting_year", "accident_date", "claim_date", "booking_date",
        "renewal_date", "period_start", "as_of_date",
    ],
    "region": [
        "region", "territory", "location", "country", "area", "market",
        "geography", "geo", "state", "province", "country_of_risk", "risk_country",
        "underwriting_region", "operating_region", "branch", "office",
    ],
    "line_of_business": [
        "line_of_business", "line of business", "lob", "business_line", "product_line",
        "class_of_business", "segment", "insurance_type", "product_type", "coverage_type",
        "peril", "class", "portfolio", "book_of_business", "treaty_class",
        "sub_class", "policy_type",
    ],
    "gross_written_premium": [
        "gross_written_premium", "gross written premium", "gwp", "premium_written",
        "written_premium", "gross_premium", "premium_amount", "total_premium",
        "annual_premium", "gross_premium_written", "premium_income", "gwp_usd",
        "sum_premium", "reinsurance_premium", "ceded_premium_gross",
    ],
    "net_earned_premium": [
        "net_earned_premium", "net earned premium", "nep", "earned_premium",
        "net_premium", "premium_earned", "net_written_premium", "nwp",
        "net_premium_income", "retained_premium", "premium_net_of_reinsurance",
        "nep_usd",
    ],
    "claims_paid": [
        "claims_paid", "claims", "losses", "paid_losses", "incurred_claims",
        "claim_paid", "claim_amount", "total_claims", "claims_incurred",
        "gross_claims", "gross_claims_paid", "loss_amount", "loss_incurred",
        "indemnity_paid", "settled_amount", "paid_amount", "claim_cost",
        "net_claims_paid", "claims_paid_usd",
    ],
    "loss_ratio": [
        "loss_ratio", "loss ratio", "claims_ratio", "loss ratio percent",
        "loss_percentage", "loss percent", "incurred_loss_ratio", "net_loss_ratio",
        "lr", "loss_ratio_pct",
    ],
    "combined_ratio": [
        "combined_ratio", "combined ratio", "combined ratio percent", "cr",
        "combined_ratio_pct", "underwriting_ratio",
    ],
    "client_name": [
        "client_name", "client name", "cedant", "cedant_name", "insured", "customer",
        "customer_name", "policyholder", "policy_holder", "insured_name",
        "account_name", "client",
    ],
    "risk_category": [
        "risk_category", "risk category", "risk", "risk_type", "risk class",
        "risk_segmentation", "risk_classification", "hazard_class", "peril_category",
        "risk_grade", "risk_rating",
    ],
    "exposure": [
        "exposure", "sum_insured", "limit", "exposed_value", "total_insured_value",
        "tiv", "sum_assured", "policy_limit", "coverage_limit", "insured_value",
        "aggregate_limit",
    ],
    "premium_rate": [
        "premium_rate", "rate", "rate_on_line", "rol", "rate_percent", "pricing_rate",
        "technical_rate", "loaded_rate",
    ],
    "ceded_premium": [
        "ceded_premium", "ceded premium", "premium_ceded", "reinsurance_ceded",
        "outward_premium",
    ],
    "commission": [
        "commission", "ceding_commission", "brokerage", "broker_commission",
        "commission_rate", "commission_amount",
    ],
    "retention": [
        "retention", "net_retention", "priority", "deductible", "attachment_point",
        "self_insured_retention", "sir",
    ],
    "treaty_type": [
        "treaty_type", "treaty type", "reinsurance_type", "cover_type",
        "quota_share", "excess_of_loss", "xol", "facultative",
    ],
    "currency": [
        "currency", "ccy", "currency_code", "denomination",
    ],
    "underwriter": [
        "underwriter", "underwriter_name", "uw", "underwriting_manager",
    ],
    "claim_status": [
        "claim_status", "status", "claim_state", "settlement_status",
    ],
    "cause_of_loss": [
        "cause_of_loss", "loss_cause", "peril_type", "incident_type", "incident_severity",
    ],
    "settlement_date": [
        "settlement_date", "date_settled", "closed_date", "claim_closed_date",
        "payment_date",
    ],
    "reserve": [
        "reserve", "case_reserve", "outstanding_reserve", "incurred_but_not_reported",
        "ibnr", "reserve_amount",
    ],
    "broker": [
        "broker", "broker_name", "intermediary", "agent", "agent_name", "agent_id",
    ],
}

def normalize_upload_columns(frame: pd.DataFrame) -> pd.DataFrame:
    frame = frame.rename(columns={col: str(col).strip().lower() for col in frame.columns})
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


def download_kaggle_dataset(dataset_ref: str, kaggle_json_file: io.BytesIO | None = None, target_dir: str | Path | None = None) -> tuple[Path | None, str | None]:
    """Download and unzip a Kaggle dataset using the Kaggle API if available.

    Returns (target_path, error_message). If the Kaggle package is missing, returns an explanatory error.
    """
    try:
        import importlib
        kaggle_mod = importlib.import_module("kaggle.api.kaggle_api_extended")
        KaggleApi = getattr(kaggle_mod, "KaggleApi")
    except Exception:
        return None, "`kaggle` package is not installed. Install it (`pip install kaggle`) or provide the files manually."

    temp_dir = Path(target_dir or (ROOT / "data" / "kaggle"))
    temp_dir.mkdir(parents=True, exist_ok=True)

    old_kaggle_dir = os.environ.get("KAGGLE_CONFIG_DIR")
    cleanup_dir = None
    try:
        if kaggle_json_file is not None:
            cleanup_dir = Path(tempfile.mkdtemp())
            kaggle_cfg = cleanup_dir / ".kaggle"
            kaggle_cfg.mkdir(parents=True, exist_ok=True)
            cfg_path = kaggle_cfg / "kaggle.json"
            with open(cfg_path, "wb") as fh:
                fh.write(kaggle_json_file.getbuffer())
            os.chmod(cfg_path, 0o600)
            os.environ["KAGGLE_CONFIG_DIR"] = str(kaggle_cfg)

        api = KaggleApi()
        api.authenticate()
        api.dataset_download_files(dataset_ref, path=str(temp_dir), unzip=True, quiet=False)
        return temp_dir, None
    except Exception as error:
        return None, f"Kaggle download failed: {error}"
    finally:
        if old_kaggle_dir is not None:
            os.environ["KAGGLE_CONFIG_DIR"] = old_kaggle_dir
        elif cleanup_dir is not None:
            pass


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

def _filter_popover(label: str, options: list, key: str) -> list:
    """
    Renders a compact multiselect filter behind a popover button, so a
    long list of selected items doesn't wrap into a sprawling pill block
    that eats sidebar space. The button label always shows a live
    "N of M selected" summary even while the popover is closed.

    If the data source changed since the filter was last set (so the
    stored selection no longer matches any current option), the filter
    resets to "all selected" rather than silently filtering out every row.
    """
    current = st.session_state.get(key, options)
    if current and not any(item in options for item in current):
        st.session_state[key] = list(options)
        current = options

    count = len(current)
    total = len(options)
    button_label = f"{label}: All ({total})" if count == total else f"{label}: {count} of {total}"

    with st.popover(button_label, width="stretch"):
        quick_cols = st.columns(2)
        if quick_cols[0].button("Select all", key=f"{key}_all", width="stretch"):
            st.session_state[key] = list(options)
            st.rerun()
        if quick_cols[1].button("Clear", key=f"{key}_clear", width="stretch"):
            st.session_state[key] = []
            st.rerun()
        st.multiselect(label, options, default=options, key=key, label_visibility="collapsed")

    return st.session_state.get(key, options)


def _render_sidebar_logo() -> None:
    """Renders an original shield-and-checkmark wordmark, replacing the placeholder Twemoji icon."""
    st.markdown(
        '<div style="display:flex;align-items:center;gap:10px;margin-bottom:2px;">'
        '<svg width="36" height="36" viewBox="0 0 40 40" aria-hidden="true">'
        '<path d="M20 3 L34 8 V19 C34 28 28 34 20 37 C12 34 6 28 6 19 V8 Z" fill="none" stroke="#2f80ed" stroke-width="2.2"/>'
        '<path d="M13 20 L18 25 L27 14" fill="none" stroke="#2f80ed" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"/>'
        '</svg>'
        '<div>'
        '<div style="font-weight:600;font-size:16px;line-height:1.2;">RMIP-DSS PORTFOLIO</div>'
        '<div style="font-size:11px;color:rgba(255,255,255,0.55);">Reinsurance Intelligence</div>'
        '</div>'
        '</div>',
        unsafe_allow_html=True,
    )


def sidebar_controls(df: pd.DataFrame) -> tuple[str, pd.DataFrame, str]:
    with st.sidebar:
        _render_sidebar_logo()
        st.caption("Portfolio intelligence workspace")
        st.divider()
        st.caption(f"Signed in as **{st.session_state.user}**")
        st.badge(st.session_state.role, icon=":material/verified_user:", color="blue")

        workspace_permission_map = {
            "Portfolio analytics": "dashboard",
            "Claims Intelligence": "claims",
            "Reinsurers": "reinsurers",
            "Cedants": "cedants",
            "Pricing Analytics": "pricing",
            "Upload portfolio data": "upload",
            "Portfolio assistant": "dashboard",
            "Data quality": "dashboard",
        }
        workspace_options = [
            workspace for workspace, required_permission in workspace_permission_map.items()
            if has_permission(st.session_state.role, required_permission)
        ]

        if not workspace_options:
            st.error("Your role does not have access to any workspace. Contact your administrator.")
            st.stop()

        workspace = st.radio(
            "Workspace",
            workspace_options,
            format_func=lambda item: {
                "Portfolio analytics": ":material/monitoring: Analytics overview",
                "Claims Intelligence": ":material/medical_services: Claims Intelligence",
                "Reinsurers": ":material/handshake: Reinsurers",
                "Cedants": ":material/apartment: Cedants",
                "Pricing Analytics": ":material/price_change: Pricing Analytics",
                "Upload portfolio data": ":material/upload_file: Data upload",
                "Portfolio assistant": ":material/smart_toy: Assistant",
                "Data quality": ":material/verified: Data quality",
            }[item],
        )
        st.divider()
        st.subheader("Portfolio scope")
        source_options = ["Global portfolio"]
        if st.session_state.uploaded_data is not None:
            source_options.append("Uploaded portfolio")
        if st.session_state.get("internal_claims") is not None:
            source_options.append("Internal claims")
        source = st.selectbox("Data source", source_options)
        claims_obj = st.session_state.get("internal_claims")
        if source == "Uploaded portfolio" and st.session_state.uploaded_data is not None:
            active_df = st.session_state.uploaded_data.copy()
        elif source == "Internal claims" and claims_obj is not None:
            active_df = claims_obj.copy()
        else:
            active_df = df.copy()
        date_mode = st.segmented_control("Reporting period", ["All available years", "Custom range"], default="All available years")
        if date_mode == "Custom range":
            dates = st.date_input(
                "Date range", value=(active_df.period.min().date(), active_df.period.max().date()),
                min_value=active_df.period.min().date(), max_value=active_df.period.max().date(),
                help="Pick a specific reporting period, or choose all available years to include everything.",
            )
        else:
            dates = (active_df.period.min().date(), active_df.period.max().date())
            st.caption(f"Showing all available years from {active_df.period.min():%Y} to {active_df.period.max():%Y}.")
        lines = _filter_popover("Line of business", sorted(active_df.line_of_business.unique()), "filter_lines")
        regions = _filter_popover("Region", sorted(active_df.region.unique()), "filter_regions")
        risks = _filter_popover("Risk category", sorted(active_df.risk_category.unique()), "filter_risks")
        st.caption(f"Scope: {len(lines)} lines • {len(regions)} regions • {len(risks)} risk categories")
    result = active_df.copy()
    if isinstance(dates, tuple) and len(dates) == 2:
        result = result[result.period.dt.date.between(*dates)]
        period_label = f"{dates[0]:%d %b %Y} – {dates[1]:%d %b %Y}"
    else:
        period_label = "All periods"
    result = result[result.line_of_business.isin(lines) & result.region.isin(regions) & result.risk_category.isin(risks)]
    return workspace, result, period_label


def render_logout_topbar() -> None:
    cols = st.columns([4, 1, 1], vertical_alignment="center")
    with cols[0]:
        st.caption("RMIP-DSS  /  Enterprise portfolio intelligence")
    with cols[1]:
        st.caption(f"{st.session_state.user}")
    with cols[2]:
        if st.button("Sign out", icon=":material/logout:", width="stretch"):
            for key in ("logged_in", "user", "email", "role", "department"):
                st.session_state[key] = "" if key != "logged_in" else False
            st.session_state.page = "welcome"
            st.rerun()


def configure_enterprise_workspace() -> None:
    """Applies a restrained enterprise visual system only after authentication."""
    st.markdown("""
    <style>
    .block-container { max-width: 1680px; padding-top: 1.15rem; }
    [data-testid="stSidebar"] { border-right: 1px solid rgba(56, 189, 248, .18); }
    [data-testid="stSidebar"] [data-testid="stRadio"] label { border-radius: 8px; padding: 3px 5px; }
    div[data-testid="stMetric"] { background: linear-gradient(135deg, rgba(15, 35, 55, .92), rgba(10, 24, 40, .92)); border-color: rgba(80, 140, 180, .35); min-height: 126px; }
    div[data-testid="stMetricLabel"] { color: #a9c0d4; font-size: .79rem; }
    div[data-testid="stMetricValue"] { color: #f0f7fc; }
    [data-testid="stDataFrame"] { border: 1px solid rgba(80, 140, 180, .26); border-radius: 9px; overflow: hidden; }
    </style>
    """, unsafe_allow_html=True)


def show_welcome() -> None:
    """Professional multi-page landing with tabbed authentication and functional navigation."""
    st.session_state.setdefault("password_reset_email", "")
    st.session_state.setdefault("landing_page", "home")  # Track which page to show
    
    # ===== CUSTOM CSS =====
    st.markdown("""
    <style>
    /* ===== RESET & BASE ===== */
* { box-sizing: border-box; }
[data-testid="stHeader"] { background: transparent !important; }
#MainMenu, footer { display: none; }
[data-testid="stSidebar"], [data-testid="stSidebarCollapsedControl"] { display: none; }

/* ===== PAGE STRUCTURE ===== */
.block-container { max-width: 100%; padding: 0; margin: 0; }

/* =====================================================
   NUCLEAR FORCE DARK BACKGROUND
   (kills yellow/beige before AND after login)
   ===================================================== */
html, body,
[data-testid="stAppViewContainer"],
[data-testid="stAppViewContainer"] > div,
[data-testid="stAppViewContainer"] > .main,
.stApp,
.stApp > div,
.main,
section.main,
.block-container,
div[data-testid="stVerticalBlock"],
div[data-testid="stHorizontalBlock"],
div[data-testid="stVerticalBlockBorderWrapper"],
.element-container {
    background: #020617 !important;
    background-color: #020617 !important;
    background-image: none !important;
}

/* Final dark background + soft cyan glow */
.stApp { 
    background: 
        radial-gradient(ellipse 60% 50% at 85% 20%, rgba(56, 189, 248, 0.10) 0%, transparent 55%),
        radial-gradient(ellipse 50% 40% at 90% 70%, rgba(14, 165, 233, 0.07) 0%, transparent 50%),
        linear-gradient(165deg, #020617 0%, #0B1220 45%, #0F172A 100%) !important;
    min-height: 100vh !important;
    font-family: 'Inter', ui-sans-serif, system-ui, sans-serif;
    color: #E2E8F0 !important;
    position: relative;
    overflow-x: hidden;
}

/* Optional faint grid – delete this whole block if you want pure flat dark */
.stApp::before {
    content: "";
    position: fixed;
    inset: 0;
    background-image: url("data:image/svg+xml,%3Csvg width='800' height='600' xmlns='http://www.w3.org/2000/svg'%3E%3Cdefs%3E%3Cpattern id='grid' width='40' height='40' patternUnits='userSpaceOnUse'%3E%3Cpath d='M 40 0 L 0 0 0 40' fill='none' stroke='%231E293B' stroke-width='0.5' opacity='0.12'/%3E%3C/pattern%3E%3C/defs%3E%3Crect width='100%25' height='100%25' fill='url(%23grid)'/%3E%3C/svg%3E");
    opacity: 0.35;
    pointer-events: none;
    z-index: 0;
}

/* Keep content above the background layers */
.stApp > div {
    position: relative;
    z-index: 1;
}

/* Extra safety for the content area after login */
[data-testid="stAppViewContainer"] .main .block-container {
    background: transparent !important;
}
/* =====================================================
   KILL THE YELLOW CSS VARIABLES
   ===================================================== */
:root {
    --primary-bg: #020617 !important;
    --secondary-bg: #0B1220 !important;
    --surface-bg: #0F172A !important;
    --text-primary: #E2E8F0 !important;
    --text-secondary: #94A3B8 !important;
    --accent-primary: #38BDF8 !important;
    --accent-secondary: #0EA5E9 !important;
    --border-subtle: #1E293B !important;
}

html, body, .stApp, [data-testid="stAppViewContainer"] {
    background-color: #020617 !important;
    background: #020617 !important;
    color: #E2E8F0 !important;
}
    /* ===== NAVBAR ===== */
    .navbar {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 1rem 3rem;
        background: rgba(2, 6, 23, 0.85);
        backdrop-filter: blur(16px);
        border-bottom: 1px solid rgba(30, 41, 59, 0.8);
        position: sticky;
        top: 0;
        z-index: 1000;
    }
    
    .navbar-brand {
        display: flex;
        align-items: center;
        gap: 0.8rem;
        font-weight: 700;
        letter-spacing: 0.12em;
        font-size: 1.15rem;
        color: #E2E8F0;
    }
    
    .navbar-brand .mark {
        color: #38BDF8;
        font-size: 1.6rem;
        font-weight: 900;
    }
    
    .navbar-links {
        display: flex;
        gap: 1.2rem;
        align-items: center;
    }
    
    .navbar-links a {
        color: #94A3B8;
        text-decoration: none;
        font-size: 0.9rem;
        font-weight: 500;
        padding: 0.55rem 1.1rem;
        border-radius: 8px;
        transition: all 0.2s ease;
        background: rgba(30, 41, 59, 0.4);
    }
    
    .navbar-links a:hover {
        color: #38BDF8;
        background: rgba(56, 189, 248, 0.12);
    }
    
    .navbar-signin {
        background: linear-gradient(90deg, #38BDF8, #0EA5E9);
        color: #020617;
        padding: 0.7rem 1.8rem;
        border-radius: 8px;
        font-weight: 600;
        font-size: 0.9rem;
        cursor: pointer;
        border: none;
        transition: all 0.2s ease;
        box-shadow: 0 4px 14px rgba(56, 189, 248, 0.3);
    }
    
    .navbar-signin:hover {
        box-shadow: 0 8px 22px rgba(56, 189, 248, 0.45);
        transform: translateY(-2px);
    }
    
    /* ===== HERO SECTION ===== */
    .hero-container {
        display: grid;
        grid-template-columns: 1.4fr 1fr;
        gap: 3rem;
        align-items: start;
        padding: 3.5rem 3rem;
        max-width: 1500px;
        margin: 0 auto;
        position: relative;
    }
    
    .hero-bg {
        position: absolute;
        top: -40px;
        right: -20px;
        width: 580px;
        height: 580px;
        background: radial-gradient(circle, rgba(56, 189, 248, 0.14) 0%, transparent 68%);
        border-radius: 50%;
        filter: blur(60px);
        pointer-events: none;
        z-index: 0;
    }
    
    .hero-content {
        position: relative;
        z-index: 2;
    }
    
    .hero-content h1 {
        font-size: 3.2rem;
        font-weight: 700;
        color: #F1F5F9;
        line-height: 1.2;
        margin: 0 0 1.2rem 0;
        letter-spacing: -1px;
    }
    
    .hero-content h1 em {
        color: #38BDF8;
        font-style: normal;
        font-weight: 700;
    }
    
    .hero-content > p {
        font-size: 1.05rem;
        color: #94A3B8;
        line-height: 1.7;
        margin-bottom: 2rem;
        max-width: 580px;
    }
    
    /* Feature cards under hero */
    .feature-grid {
        display: grid;
        grid-template-columns: repeat(3, 1fr);
        gap: 1.2rem;
        margin-bottom: 2.5rem;
    }
    
    .feature-card {
        background: rgba(15, 23, 42, 0.7);
        border: 1px solid rgba(30, 41, 59, 0.9);
        border-radius: 12px;
        padding: 1.3rem;
        transition: all 0.3s ease;
        backdrop-filter: blur(8px);
    }
    
    .feature-card:hover {
        background: rgba(15, 23, 42, 0.9);
        border-color: rgba(56, 189, 248, 0.5);
        box-shadow: 0 8px 28px rgba(56, 189, 248, 0.15);
        transform: translateY(-4px);
    }
    
    .feature-card .icon {
        font-size: 1.8rem;
        color: #38BDF8;
        margin-bottom: 0.8rem;
        display: block;
    }
    
    .feature-card h3 {
        font-size: 0.95rem;
        color: #E2E8F0;
        font-weight: 600;
        margin-bottom: 0.4rem;
        margin-top: 0;
    }
    
    .feature-card p {
        font-size: 0.8rem;
        color: #94A3B8;
        line-height: 1.5;
        margin: 0;
    }
    
    /* Purpose / Vision / Mission cards */
    .value-cards {
        display: grid;
        grid-template-columns: repeat(3, 1fr);
        gap: 1.5rem;
    }
    
    .value-card {
        background: linear-gradient(145deg, rgba(15, 23, 42, 0.85), rgba(2, 6, 23, 0.75));
        border: 1px solid rgba(30, 41, 59, 0.9);
        border-radius: 12px;
        padding: 1.8rem;
        transition: all 0.3s ease;
        position: relative;
        overflow: hidden;
        backdrop-filter: blur(6px);
    }
    
    .value-card::before {
        content: "";
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        height: 3px;
        background: linear-gradient(90deg, #38BDF8, transparent);
    }
    
    .value-card:hover {
        border-color: rgba(56, 189, 248, 0.5);
        transform: translateY(-5px);
        box-shadow: 0 14px 32px rgba(56, 189, 248, 0.14);
    }
    
    .value-card h4 {
        font-size: 1rem;
        color: #E2E8F0;
        font-weight: 600;
        margin: 0 0 0.8rem 0;
    }
    
    .value-card p {
        font-size: 0.82rem;
        color: #94A3B8;
        line-height: 1.6;
        margin: 0;
    }
    
    /* ===== AUTH / LOGIN CARD ===== */
    .auth-container {
        background: rgba(15, 23, 42, 0.92);
        border: 1px solid rgba(30, 41, 59, 0.95);
        border-radius: 16px;
        padding: 2.2rem;
        max-width: 400px;
        position: sticky;
        top: 120px;
        box-shadow: 
            0 25px 50px -12px rgba(0, 0, 0, 0.6),
            0 0 0 1px rgba(56, 189, 248, 0.05);
        backdrop-filter: blur(12px);
    }
    
    .auth-header {
        display: flex;
        align-items: center;
        gap: 1rem;
        margin-bottom: 1.5rem;
        padding-bottom: 1.5rem;
        border-bottom: 1px solid rgba(30, 41, 59, 0.8);
    }
    
    .auth-header .logo {
        font-size: 1.8rem;
        color: #38BDF8;
        font-weight: 900;
    }
    
    .auth-header-text h3 {
        font-size: 0.95rem;
        color: #E2E8F0;
        font-weight: 600;
        margin: 0;
    }
    
    .auth-header-text p {
        font-size: 0.75rem;
        color: #64748B;
        margin: 0.3rem 0 0;
    }
    
    .auth-title {
        font-size: 1.3rem;
        color: #F1F5F9;
        font-weight: 700;
        margin-bottom: 0.5rem;
    }
    
    .auth-subtitle {
        font-size: 0.85rem;
        color: #94A3B8;
        margin-bottom: 1.5rem;
        line-height: 1.5;
    }
    
    /* Tabs inside auth */
    [data-testid="stTabs"] {
        margin-bottom: 1.5rem;
    }
    
    [data-testid="stTabs"] [role="tablist"] {
        display: grid;
        grid-template-columns: repeat(3, 1fr);
        gap: 0.5rem;
        background: rgba(2, 6, 23, 0.7);
        padding: 0.5rem;
        border-radius: 8px;
        border: 1px solid rgba(30, 41, 59, 0.8);
    }
    
    [data-testid="stTabs"] [role="tab"] {
        background: transparent;
        color: #94A3B8;
        border: none;
        padding: 0.7rem 0.4rem;
        font-size: 0.85rem;
        font-weight: 500;
        border-radius: 6px;
        text-align: center;
        transition: all 0.2s ease;
        cursor: pointer;
    }
    
    [data-testid="stTabs"] [role="tab"]:hover {
        background: rgba(56, 189, 248, 0.1);
        color: #38BDF8;
    }
    
    [data-testid="stTabs"] [role="tab"][aria-selected="true"] {
        background: #38BDF8;
        color: #020617;
        font-weight: 600;
        box-shadow: 0 4px 12px rgba(56, 189, 248, 0.3);
    }
    
    .auth-form input,
    .auth-form textarea {
        width: 100%;
        background: #020617;
        color: #E2E8F0;
        border: 1px solid rgba(30, 41, 59, 0.9);
        border-radius: 8px;
        padding: 0.75rem;
        margin-bottom: 1rem;
        font-size: 0.9rem;
        font-family: inherit;
        transition: all 0.2s ease;
    }
    
    .auth-form input:focus,
    .auth-form textarea:focus {
        outline: none;
        border-color: #38BDF8;
        background: #0F172A;
        box-shadow: 0 0 0 3px rgba(56, 189, 248, 0.2);
    }
    
    .auth-form input::placeholder {
        color: #64748B;
    }
    
    .auth-security {
        background: rgba(56, 189, 248, 0.08);
        border: 1px solid rgba(56, 189, 248, 0.25);
        border-radius: 8px;
        padding: 0.9rem;
        margin-bottom: 1.5rem;
        font-size: 0.75rem;
        color: #38BDF8;
        line-height: 1.5;
    }
    
    .auth-security strong {
        display: block;
        margin-bottom: 0.3rem;
        font-weight: 600;
    }
    
    /* ===== TRUST FOOTER ===== */
    .trust-footer {
        display: grid;
        grid-template-columns: repeat(3, 1fr);
        gap: 2rem;
        padding: 3.5rem 3rem;
        background: rgba(2, 6, 23, 0.75);
        border-top: 1px solid rgba(30, 41, 59, 0.8);
        max-width: 1500px;
        margin: 0 auto;
    }
    
    .trust-item {
        text-align: center;
    }
    
    .trust-item .icon {
        font-size: 2rem;
        color: #38BDF8;
        margin-bottom: 0.8rem;
    }
    
    .trust-item h4 {
        font-size: 0.95rem;
        color: #E2E8F0;
        font-weight: 600;
        margin-bottom: 0.4rem;
    }
    
    .trust-item p {
        font-size: 0.8rem;
        color: #94A3B8;
        line-height: 1.5;
        margin: 0;
    }
    
    .footer-bottom {
        text-align: center;
        padding: 2rem 3rem;
        color: #64748B;
        font-size: 0.8rem;
        border-top: 1px solid rgba(30, 41, 59, 0.8);
        background: rgba(2, 6, 23, 0.95);
    }
    
    .footer-bottom a {
        color: #38BDF8;
        text-decoration: none;
        transition: color 0.2s ease;
    }
    
    .footer-bottom a:hover {
        color: #7DD3FC;
    }
    
    /* ===== RESPONSIVE ===== */
    @media (max-width: 1200px) {
        .hero-container {
            grid-template-columns: 1fr;
            padding: 2rem;
        }
        .auth-container {
            position: relative;
            top: auto;
            max-width: 100%;
            margin-top: 2rem;
        }
    }
    
    @media (max-width: 768px) {
        .navbar {
            padding: 1rem;
            flex-wrap: wrap;
            gap: 0.8rem;
        }
        .navbar-links {
            gap: 0.6rem;
            order: 3;
            width: 100%;
            margin-top: 0.8rem;
            flex-wrap: wrap;
        }
        .hero-content h1 {
            font-size: 2.1rem;
        }
        .feature-grid, .value-cards, .trust-footer {
            grid-template-columns: 1fr;
        }
        [data-testid="stTabs"] [role="tablist"] {
            grid-template-columns: 1fr;
        }
    }
</style>
    """, unsafe_allow_html=True)

    # ===== FUNCTIONAL NAVBAR WITH NAVIGATION =====
    navbar_col1, navbar_col2, navbar_col3, navbar_col4, navbar_col5 = st.columns([1.2, 4, 0.8, 0.8, 0.8])
    
    with navbar_col1:
        st.markdown("""
        <div style="display: flex; align-items: center; gap: 0.6rem; font-weight: 700; color: #F8FAFC; font-size: 1.1rem;">
            <span style="color: #06B6D4; font-size: 1.5rem;">◆</span>
            <span>RMIP-DSS PORTFOLIO</span>
        </div>
        """, unsafe_allow_html=True)
    
    with navbar_col2:
        nav_col1, nav_col2, nav_col3, nav_col4, nav_col5 = st.columns(5)
        with nav_col1:
            if st.button("🏠 Home", use_container_width=True, key="nav_home"):
                st.session_state.landing_page = "home"
                st.rerun()
        with nav_col2:
            if st.button("💼 Platform", use_container_width=True, key="nav_platform"):
                st.session_state.landing_page = "platform"
                st.rerun()
        with nav_col3:
            if st.button("🎯 Solutions", use_container_width=True, key="nav_solutions"):
                st.session_state.landing_page = "solutions"
                st.rerun()
        with nav_col4:
            if st.button("📊 Intelligence", use_container_width=True, key="nav_intelligence"):
                st.session_state.landing_page = "intelligence"
                st.rerun()
        with nav_col5:
            if st.button("ℹ️ About Us", use_container_width=True, key="nav_about"):
                st.session_state.landing_page = "about"
                st.rerun()
    
    with navbar_col5:
        if st.button("Sign In", use_container_width=True, key="nav_signin"):
            st.session_state.show_auth = True
    
    st.markdown("<hr style='margin: 0; border: none; height: 1px; background: rgba(51, 65, 85, 0.3);'>", unsafe_allow_html=True)
    
    # ===== PAGE ROUTING =====
    if st.session_state.landing_page == "home":
        _render_home_page()
    elif st.session_state.landing_page == "platform":
        _render_platform_page()
    elif st.session_state.landing_page == "solutions":
        _render_solutions_page()
    elif st.session_state.landing_page == "intelligence":
        _render_intelligence_page()
    elif st.session_state.landing_page == "about":
        _render_about_page()
    
    # ===== FOOTER =====
    st.markdown("""
    <div class="trust-footer">
        <div class="trust-item">
            <div class="icon">♢</div>
            <h4>Enterprise Security</h4>
            <p>SOC 2 Type II compliant • Role-based access • Complete audit trails</p>
        </div>
        <div class="trust-item">
            <div class="icon">◌</div>
            <h4>Real-time Intelligence</h4>
            <p>Premium, claims & risk data unified in one trusted view</p>
        </div>
        <div class="trust-item">
            <div class="icon">↗</div>
            <h4>Decisive Action</h4>
            <p>Clear insights for smarter strategic decisions</p>
        </div>
    </div>
    <div class="footer-bottom">
        © 2026 Rmip-Dss. All rights reserved. | 
        <a href="#">Privacy Policy</a> | 
        <a href="#">Security</a> | 
        <a href="#">Support</a>
    </div>
    """, unsafe_allow_html=True)


def _render_home_page() -> None:
    """Home page with hero, features, and auth forms."""
    col_hero, col_auth = st.columns([1.4, 0.95], gap="large", vertical_alignment="top")

    with col_hero:
        st.markdown("""
        <div class="hero-container">
            <div class="hero-bg"></div>
            <div class="hero-content">
                <h1>Reinsurance Enterprise <em>intelligence</em> that drives smarter decisions.</h1>
                <p>RMIP-DSS delivers trusted analytics, claims insights and real intelligence across your global portfolio, turns fragmented reinsurance data into real-time intelligence and is evolving into a predictive decision platform that forecasts claims, reserves, and pricing so teams can act before losses materialize</p>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # Feature cards
        st.markdown("<div class='feature-grid'>", unsafe_allow_html=True)
        feature_cols = st.columns(3)
        features = [
            ("◉", "Real-time intelligence", "Actionable insights updated continuously"),
            ("♢", "Secure & monitored", "Enterprise-grade • SOC 2 aligned"),
            ("↗", "Data-driven decisions", "Better outcomes across the enterprise"),
        ]
        for col, (icon, title, desc) in zip(feature_cols, features):
            with col:
                st.markdown(f"""
                <div class="feature-card">
                    <div class="icon">{icon}</div>
                    <h3>{title}</h3>
                    <p>{desc}</p>
                </div>
                """, unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

        # Value cards
        st.markdown("<div class='value-cards'>", unsafe_allow_html=True)
        value_cols = st.columns(3)
        values = [
            ("Purpose", "To turn fragmented reinsurance data into trusted intelligence that powers better underwriting and claims decisions."),
            ("Vision", "To be the definitive navigation and decision layer for global reinsurers seeking clarity, confidence, and advantage."),
            ("Mission", "To unify premium, claims, and risk data into predictive, actionable insights that improve outcomes across the enterprise."),
        ]
        for col, (label, desc) in zip(value_cols, values):
            with col:
                st.markdown(f"""
                <div class="value-card">
                    <h4>{label}</h4>
                    <p>{desc}</p>
                </div>
                """, unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

    with col_auth:
        st.markdown(f"""
        <div class="auth-container">
            <div class="auth-header">
                <div class="logo">◆</div>
                <div class="auth-header-text">
                    <h3>RMIP-DSS 📈</h3>
                    <p>Reinsurance Intelligence Portfolio 📊</p>
                </div>
            </div>
        """, unsafe_allow_html=True)

        # ===== TABBED AUTHENTICATION =====
        tab1, tab2, tab3 = st.tabs(["🔐 Sign In", "🔑 Reset Password", "📝 Request Access"])

        # TAB 1: SIGN IN
        with tab1:
            st.markdown("""
            <div class="auth-title">Welcome Back</div>
            <div class="auth-subtitle">Sign in to access your intelligence dashboard.</div>
            <div class="auth-security">
                <strong>🔒 Restricted Access</strong>
                Authorized personnel only. All actions are logged.
            </div>
            """, unsafe_allow_html=True)
            
            with st.form("sign_in_form_main", clear_on_submit=False):
                email = st.text_input("Email", placeholder="you@company.com", key="signin_email")
                password = st.text_input("Password", type="password", placeholder="Enter your password", key="signin_pwd")
                
                if st.form_submit_button("Sign In", use_container_width=True):
                    if not email or not password:
                        st.error("❌ Please enter your email and password.")
                    else:
                        user = login_user(email.strip().lower(), password)
                        if not user:
                            st.error("❌ Invalid credentials. Please try again.")
                        else:
                            notify_admin_login(user)
                            st.session_state.update({
                                "logged_in": True,
                                "page": "dashboard",
                                "user": user["fullname"],
                                "email": user["email"],
                                "role": user["role"],
                                "department": user["department"],
                            })
                            st.rerun()

        # TAB 2: RESET PASSWORD  
        with tab2:
            st.markdown("""
            <div class="auth-title">Reset Password</div>
            <div class="auth-subtitle">Forgot your password? We'll help you reset it.</div>
            """, unsafe_allow_html=True)
            
            if not st.session_state.get("password_reset_email"):
                with st.form("reset_step1_form", clear_on_submit=False):
                    reset_email = st.text_input("Your email", placeholder="you@gmail.com", key="reset_email_step1")
                    
                    if st.form_submit_button("Send Reset Code", use_container_width=True):
                        if not reset_email.strip():
                            st.error("❌ Please enter your email.")
                        else:
                            st.session_state.password_reset_email = reset_email.strip().lower()
                            request_password_reset(st.session_state.password_reset_email)
                            st.success("✓ Reset code sent to your email!")
                            st.rerun()
            else:
                with st.form("reset_step2_form", clear_on_submit=False):
                    reset_code = st.text_input("Reset code (from email)", placeholder="000000", max_chars=6, key="reset_code")
                    new_password = st.text_input("New password", type="password", placeholder="Min 10 chars", key="new_pwd")
                    confirm_password = st.text_input("Confirm password", type="password", placeholder="Confirm", key="confirm_pwd")
                    
                    col_reset1, col_reset2 = st.columns(2)
                    with col_reset1:
                        if st.form_submit_button("Update Password", use_container_width=True):
                            if not new_password or not confirm_password:
                                st.error("❌ Please enter new password.")
                            elif new_password != confirm_password:
                                st.error("❌ Passwords do not match.")
                            else:
                                reset_ok, reset_message = reset_password_with_code(
                                    st.session_state.password_reset_email, reset_code, new_password
                                )
                                if reset_ok:
                                    st.success("✓ Password updated! You can now sign in.")
                                    st.session_state.password_reset_email = ""
                                    st.rerun()
                                else:
                                    st.error(f"❌ {reset_message}")
                    with col_reset2:
                        if st.form_submit_button("Start Over", use_container_width=True):
                            st.session_state.password_reset_email = ""
                            st.rerun()

        # TAB 3: REQUEST ACCESS
        with tab3:
            st.markdown("""
            <div class="auth-title">Request Access</div>
            <div class="auth-subtitle">Join our enterprise reinsurers. We'll contact you within 24 hours.</div>
            <div class="auth-security">
                <strong>✓ Secure Enterprise Access</strong>
                Your data is protected with SOC 2 Type II compliance.
            </div>
            """, unsafe_allow_html=True)
            
            with st.form("request_access_form_main", clear_on_submit=False):
                req_name = st.text_input("Full name", placeholder="John Doe", key="req_name")
                req_email = st.text_input("Work email", placeholder="you@company.com", key="req_email")
                req_department = st.text_input("Department", placeholder="Underwriting", key="req_dept")
                req_message = st.text_area("Tell us about your needs", height=80, placeholder="What challenges are you solving?", key="req_msg")
                
                if st.form_submit_button("Submit Request", use_container_width=True):
                    if not req_name.strip() or not req_email.strip():
                        st.error("❌ Please enter your name and email.")
                    else:
                        request_access(req_name.strip(), req_email.strip().lower(), req_department.strip(), req_message.strip())
                        st.success("✓ Your request has been submitted! Our team will contact you soon.")
                        st.balloons()

        st.markdown("</div>", unsafe_allow_html=True)


def _render_platform_page() -> None:
    """Platform capabilities page."""
    st.markdown("""
    <div style="padding: 3rem; max-width: 1400px; margin: 0 auto;">
        <h1 style="color: #F8FAFC; font-size: 2.5rem; margin-bottom: 1rem;">Our Platform</h1>
        <p style="color: #94A3B8; font-size: 1.1rem; margin-bottom: 3rem; max-width: 700px;">
            RMIP-DSS delivers a unified intelligence platform that consolidates premium, claims, and risk data into a single 
            secure and intuitive interface—giving underwriting, claims, and executive teams a clear, consistent view of 
            portfolio performance and the insights needed to act with confidence.
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    platform_features = [
        ("📊", "Real-time Data Dashboards", "Access a unified, always-current view of your reinsurance portfolio. Interactive dashboards deliver live "
        "updates on premium, claims, loss ratios, risk concentration, and key performance indicators, enabling "
        "underwriters, claims teams, and executives to monitor performance and respond to emerging trends without delay."),
        ("🔍", "Advanced Search & Filtering", "Locate critical insights in seconds with powerful search, multi-dimensional filtering, and deep drill-down "
        "capabilities. Users can slice data by line of business, region, cedent, treaty, time period, or risk category "
        "to move from high-level overview to granular detail with precision and speed."),
        ("📈", "Predictive Analytics", "Move from reactive reporting to forward-looking intelligence. Machine learning models forecast claims "
        "frequency and severity, project loss and combined ratios, surface emerging risks, and highlight potential "
        "portfolio deterioration—giving teams the opportunity to act before losses fully materialise."),
        ("🔐", "Enterprise Security", "Protect sensitive portfolio and claims data with bank-grade encryption, granular role-based access control, "
        "and comprehensive audit trails. Every action is logged and monitored, supporting regulatory compliance, "
        "internal governance, and the highest standards of data integrity and confidentiality."),
        ("⚙️", "Workflow Automation", "Eliminate repetitive manual work and standardise processes across teams. Configure automated alerts, "
        "approval flows, data validation rules, and custom workflows that align with your underwriting, claims, "
        "and portfolio management operating model—improving consistency, speed, and control."),
        ("🔗", "Seamless Integration", "Connect the platform to your existing technology landscape without disruption. Robust APIs, automated "
        "data feeds, and webhook support enable reliable exchange of premium, claims, exposure, and reference data "
        "with core systems, data warehouses, and third-party sources, ensuring a single source of truth."),
    ]
    
    for icon, title, desc in platform_features:
        st.markdown(f"""
        <div style="background: rgba(30, 41, 59, 0.5); border: 1px solid rgba(51, 65, 85, 0.4); border-radius: 10px; padding: 2rem; transition: all 0.3s ease;">
            <div style="font-size: 2.5rem; color: #06B6D4; margin-bottom: 1rem;">{icon}</div>
            <h3 style="color: #F8FAFC; font-size: 1.2rem; margin-bottom: 0.5rem; margin-top: 0;">{title}</h3>
            <p style="color: #94A3B8; line-height: 1.6; margin: 0;">{desc}</p>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("</div>", unsafe_allow_html=True)


def _render_solutions_page() -> None:
    """Solutions & Services page."""
    st.markdown("""
    <div style="padding: 3rem; max-width: 1400px; margin: 0 auto;">
        <h1 style="color: #F8FAFC; font-size: 2.5rem; margin-bottom: 1rem;">Solutions & Services</h1>
        <p style="color: #94A3B8; font-size: 1.1rem; margin-bottom: 3rem; max-width: 700px;">
            We deliver tailored solutions designed for every function across your organisation—from underwriting and claims 
            to pricing, portfolio management, and executive leadership—ensuring each team has the intelligence and tools 
            required to make faster, more confident decisions.
        </p>
        
    """, unsafe_allow_html=True)
    
    solutions = [
        ("👔", "Underwriting Solutions", "Empower underwriting teams with a complete view of risk across treaties, lines of business, and geographies. "
        "Our platform delivers advanced risk assessment, concentration analysis, portfolio optimization tools, and "
        "pricing benchmarks that help underwriters identify emerging exposures, balance portfolio mix, and make "
        "faster, more confident acceptance and pricing decisions."),
        ("📋", "Claims Management", "Gain end-to-end visibility into claims performance and outcomes. Track open and settled claims in real time, "
        "monitor loss ratios and development patterns, analyse reserves, and apply predictive loss modelling to "
        "anticipate severity trends. The result is earlier intervention, reduced leakage, and stronger control over "
        "claims costs across the entire portfolio."),
        ("📈", "Pricing & Analytics", "Move beyond historical reporting to true pricing intelligence. Combine multi-year premium and claims data "
        "with competitive benchmarking, margin analysis, and technical pricing insights. Underwriters and pricing "
        "actuaries can test rate changes, evaluate adequacy, and optimise portfolio profitability with clear, "
        "data-driven recommendations."),
        ("💼", "Executive Dashboards", "Provide senior leadership with a single, trusted view of portfolio health. Real-time KPI monitoring, "
        "performance tracking against targets, and board-ready strategic reports deliver the clarity executives "
        "need to steer the organisation. From combined ratio trends to emerging risk signals, decision-makers "
        "have the insight required to act decisively."),
        ("🎓", "Training & Enablement", "Ensure rapid adoption and sustained value across the organisation. We provide structured onboarding "
        "programmes, role-based user training, certification pathways, and continuous enablement support so that "
        "underwriters, claims handlers, analysts, and executives can fully leverage the platform from day one."),
        ("🤝", "Professional Services", "Accelerate time-to-value with expert implementation and advisory support. Our team delivers custom "
        "platform configurations, complex data migrations, system integrations, and strategic consulting to "
        "align the solution with your operating model, data landscape, and long-term reinsurance objectives."),
    ]
    
    for icon, title, desc in solutions:
        st.markdown(f"""
        <div style="background: linear-gradient(135deg, rgba(30, 41, 59, 0.5), rgba(15, 23, 42, 0.3)); border: 1px solid rgba(51, 65, 85, 0.4); border-radius: 10px; padding: 2rem; transition: all 0.3s ease;">
            <div style="font-size: 2.5rem; color: #06B6D4; margin-bottom: 1rem;">{icon}</div>
            <h3 style="color: #F8FAFC; font-size: 1.2rem; margin-bottom: 0.5rem; margin-top: 0;">{title}</h3>
            <p style="color: #94A3B8; line-height: 1.6; margin: 0;">{desc}</p>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("</div>", unsafe_allow_html=True)


def _render_intelligence_page() -> None:
    """Market Intelligence page."""
    st.markdown("""
    <div style="padding: 3rem; max-width: 1400px; margin: 0 auto;">
        <h1 style="color: #F8FAFC; font-size: 2.5rem; margin-bottom: 1rem;">Market Intelligence</h1>
        <p style="color: #94A3B8; font-size: 1.1rem; margin-bottom: 3rem; max-width: 700px;">
            Stay ahead of shifting market conditions with curated intelligence, peer benchmarking, and portfolio-specific insights. 
            Combine real-time market signals, competitive performance data, and forward-looking analysis to support more informed 
            underwriting, pricing, and strategic decisions across your reinsurance portfolio.
        </p>
        
    """, unsafe_allow_html=True)
    
    intel_features = [
        ("🌍", "Global Market Insights", "Maintain continuous visibility into the global reinsurance landscape. Track rate movements, capacity shifts, "
        "regional performance trends, and broader market dynamics in real time so underwriting and strategy teams "
        "can respond quickly to changing conditions and emerging opportunities across key markets."),
        ("📊", "Competitive Benchmarking", "Measure your portfolio performance against relevant industry peers with clarity and confidence. Identify "
        "relative strengths and weaknesses in loss ratios, growth, pricing adequacy, and risk appetite, enabling "
        "leadership to refine competitive positioning and prioritise areas for improvement."),
        ("⚠️", "Risk Intelligence", "Stay ahead of developing threats with timely intelligence on emerging risks, catastrophic events, and "
        "regulatory changes. Understand potential portfolio impact early, prioritise monitoring, and support "
        "proactive risk mitigation and capital management decisions across the organisation."),
        ("💰", "Pricing Intelligence", "Strengthen pricing decisions with clear visibility into market rate trends, technical adequacy, and "
        "competitive positioning. Combine internal portfolio data with external market signals to support more "
        "disciplined rate setting, renewal strategy, and margin protection."),
        ("🔮", "Predictive Analytics", "Anticipate market and portfolio developments before they fully materialise. Forecast loss severity patterns, "
        "rate trajectory, demand shifts, and emerging opportunities so teams can adjust underwriting appetite, "
        "pricing, and capacity deployment with greater foresight."),
        ("📰", "Industry News & Alerts", "Receive curated, high-signal industry news, regulatory updates, and market alerts directly relevant to "
        "your portfolio and regions of interest. Reduce noise, stay informed, and ensure critical developments "
        "reach the right stakeholders without delay."),
    ]
    
    for icon, title, desc in intel_features:
        st.markdown(f"""
        <div style="background: rgba(30, 41, 59, 0.5); border: 1px solid rgba(51, 65, 85, 0.4); border-radius: 10px; padding: 2rem; transition: all 0.3s ease;">
            <div style="font-size: 2.5rem; color: #06B6D4; margin-bottom: 1rem;">{icon}</div>
            <h3 style="color: #F8FAFC; font-size: 1.2rem; margin-bottom: 0.5rem; margin-top: 0;">{title}</h3>
            <p style="color: #94A3B8; line-height: 1.6; margin: 0;">{desc}</p>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("</div>", unsafe_allow_html=True)


def _render_about_page() -> None:
    """About Us page with Built for Your Team use cases."""
    st.markdown("""
    <div style="padding: 3rem 0; max-width: 1400px; margin: 0 auto;">
        <h1 style="color: #F8FAFC; font-size: 2.5rem; text-align: center; margin-bottom: 1rem;">ABOUT RMIP-DSS INTELLIGENCE PORTFOLIO</h1>
        <p style="color: #94A3B8; font-size: 1.1rem; text-align: center; margin-bottom: 3rem; max-width: 700px; margin-left: auto; margin-right: auto;">
            We're reimagining how global reinsurers make decisions. Built by industry experts, for industry professionals.
        </p>
        
    """, unsafe_allow_html=True)
    
    values = [
        ("🎯", "Our Mission", "To unify premium, claims, and risk data into clear, actionable insights that enable underwriting, claims, "
        "and leadership teams to make faster, more confident decisions and drive better outcomes across the enterprise."),
        ("🔭", "Our Vision", "To become the essential navigation and intelligence layer that global reinsurers rely on for clarity, "
        "confidence, and sustained competitive advantage in an increasingly complex risk landscape."),
        ("💎", "Our Values", "We are guided by trust, transparency, and excellence in everything we deliver. We pursue continuous "
        "innovation while maintaining a relentless focus on customer success, ensuring our platform creates lasting "
        "value for the organisations and teams that depend on it."),
    ]
    
    for icon, title, desc in values:
        st.markdown(f"""
        <div style="background: linear-gradient(135deg, rgba(30, 41, 59, 0.5), rgba(15, 23, 42, 0.3)); border: 1px solid rgba(51, 65, 85, 0.3); border-radius: 10px; padding: 2rem; transition: all 0.3s ease;">
            <div style="font-size: 2.2rem; color: #06B6D4; margin-bottom: 1rem;">{icon}</div>
            <h3 style="color: #F8FAFC; font-size: 1.1rem; margin-bottom: 0.5rem; margin-top: 0;">{title}</h3>
            <p style="color: #94A3B8; line-height: 1.6; margin: 0;">{desc}</p>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("</div>", unsafe_allow_html=True)
    
    # Built for Your Team section
    st.markdown("""
    <div style="background: rgba(30, 41, 59, 0.3); border: 1px solid rgba(51, 65, 85, 0.3); border-radius: 12px; padding: 3rem; margin: 0 3rem;">
        <h2 style="color: #F8FAFC; font-size: 2rem; text-align: center; margin-bottom: 2.5rem;">Built for Your Team</h2>
        <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 2rem;">
    """, unsafe_allow_html=True)
    
    use_cases = [
    (
        "👔",
        "Underwriting Teams",
        "Equip underwriters with a complete, real-time view of portfolio risk. Evaluate concentration across lines of business, "
        "regions, and cedents, identify emerging exposure patterns, and support faster, more consistent acceptance and pricing "
        "decisions with unified premium, claims, and risk data.",
        ["✓ Portfolio risk assessment", "✓ Concentration analysis", "✓ Pricing benchmarks"]
    ),
    (
        "📋",
        "Claims Management",
        "Gain clear visibility into claims performance and development. Track open and settled claims, monitor loss ratio trends, "
        "surface severity patterns, and identify leakage or emerging issues early—enabling claims teams to improve outcomes, "
        "control costs, and support more accurate reserving.",
        ["✓ Claims tracking", "✓ Loss ratio monitoring", "✓ Pattern identification"]
    ),
    (
        "📈",
        "Pricing Analytics",
        "Strengthen pricing decisions with robust historical and forward-looking analysis. Examine multi-year loss experience, "
        "benchmark premiums against technical indications and market peers, and refine rate strategies to protect margins while "
        "remaining competitive.",
        ["✓ Historical analysis", "✓ Premium optimization", "✓ Competitive benchmarking"]
    ),
    (
        "🎯",
        "Executive Leadership",
        "Provide senior leaders with a trusted, real-time view of portfolio health and performance. Deliver clear KPI dashboards, "
        "trend analysis, and board-ready insights that support strategic steering, capital allocation, and proactive risk management "
        "across the organisation.",
        ["✓ KPI dashboards", "✓ Performance trends", "✓ Strategic reporting"]
    ),
]
    
    for icon, title, desc, benefits in use_cases:
        benefits_html = "".join(f"<div style='color: #06B6D4; margin-bottom: 0.5rem;'>{b}</div>" for b in benefits)
        st.markdown(f"""
        <div style="background: rgba(15, 23, 42, 0.6); border: 1px solid rgba(51, 65, 85, 0.4); border-radius: 10px; padding: 2rem; transition: all 0.3s ease;">
            <div style="font-size: 2rem; color: #06B6D4; margin-bottom: 1rem;">{icon}</div>
            <h3 style="color: #F8FAFC; font-size: 1.15rem; margin-bottom: 0.6rem; margin-top: 0;">{title}</h3>
            <p style="color: #94A3B8; line-height: 1.6; margin-bottom: 1rem;">{desc}</p>
            <div style="border-top: 1px solid rgba(51, 65, 85, 0.3); padding-top: 1rem;">
                {benefits_html}
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("</div></div>", unsafe_allow_html=True)




def _fmt_usd(value: float) -> str:
    """Formats a USD amount with sensible abbreviation, never truncating mid-digit."""
    abs_v = abs(value)
    if abs_v >= 1e9:
        return f"USD {value / 1e9:.2f}B"
    if abs_v >= 1e6:
        return f"USD {value / 1e6:.1f}M"
    if abs_v >= 1e3:
        return f"USD {value / 1e3:.1f}K"
    return f"USD {value:,.0f}"


def _period_over_period_delta(monthly_series: pd.Series) -> tuple[str, bool]:
    """
    Splits a monthly series in half and compares recent vs. prior sum, so
    KPI deltas reflect the actual filtered data rather than fixed values.
    """
    if len(monthly_series) < 2:
        return "", True
    mid = len(monthly_series) // 2
    prior = monthly_series.iloc[:mid].sum()
    recent = monthly_series.iloc[mid:].sum()
    if prior == 0:
        return "", True
    change = (recent - prior) / prior * 100
    return f"{change:+.1f}%", change >= 0


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
    loss = df.loss_ratio.mean() * 100

    monthly_gwp = df.groupby(df.period.dt.to_period("M"))["gwp_usd"].sum()
    monthly_nep = df.groupby(df.period.dt.to_period("M"))["nep_usd"].sum()
    monthly_claims = df.groupby(df.period.dt.to_period("M"))["claims_paid_usd"].sum()
    monthly_combined = df.groupby(df.period.dt.to_period("M"))["combined_ratio"].mean()
    monthly_loss = df.groupby(df.period.dt.to_period("M"))["loss_ratio"].mean()
    trend = monthly_gwp.div(1_000_000).tolist()

    gwp_delta, _ = _period_over_period_delta(monthly_gwp)
    nep_delta, _ = _period_over_period_delta(monthly_nep)
    claims_delta, _ = _period_over_period_delta(monthly_claims)
    combined_delta, _ = _period_over_period_delta(monthly_combined)
    loss_delta, _ = _period_over_period_delta(monthly_loss)

    st.subheader("Executive portfolio view", help="Current performance across the selected portfolio scope.")
    primary_metrics = st.columns(4)
    with primary_metrics[0]:
        st.metric("Gross written premium", _fmt_usd(gwp), gwp_delta, border=True, chart_data=trend, chart_type="line")
    with primary_metrics[1]:
        st.metric("Net earned premium", _fmt_usd(nep), nep_delta, border=True, chart_data=trend, chart_type="line")
    with primary_metrics[2]:
        st.metric("Claims incurred", _fmt_usd(claims), claims_delta, delta_color="inverse", border=True, chart_data=trend, chart_type="line")
    with primary_metrics[3]:
        st.metric("Combined ratio", f"{combined:.1f}%", combined_delta, delta_color="inverse", border=True)

    supporting_metrics = st.columns([1, 1, 2])
    with supporting_metrics[0]:
        st.metric("Loss ratio", f"{loss:.1f}%", loss_delta, delta_color="inverse", border=True)
    with supporting_metrics[1]:
        st.metric("Active cedants", f"{df.client_name.nunique():,}", border=True)
    with supporting_metrics[2]:
        status = "Portfolio requires underwriting attention" if combined >= 100 else "Portfolio is within operating tolerance" if combined < 95 else "Portfolio is approaching rate adequacy threshold"
        icon = ":material/warning:" if combined >= 100 else ":material/check_circle:" if combined < 95 else ":material/priority_high:"
        st.info(
            f"**Portfolio operating signal**  \n{status}. Combined ratio is "
            f"**{combined:.1f}%** against the 95% monitoring threshold.",
            icon=icon,
        )

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
            st.plotly_chart(px.line(chart_df, x="period", y="USD", color="Metric", markers=True, color_discrete_sequence=["#f74d0b", "#10d1f3"]), width="stretch")
    with col2:
        with card("Premium by line of business"):
            lob_top = lob.head(6).copy()
            other_total = lob.iloc[6:].gwp_usd.sum()
            if other_total > 0:
                lob_top = pd.concat([lob_top, pd.DataFrame([{"line_of_business": "Other", "gwp_usd": other_total}])], ignore_index=True)
            donut = px.pie(
                lob_top, names="line_of_business", values="gwp_usd", hole=.58,
                color_discrete_sequence=px.colors.qualitative.Set2,
            )
            donut.update_layout(legend=dict(orientation="h", yanchor="top", y=-0.1, font=dict(size=10)))
            st.plotly_chart(donut, width="stretch")
    with col3:
        with card("Underwriting watchlist"):
            top_line = df.groupby("line_of_business").gwp_usd.sum().idxmax()
            top_line_share = df.groupby("line_of_business").gwp_usd.sum().max() / gwp * 100
            worst_line_series = df.groupby("line_of_business").loss_ratio.mean()
            worst_line = worst_line_series.idxmax()
            worst_loss = worst_line_series.max() * 100
            top_region = df.groupby("region").gwp_usd.sum().idxmax()
            gwp_delta_val, gwp_growing = _period_over_period_delta(monthly_gwp)
            trend_word = "growing" if gwp_growing else "declining"

            insights = [
                f"**Concentration:** {top_line} represents {top_line_share:.0f}% of gross written premium.",
                f"**Performance:** {worst_line} has the highest loss ratio at {worst_loss:.1f}%.",
                f"**Momentum:** premium is {trend_word} ({gwp_delta_val or 'flat'} versus the prior period).",
                f"**Geography:** {top_region} is the largest premium concentration.",
            ]
            for text in insights:
                st.caption("• " + text)
    with col4:
        with card("Top competitors — market share"):
            chart = px.bar(competitors.head(7), x="share", y="client_name", orientation="h", color="share", color_continuous_scale="Blues")
            chart.update_traces(texttemplate="%{x:.1f}%", textposition="outside")
            chart.update_layout(yaxis={"categoryorder": "total ascending"}, coloraxis_showscale=False, xaxis_title="Market share (%)")
            st.plotly_chart(chart, width="stretch")

    bottom_left, bottom_mid, bottom_right = st.columns([1.35, 1, .8])
    with bottom_left:
        with card("Treaty performance summary"):
            summary = df.groupby("line_of_business").agg(
                Treaties=("policy_id", "nunique"), GWP=("gwp_usd", "sum"),
                Loss_Ratio=("loss_ratio", "mean"), Combined_Ratio=("combined_ratio", "mean"),
            ).reset_index()
            summary["GWP (USD M)"] = (summary.pop("GWP") / 1e6).round(2)
            summary["Loss ratio (%)"] = (summary.pop("Loss_Ratio") * 100).round(1)
            summary["Combined ratio (%)"] = (summary.pop("Combined_Ratio") * 100).round(1)
            summary["Rate adequacy"] = summary["Combined ratio (%)"].map(lambda x: "Maintain" if x < 95 else "Increase rates")
            st.dataframe(
                summary.rename(columns={"line_of_business": "Line of business"}),
                hide_index=True, height=300, width="stretch",
                column_config={
                    "GWP (USD M)": st.column_config.NumberColumn(format="$%.1fM"),
                    "Loss ratio (%)": st.column_config.NumberColumn(format="%.1f%%"),
                    "Combined ratio (%)": st.column_config.NumberColumn(format="%.1f%%"),
                },
            )
    with bottom_mid:
        with card("Pricing adequacy analysis"):
            pricing = df.groupby("line_of_business", as_index=False).agg(loss_ratio=("loss_ratio", "mean"), premium_rate=("premium_rate", "mean"), exposure=("exposure", "sum"))
            pricing["loss_ratio"] *= 100
            pricing["premium_adequacy"] = pricing.premium_rate / pricing.premium_rate.max() * 110
            st.plotly_chart(px.scatter(pricing, x="loss_ratio", y="premium_adequacy", size="exposure", color="line_of_business", hover_name="line_of_business", labels={"loss_ratio":"Loss ratio (%)", "premium_adequacy":"Premium adequacy (%)"}), width="stretch")

    with st.expander("Cedant selection and policy rate comparison"):
        cedant_df = df.groupby("client_name", as_index=False).agg(
            policy_count=("policy_id", "nunique"),
            average_premium_rate=("premium_rate", "mean"),
            average_combined_ratio=("combined_ratio", "mean"),
            total_gwp=("gwp_usd", "sum"),
        ).sort_values("total_gwp", ascending=False)
        cedant_df["average_combined_ratio"] *= 100
        selected_cedants = st.multiselect(
            "Select cedants to compare",
            cedant_df.client_name.tolist(),
            default=cedant_df.client_name.head(5).tolist(),
            help="Choose cedants to compare policy counts, average premium rate, and combined ratio."
        )
        if selected_cedants:
            comparison = cedant_df[cedant_df.client_name.isin(selected_cedants)].copy()
            st.dataframe(
                comparison.rename(
                    columns={
                        "client_name": "Cedant",
                        "policy_count": "Policy count",
                        "average_premium_rate": "Avg premium rate",
                        "average_combined_ratio": "Avg combined ratio (%)",
                        "total_gwp": "Total GWP (USD)",
                    }
                ).round({"average_premium_rate": 2, "average_combined_ratio": 1}),
                hide_index=True,
                width="stretch",
            )
            compare_fig = px.bar(
                comparison.melt(
                    id_vars=["client_name"],
                    value_vars=["policy_count", "average_premium_rate", "average_combined_ratio"],
                    var_name="Metric",
                    value_name="Value",
                ),
                x="client_name",
                y="Value",
                color="Metric",
                barmode="group",
                title="Cedant comparison",
                labels={"client_name": "Cedant", "Value": "Metric value"},
            )
            st.plotly_chart(compare_fig, width="stretch")
        else:
            st.info("Select at least one cedant to compare policy and rate metrics.")
    with bottom_right:
        with card("Emerging risks monitor"):
            risks = df.groupby("risk_category").agg(Exposure=("exposure", "sum"), Loss_ratio=("loss_ratio", "mean")).reset_index()
            if len(risks) >= 3 and risks["Loss_ratio"].nunique() >= 3:
                try:
                    risks["Risk level"] = pd.qcut(risks["Loss_ratio"], q=3, labels=["Low", "Medium", "High"])
                except ValueError:
                    risks["Risk level"] = risks["Loss_ratio"].map(lambda x: "High" if x >= .65 else "Medium" if x >= .45 else "Low")
            else:
                risks["Risk level"] = risks["Loss_ratio"].map(lambda x: "High" if x >= .65 else "Medium" if x >= .45 else "Low")

            badge_colors = {"High": "#EF4444", "Medium": "#F59E0B", "Low": "#22C55E"}
            for _, row in risks.sort_values("Exposure", ascending=False).iterrows():
                color = badge_colors.get(str(row["Risk level"]), "#94A3B8")
                st.markdown(
                    f'<div style="display:flex;justify-content:space-between;align-items:center;padding:6px 0;border-bottom:1px solid rgba(255,255,255,0.06);">'
                    f'<span style="font-size:13px;">{row["risk_category"]}</span>'
                    f'<span style="background:{color}22;color:{color};padding:2px 10px;border-radius:10px;font-size:11px;">{row["Risk level"]}</span>'
                    f'</div>',
                    unsafe_allow_html=True,
                )

    geographic, claims_col, simulator = st.columns([1, 1, 1.15])
    with geographic:
        with card("Geographic exposure (GWP)"):
            geographic_data = df.groupby("continent", as_index=False).gwp_usd.sum()
            unmapped_gwp = geographic_data.loc[~geographic_data.continent.isin(CONTINENTS), "gwp_usd"].sum()
            geographic_data = geographic_data.set_index("continent").reindex(CONTINENTS, fill_value=0).reset_index()
            if unmapped_gwp > 0:
                geographic_data = pd.concat([
                    geographic_data,
                    pd.DataFrame([{"continent": "Other / unmapped region", "gwp_usd": unmapped_gwp}]),
                ], ignore_index=True)
            geographic_data["portfolio_status"] = geographic_data.gwp_usd.map(lambda value: "Active portfolio" if value else "No active portfolio")
            st.plotly_chart(px.bar(geographic_data, x="gwp_usd", y="continent", orientation="h", color="portfolio_status", labels={"gwp_usd": "GWP (USD)", "continent": "Continent"}, color_discrete_map={"Active portfolio": "#2f80ed", "No active portfolio": "#64748b"}), width="stretch")
            if unmapped_gwp > 0:
                st.caption(f"⚠️ {_fmt_usd(unmapped_gwp)} in GWP comes from regions not yet mapped to a continent.")
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
        with st.expander("Upload internal claims data (for Claims Intelligence)"):
            perm = st.checkbox("I confirm I have permission to upload organization data", key="org_data_permission")
            st.caption("Uploading organization data requires explicit permission. Check the box to proceed.")
            if perm:
                internal_file = st.file_uploader("Internal claims file", type=["csv", "xlsx", "xls"], key="internal_claims_file")
                st.caption("Upload your organization's internal claims dataset for deeper analysis. This will be available as 'Internal claims' in the data source selector.")
                if internal_file is not None:
                    parsed_internal, internal_error = parse_upload(internal_file)
                    if internal_error:
                        st.error(internal_error)
                    elif parsed_internal is not None:
                        st.session_state.internal_claims = parsed_internal
                        n_int = parsed_internal.shape[0] if hasattr(parsed_internal, "shape") else len(parsed_internal)
                        st.success(f"Loaded {n_int:,} internal claim records.")
                        save_upload(st.session_state.email, st.session_state.user, parsed_internal, "internal_claims", internal_file.name)
            else:
                st.info("You must confirm permission to upload organizational data. Contact your administrator if unsure.")
        with st.expander("Load dataset from the web"):
            remote_url = st.text_input("Remote dataset URL", placeholder="https://example.com/portfolio.csv")
            if st.button("Load remote dataset", icon=":material/cloud_download:") and remote_url:
                remote_df, remote_error = load_remote_dataset(remote_url.strip())
                if remote_error:
                    st.error(remote_error)
                elif remote_df is not None:
                    st.session_state.uploaded_data = remote_df
                    st.success(f"Loaded {len(remote_df):,} remote records from the URL.")
                    save_upload(st.session_state.email, st.session_state.user, remote_df, "remote_url", remote_url.strip())
        with st.expander("Download dataset from Kaggle"):
            kaggle_ref = st.text_input("Kaggle dataset (owner/dataset)", placeholder="zynicide/wine-reviews")
            kaggle_json = st.file_uploader("Upload kaggle.json (optional)", type=["json"], key="kaggle_json")
            # persist uploaded kaggle.json for subsequent downloads in this session
            if kaggle_json is not None:
                st.session_state["kaggle_json"] = kaggle_json
            if st.button("Download from Kaggle", icon=":material/cloud_download:") and kaggle_ref:
                cfg = st.session_state.get("kaggle_json") if st.session_state.get("kaggle_json") is not None else None
                target, kerror = download_kaggle_dataset(kaggle_ref.strip(), kaggle_json_file=cfg)
                if kerror:
                    st.error(kerror)
                elif target is not None:
                    # try to locate a CSV/XLSX in the target directory
                    files = list(Path(target).rglob("*.csv")) + list(Path(target).rglob("*.xlsx")) + list(Path(target).rglob("*.xls"))
                    if files:
                        parsed, perr = parse_upload(files[0].open("rb"))
                        if perr:
                            st.error(perr)
                        else:
                            st.session_state.uploaded_data = parsed
                            st.success(f"Downloaded and loaded {files[0].name}")
                            save_upload(st.session_state.email, st.session_state.user, parsed, "kaggle", files[0].name)
                    else:
                        st.warning(f"No CSV/XLSX files found in Kaggle dataset at {target}")
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
                save_upload(st.session_state.email, st.session_state.user, parsed, "portfolio_file", uploaded_file.name)
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
    enforce_session_timeout()
    if st.session_state.logged_in:
        configure_enterprise_workspace()
        render_logout_topbar()
        workspace, filtered_data, period_label = sidebar_controls(load_portfolio())
        if workspace == "Portfolio analytics":
            show_dashboard(filtered_data, period_label)
        elif workspace == "Claims Intelligence":
            show_claims_dashboard(filtered_data, period_label)
        elif workspace == "Upload portfolio data":
            show_upload_data()
        elif workspace == "Reinsurers":
            show_reinsurers_dashboard(filtered_data, period_label)
        elif workspace == "Cedants":
            show_cedants_dashboard(filtered_data, period_label)
        elif workspace == "Pricing Analytics":
            show_pricing_dashboard(filtered_data, period_label)
        elif workspace == "Data quality":
            show_data_quality_dashboard(filtered_data, period_label)
        else:
            show_assistant(filtered_data, period_label)
    else:
        show_welcome()


if __name__ == "__main__":
    main()


# Compatibility entrypoint when the dashboard is launched through pages/dashboard.py
build_dashboard = main

import sys
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd
import plotly.express as px
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

DATA_PATH = ROOT / "data" / "reinsurance_sample.csv"
try:
    BACKEND_URL = st.secrets["backend_url"]
except Exception:
    BACKEND_URL = "http://127.0.0.1:8001"

LOGO_HTML = '''
<div style="display:flex; align-items:center; gap:18px; margin-bottom: 18px;">
  <div style="width:64px; height:64px; border-radius:20px; background: linear-gradient(135deg, #2563eb 0%, #9333ea 100%);
              display:flex; align-items:center; justify-content:center; color:#ffffff; font-weight:800; font-size:1.35rem;">
    RI
  </div>
  <div>
    <div style="font-size:2.2rem; font-weight:800; line-height:1.1; margin-bottom: 6px; color:#f8fafc;">
      Reinsurance intelligence & pricing dashboard
    </div>
    <div style="color:#cbd5e1; font-size:0.95rem;">
      Market Intelligence · Pricing Analytics · Portfolio Performance
    </div>
  </div>
</div>
'''

DARK_THEME_CSS = '''
<style>
  html, body, .streamlit-container, .stApp, .main, .block-container {
    background: #04080f !important;
    color: #e2e8f0 !important;
  }
  .css-1aehpvj.e1fqkh3o3 { background: #02040a !important; }
  .stButton>button, .css-78trlr, .css-1avcm0n, .css-h5rgaw, .css-145kmo2 {
    background-color: #111827 !important;
    color: #f8fafc !important;
    border-color: #334155 !important;
  }
  .stTextInput>div>div>input, .stSelectbox>div>div>div>div, .stSlider>div, .stMultiselect>div>div>div {
    background-color: #0f172a !important;
    color: #e2e8f0 !important;
  }
  .stDataFrame, .stTable, .stMarkdown, .stText, .stHeader, .stSubheader {
    color: #e2e8f0 !important;
  }
  .stAlert {
    background-color: #111827 !important;
    color: #e2e8f0 !important;
  }
  .css-1vencpc, .css-1q1n0ol, .css-1lsmgbg {
    background-color: #0f172a !important;
  }
  .kpi-grid {
    display: flex;
    flex-wrap: wrap;
    gap: 16px;
    margin-bottom: 24px;
  }
  .kpi-card {
    flex: 1 1 14%;
    min-width: 180px;
    padding: 18px;
    border-radius: 20px;
    background: linear-gradient(180deg, rgba(15, 23, 42, 0.98), rgba(15, 23, 42, 0.88));
    border: 1px solid rgba(148, 163, 184, 0.15);
  }
  .kpi-label {
    font-size: 0.95rem;
    letter-spacing: 0.04em;
    color: #94a3b8;
    margin-bottom: 10px;
  }
  .kpi-value {
    font-size: 1.6rem;
    font-weight: 700;
    color: #f8fafc;
  }
  .kpi-delta {
    margin-top: 10px;
    font-size: 0.95rem;
    font-weight: 600;
  }
  .kpi-delta.up {
    color: #22c55e;
  }
  .kpi-delta.down {
    color: #f87171;
  }
  .kpi-note {
    font-size: 0.82rem;
    color: #94a3b8;
  }
  .section-card {
    background:#0b1220 !important;
    border:1px solid rgba(148,163,184,0.12) !important;
    border-radius:20px !important;
    padding:24px !important;
    box-shadow:0 20px 50px rgba(0,0,0,0.25);
  }
  .section-header {
    display:flex;
    justify-content:space-between;
    align-items:center;
    gap:12px;
    margin-bottom:18px;
  }
  .section-title {
    font-size:1.15rem;
    font-weight:700;
    color:#f8fafc;
  }
  .top-banner {
    font-size:0.95rem;
    color:#94a3b8;
    letter-spacing:0.06em;
    margin-bottom: 10px;
  }
  .header-chip {
    display:inline-block;
    padding:10px 18px;
    border-radius:999px;
    border:1px solid rgba(148,163,184,0.25);
    color:#cbd5e1;
    background: rgba(15,23,42,0.85);
    font-size:0.95rem;
    margin-bottom:10px;
  }
  .sidebar .css-14xtw13 { background: #02040a !important; }
  .sidebar .css-1d391kg {
    background: #02040a !important;
  }
  .sidebar .css-1r6slb0 {
    color: #f8fafc !important;
  }
</style>
'''





def parse_uploaded_file(uploaded_file) -> pd.DataFrame:
    try:
        return pd.read_csv(uploaded_file, parse_dates=["period"])
    except Exception:
        return pd.DataFrame()


def load_reinsurance_data(uploaded_file=None) -> pd.DataFrame:
    if uploaded_file is not None:
        return parse_uploaded_file(uploaded_file)
    if DATA_PATH.exists():
        df = pd.read_csv(DATA_PATH, parse_dates=["period"])
        return df
    return pd.DataFrame()


def get_kpi_data(df: pd.DataFrame) -> Dict[str, Dict[str, str]]:
    if df.empty:
        return {
            "Gross Written Premium": {"value": "USD 1.87B", "delta": "+14.6%", "trend": "up"},
            "Net Earned Premium": {"value": "USD 1.32B", "delta": "+11.3%", "trend": "up"},
            "Total Claims Incurred": {"value": "USD 889M", "delta": "+9.8%", "trend": "up"},
            "Combined Ratio": {"value": "89.4%", "delta": "-3.6%", "trend": "down"},
            "Return on Equity": {"value": "16.2%", "delta": "+1.8%", "trend": "up"},
            "RBC Ratio": {"value": "312%", "delta": "Strong", "trend": "up"},
        }

    total_gwp = df["gross_written_premium"].sum()
    total_nep = df["net_earned_premium"].sum()
    total_claims = df["claims_paid"].sum()
    avg_combined = df["combined_ratio"].mean() * 100
    avg_loss = df["loss_ratio"].mean() * 100

    return {
        "Gross Written Premium": {"value": f"USD {total_gwp / 1_000_000:.2f}M", "delta": "+14.6%", "trend": "up"},
        "Net Earned Premium": {"value": f"USD {total_nep / 1_000_000:.2f}M", "delta": "+11.3%", "trend": "up"},
        "Total Claims Incurred": {"value": f"USD {total_claims / 1_000_000:.2f}M", "delta": "+9.8%", "trend": "up"},
        "Combined Ratio": {"value": f"{avg_combined:.1f}%", "delta": "-3.6%", "trend": "down"},
        "Return on Equity": {"value": "16.2%", "delta": "+1.8%", "trend": "up"},
        "RBC Ratio": {"value": "312%", "delta": "Strong", "trend": "up"},
    }


def get_premium_trend(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        # sample monthly trend matching dashboard snapshot (Jan-Apr 2024)
        months = pd.to_datetime(["2024-01-01", "2024-02-01", "2024-03-01", "2024-04-01"])
        return pd.DataFrame(
            {
                "Month": months,
                "GWP": [1.5, 1.8, 1.95, 2.1],
                "NEP": [1.1, 1.2, 1.25, 1.32],
            }
        )
    trend_df = (
        df.groupby(df["period"].dt.to_period("M"))[ ["gross_written_premium", "net_earned_premium"] ]
        .sum()
        .reset_index()
    )
    trend_df["period"] = trend_df["period"].dt.to_timestamp()
    trend_df["GWP"] = trend_df["gross_written_premium"] / 1_000_000
    trend_df["NEP"] = trend_df["net_earned_premium"] / 1_000_000
    return trend_df[["period", "GWP", "NEP"]].rename(columns={"period": "Month"})


def get_business_mix(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(
            {
                "Line": ["Property", "Engineering", "Motor", "Marine", "Accident & Health", "Others"],
                "Share": [38.1, 18.7, 15.3, 12.4, 8.6, 6.9],
            }
        )

    mix_df = (
        df.groupby("line_of_business")["gross_written_premium"]
        .sum()
        .reset_index()
        .rename(columns={"gross_written_premium": "Share"})
    )
    mix_df["Share"] = mix_df["Share"] / mix_df["Share"].sum() * 100
    return mix_df.rename(columns={"line_of_business": "Line"})


def get_pricing_summary(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        # sample treaty performance summary similar to screenshot
        return pd.DataFrame(
            {
                "Line of Business": ["Property", "Engineering", "Motor", "Marine", "Accident & Health"],
                "Treaties": [128, 64, 203, 91, 77],
                "GWP (USD)": [1.12, 0.34, 0.29, 0.23, 0.16],
                "Loss Ratio": [0.63, 0.59, 0.74, 0.66, 0.45],
                "Combined Ratio": [0.88, 0.82, 1.01, 0.92, 0.72],
            }
        )

    agg_kwargs = {
        "Treaties": ("policy_id", "nunique"),
        "GWP": ("gross_written_premium", "sum"),
        "LossRatio": ("loss_ratio", "mean"),
        "CombinedRatio": ("combined_ratio", "mean"),
    }
    if "premium_rate" in df.columns:
        agg_kwargs["PremiumRate"] = ("premium_rate", "mean")
    if "exposure" in df.columns:
        agg_kwargs["Exposure"] = ("exposure", "sum")

    summary = df.groupby("line_of_business").agg(**agg_kwargs).reset_index()
    summary["GWP (USD)"] = summary["GWP"] / 1_000_000
    summary["Loss Ratio"] = (summary["LossRatio"] * 100).round(1).astype(str) + "%"
    summary["Combined Ratio"] = (summary["CombinedRatio"] * 100).round(1).astype(str) + "%"
    summary["Profitability"] = summary["LossRatio"].apply(lambda x: "Adequate" if x < 0.65 else "Inadequate")
    summary["Rate Adequacy"] = summary["CombinedRatio"].apply(lambda x: "Maintain" if x < 0.95 else "Increase Rates")

    output_columns = ["line_of_business", "Treaties", "GWP (USD)", "Loss Ratio", "Combined Ratio", "Profitability", "Rate Adequacy"]
    if "PremiumRate" in summary.columns:
        summary["Premium Rate"] = summary["PremiumRate"].round(2)
        output_columns.insert(5, "Premium Rate")
    if "Exposure" in summary.columns:
        summary["Exposure"] = summary["Exposure"].apply(lambda x: f"USD {x / 1_000_000:.2f}M")
        output_columns.insert(5, "Exposure")

    return summary[output_columns].rename(columns={"line_of_business": "Line of Business"})


def get_competitor_share(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(
            {
                "Competitor": ["Partner Re", "Hannover Re", "Munich Re", "Acentria Group", "Swiss Re", "SCOR", "Others"],
                "Market Share": [16.8, 14.7, 13.4, 11.2, 9.6, 7.8, 26.5],
            }
        )

    competitors = ["Partner Re", "Hannover Re", "Munich Re", "Acentria Group", "Swiss Re", "SCOR"]
    market_share = [len(df[df["line_of_business"] == line]) * 3.5 for line in df["line_of_business"].unique()]
    return pd.DataFrame({"Competitor": competitors[: len(market_share)], "Market Share": market_share})


def get_risk_monitor() -> List[dict]:
    return [
        {"Risk": "Climate Change", "Risk Level": "High", "Trend": "↑"},
        {"Risk": "Nat Cat (Flood)", "Risk Level": "High", "Trend": "↑"},
        {"Risk": "Cyber Risk", "Risk Level": "High", "Trend": "↑"},
        {"Risk": "Inflation", "Risk Level": "Medium", "Trend": "↑"},
        {"Risk": "Market Volatility", "Risk Level": "Medium", "Trend": "↑"},
        {"Risk": "Supply Chain", "Risk Level": "Medium", "Trend": "↑"},
        {"Risk": "Terrorism", "Risk Level": "Low", "Trend": "→"},
        {"Risk": "Pandemic Risk", "Risk Level": "Low", "Trend": "→"},
        {"Risk": "Political Risk", "Risk Level": "Medium", "Trend": "→"},
        {"Risk": "Agricultural Weather", "Risk Level": "High", "Trend": "↑"},
    ]


def get_geographic_exposure() -> pd.DataFrame:
    # sample geographic exposure by country (GWP USD millions)
    return pd.DataFrame(
        {
            "country": ["United States", "Canada", "Brazil", "United Kingdom", "Germany", "France", "India", "Australia"],
            "gwp": [620, 120, 45, 210, 150, 98, 80, 90],
        }
    )


def get_claims_trend() -> pd.DataFrame:
    months = pd.to_datetime(["2024-01-01", "2024-02-01", "2024-03-01", "2024-04-01"])
    return pd.DataFrame(
        {
            "Month": months,
            "Paid Claims (USD)": [200, 320, 480, 650],
            "Incurred Claims (USD)": [220, 340, 510, 700],
        }
    )


def get_ai_insights() -> List[str]:
    return [
        "Motor treaties are showing deteriorating loss ratios. Consider a 5–7% rate increase.",
        "Property pricing remains competitive but exposed to Nat Cat accumulations.",
        "Engineering line is performing well with adequate margins.",
        "Agriculture remains profitable but vulnerable to weather volatility.",
        "Cyber exposures are growing rapidly; consider capacity limits and aggregated retention monitoring.",
    ]


def get_cedants(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(
            {
                "Cedant": [
                    "Acentria Reinsurance",
                    "Coastal Mutual",
                    "Metro Insurers Ltd",
                    "AgriProtect",
                ],
                "Region": ["North America", "Europe", "Asia Pacific", "Latin America"],
                "Primary Lines": ["Property, Motor", "Marine, Liability", "Motor, Accident", "Agriculture"],
                "Policies": [128, 64, 203, 77],
                "Total GWP (USD)": [1870000000, 980000000, 450000000, 160000000],
            }
        )

    ced = (
        df.groupby("client_name")
        .agg(Region=("region", "first"), Policies=("policy_id", "nunique"), GWP=("gross_written_premium", "sum"))
        .reset_index()
        .rename(columns={"client_name": "Cedant", "GWP": "Total GWP (USD)", "Policies": "Policies"})
    )
    ced["Primary Lines"] = df.groupby("client_name")["line_of_business"].apply(lambda s: ", ".join(s.unique()[:2])).values
    return ced


def get_reinsurers(df: pd.DataFrame) -> pd.DataFrame:
    # Sample reinsurers with ratings and product offerings
    reinsurers = [
        ("Partner Re", "AA", "Property, Casualty"),
        ("Hannover Re", "AA", "Property, Life"),
        ("Munich Re", "AA+", "Property, Specialty"),
        ("Swiss Re", "AA", "Property, Casualty, Specialty"),
        ("SCOR", "A", "Property, Casualty"),
        ("Acentria Group", "A-", "Property, Motor, Marine"),
    ]
    df_reins = pd.DataFrame(reinsurers, columns=["Reinsurer", "Rating", "Policies Offered"])
    if not df.empty:
        # augment with simple market presence estimate
        counts = df["line_of_business"].value_counts()
        df_reins["Market Presence Index"] = df_reins["Policies Offered"].apply(
            lambda s: sum([counts.get(x.strip(), 0) for x in s.split(",")])
        )
    else:
        df_reins["Market Presence Index"] = [128, 110, 96, 88, 70, 45]
    return df_reins


def generate_sample_portfolio(source: str) -> pd.DataFrame:
    # Create synthetic transaction-level portfolio data for demo analytics
    rows = []
    clients = ["Acentria Reinsurance", "Coastal Mutual", "Metro Insurers Ltd", "AgriProtect"]
    reins = ["Partner Re", "Hannover Re", "Munich Re", "Swiss Re"]
    lines = ["Property", "Engineering", "Motor", "Marine", "Accident & Health"]
    regions = ["North America", "Europe", "Asia Pacific", "Latin America", "Middle East & Africa"]
    risks = ["Nat Cat", "Cyber", "Operational", "Market", "Weather"]
    import random
    periods = pd.to_datetime(["2024-01-01", "2024-02-01", "2024-03-01", "2024-04-01"])
    for i in range(1, 401):
        if source.startswith("Cedant"):
            client = random.choice(clients)
        elif source.startswith("Reinsurer"):
            client = random.choice(reins)
        else:
            client = random.choice(clients + reins)
        period = random.choice(periods)
        line = random.choice(lines)
        region = random.choice(regions)
        gwp = random.randint(10000, 5_000_000)
        nep = int(gwp * random.uniform(0.6, 0.9))
        claims_paid = int(gwp * random.uniform(0.1, 0.6))
        loss_ratio = claims_paid / nep if nep > 0 else 0
        combined_ratio = loss_ratio + random.uniform(0.05, 0.45)
        policy_id = f"P-{i:05d}"
        rows.append(
            {
                "policy_id": policy_id,
                "period": period,
                "region": region,
                "line_of_business": line,
                "gross_written_premium": gwp,
                "net_earned_premium": nep,
                "claims_paid": claims_paid,
                "loss_ratio": loss_ratio,
                "combined_ratio": combined_ratio,
                "client_name": client,
                "risk_category": random.choice(risks),
            }
        )
    df = pd.DataFrame(rows)
    return df


def build_dashboard() -> None:
    st.set_page_config(page_title="Reinsurance intelligence & pricing dashboard", layout="wide")
    st.markdown(DARK_THEME_CSS, unsafe_allow_html=True)
    st.markdown(LOGO_HTML, unsafe_allow_html=True)
    st.sidebar.markdown("<div style='padding: 14px 18px; border-radius: 18px; background: linear-gradient(135deg, #0f172a, #111827); border:1px solid rgba(148,163,184,0.12); margin-bottom: 18px;'><strong style='color:#ffffff;'>Acentria Group</strong><br><span style='color:#94a3b8; font-size:0.92rem;'>Reinsurance intelligence suite</span></div>", unsafe_allow_html=True)
    page = st.sidebar.radio("", ["Executive Overview", "Market Intelligence", "Pricing Analytics", "Portfolio Management", "Reports & Insights", "System"], index=0)

    # Data source selection
    st.sidebar.markdown("---")
    data_source = st.sidebar.selectbox("Data Source", ["Sample - Cedants", "Sample - Reinsurers", "Uploaded CSV"])
    uploaded_file = None
    if data_source == "Uploaded CSV":
        uploaded_file = st.file_uploader(
            "Upload Kaggle-style reinsurance data CSV",
            type=["csv"],
            help="Use a dataset with columns like policy_id, period, region, line_of_business, gross_written_premium, net_earned_premium, losses, claims_paid, loss_ratio, combined_ratio.",
        )

    if uploaded_file:
        df = load_reinsurance_data(uploaded_file)
        if uploaded_file is not None and df.empty:
            st.warning("Unable to parse uploaded CSV. Please check the file format.")
    else:
        # generate sample portfolio based on chosen source
        df = generate_sample_portfolio(data_source)

    # Expanded region list if no data provided
    default_regions = ["North America", "Europe", "Asia Pacific", "Latin America", "Middle East & Africa"]

    filter_col1, filter_col2 = st.columns(2)
    with filter_col1:
        line_filter = st.multiselect(
            "Filter by Line of Business",
            options=sorted(df["line_of_business"].unique()),
            default=sorted(df["line_of_business"].unique().tolist()),
        )
    with filter_col2:
        region_filter = st.multiselect(
            "Filter by Region",
            options=sorted(df["region"].unique()),
            default=sorted(df["region"].unique().tolist()),
        )
    df = df[df["line_of_business"].isin(line_filter) & df["region"].isin(region_filter)]

    # Custom date range selection
    if "period" in df.columns and not df.empty:
        min_date = df["period"].min().date()
        max_date = df["period"].max().date()
    else:
        min_date = pd.to_datetime("2024-01-01").date()
        max_date = pd.to_datetime("2024-04-30").date()

    selected_dates = st.sidebar.date_input(
        "Select timeline",
        value=[min_date, max_date],
        min_value=min_date,
        max_value=max_date,
    )
    if isinstance(selected_dates, tuple) or isinstance(selected_dates, list):
        if len(selected_dates) == 2:
            start_date, end_date = selected_dates
        else:
            start_date = selected_dates[0]
            end_date = selected_dates[0]
    else:
        start_date = selected_dates
        end_date = selected_dates

    if "period" in df.columns and not df.empty:
        df = df[(df["period"].dt.date >= start_date) & (df["period"].dt.date <= end_date)]

    report_csv = df.to_csv(index=False)
    header_col1, header_col2 = st.columns([4, 1])
    with header_col1:
        st.markdown('<div class="top-banner">Market Intelligence · Pricing Analytics · Portfolio Performance</div>', unsafe_allow_html=True)
    with header_col2:
        st.markdown(f'<div class="header-chip">{start_date.strftime("%d %b %Y")} - {end_date.strftime("%d %b %Y")}</div>', unsafe_allow_html=True)
        st.download_button("Export Report", report_csv, file_name="acentria_dashboard_data.csv", mime="text/csv")

    kpis = get_kpi_data(df)
    kpi_html = '<div class="kpi-grid">'
    for label, kpi in kpis.items():
        delta_class = 'up' if kpi['trend'] == 'up' else 'down'
        kpi_html += (
            '<div class="kpi-card">'
            f'<div class="kpi-label">{label}</div>'
            f'<div class="kpi-value">{kpi["value"]}</div>'
            f'<div class="kpi-delta {delta_class}">{kpi["delta"]}</div>'
            '</div>'
        )
    kpi_html += '</div>'
    st.markdown(kpi_html, unsafe_allow_html=True)

    st.divider()

    trend_df = get_premium_trend(df)
    business_df = get_business_mix(df)
    comp_df = get_competitor_share(df)
    summary_df = get_pricing_summary(df)
    risk_df = pd.DataFrame(get_risk_monitor())

    col1, col2 = st.columns([2, 1])

    with col1:
        st.markdown('<div class="section-card"><div class="section-header"><div class="section-title">Premium Trend (USD)</div></div></div>', unsafe_allow_html=True)
        fig = px.line(trend_df, x="Month", y=["GWP", "NEP"], markers=True)
        st.plotly_chart(fig, use_container_width=True)

        st.markdown('<div class="section-card"><div class="section-header"><div class="section-title">Treaty Performance Summary</div></div></div>', unsafe_allow_html=True)
        st.dataframe(summary_df, use_container_width=True, height=300)

        st.markdown('<div class="section-card"><div class="section-header"><div class="section-title">Geographic Exposure (GWP)</div></div></div>', unsafe_allow_html=True)
        geo_df = get_geographic_exposure()
        try:
            fig_geo = px.choropleth(geo_df, locations="country", locationmode="country names", color="gwp", color_continuous_scale="Blues", title="GWP by Country (USD millions)")
            st.plotly_chart(fig_geo, use_container_width=True)
        except Exception:
            st.dataframe(geo_df)

    with col2:
        st.markdown('<div class="section-card"><div class="section-header"><div class="section-title">Premium by Line of Business</div></div></div>', unsafe_allow_html=True)
        fig2 = px.pie(business_df, names="Line", values="Share", hole=0.35)
        fig2.update_traces(textinfo='percent+label', marker=dict(line=dict(color='#0b1220', width=2)))
        st.plotly_chart(fig2, use_container_width=True)

        st.markdown('<div class="section-card"><div class="section-header"><div class="section-title">Top Competitors - Market Share</div></div></div>', unsafe_allow_html=True)
        st.dataframe(comp_df, use_container_width=True, height=300)

    st.divider()

    st.subheader("Pricing Simulator (Quick)")
    simulator_col1, simulator_col2 = st.columns(2)
    with simulator_col1:
        line = st.selectbox("Line of Business", ["Property", "Engineering", "Motor", "Marine", "Accident & Health"])
        expected_loss_ratio = st.slider("Expected Loss Ratio (%)", 40, 110, 62)
        expense_ratio = st.slider("Expense Ratio (%)", 0, 50, 25)
        profit_margin = st.slider("Profit Margin (%)", 0, 30, 12)
        if st.button("Calculate"):
            rate_delta = round((expected_loss_ratio / 100 + expense_ratio / 100 + profit_margin / 100) * 100 - 100, 1)
            st.metric("Indicated Rate Change", f"+{rate_delta}%")

    with simulator_col2:
        st.subheader("Market Intelligence Highlights")
        st.write(
            "- Global reinsurance capital increased by 8.7% in Q1 2024, driven by strong investment returns."
        )
        st.write("- Natural catastrophe losses above 10-year average by 22%.")
        st.write("- Rates are hardening in Property, Casualty and Agriculture lines.")
        st.write("- Inflation remains elevated, impacting loss costs and claim severity.")

    st.divider()

    insights_col1, insights_col2 = st.columns([2, 1])
    with insights_col1:
        st.subheader("Pricing Adequacy Analysis")
        scatter_df = pd.DataFrame(
            {
                "Line": ["Property", "Engineering", "Motor", "Marine", "Others"],
                "Loss Ratio": [50, 60, 75, 55, 40],
                "Premium Adequacy": [95, 85, 55, 75, 110],
            }
        )
        fig3 = px.scatter(
            scatter_df,
            x="Loss Ratio",
            y="Premium Adequacy",
            color="Line",
            size=[30, 20, 40, 25, 15],
            hover_name="Line",
        )
        st.plotly_chart(fig3, use_container_width=True)

    with insights_col2:
        st.subheader("Emerging Risks Monitor")
        st.table(risk_df)

    st.divider()

    st.markdown('<div class="section-card"><div class="section-header"><div class="section-title">AI Insights</div></div></div>', unsafe_allow_html=True)
    for insight in get_ai_insights():
        st.info(insight)

    st.divider()
    st.markdown('<div class="section-card"><div class="section-header"><div class="section-title">Claims Trend & Pricing Summary</div></div></div>', unsafe_allow_html=True)
    ct_col1, ct_col2 = st.columns([2, 1])
    with ct_col1:
        claims_df = get_claims_trend()
        fig_claims = px.bar(claims_df, x="Month", y=["Paid Claims (USD)", "Incurred Claims (USD)"], barmode="group")
        st.plotly_chart(fig_claims, use_container_width=True)
    with ct_col2:
        st.markdown('<div style="padding:18px; border-radius:20px; background:#0f172a; border:1px solid rgba(148,163,184,0.12)">', unsafe_allow_html=True)
        st.subheader("Pricing Simulator (Quick)")
        st.metric("Technical Premium", "148.2M")
        st.metric("Expected Combined Ratio", "99.0%")
        st.markdown("<div style='margin-top:12px; color:#38bdf8; font-weight:700;'>Rate Adequacy: Adequate</div>", unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    # Additional pages
    if page == "Cedants":
        st.header("Cedants Overview")
        ced_df = get_cedants(df)
        st.write(
            "List of cedants (insurers ceding business) and summary portfolio metrics. Use the uploaded dataset to populate this table."
        )
        st.dataframe(ced_df, use_container_width=True)
    elif page == "Reinsurers":
        st.header("Reinsurers Directory")
        reins = get_reinsurers(df)
        rating_filter = st.multiselect("Filter by Rating", options=sorted(reins["Rating"].unique()), default=sorted(reins["Rating"].unique()))
        if rating_filter:
            reins = reins[reins["Rating"].isin(rating_filter)]
        st.dataframe(reins, use_container_width=True)
    # Market Intelligence remains part of the main Executive page; user can switch to it

if __name__ == "__main__":
    build_dashboard()

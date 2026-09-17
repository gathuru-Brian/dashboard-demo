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
CURRENCY_EXCHANGE_RATES_USD = {
    "USD": 1.0,
    "KES": 0.00645,
    "EUR": 1.09,
    "GBP": 1.27,
    "AED": 0.27,
    "ZAR": 0.053,
    "NGN": 0.0024,
}
CURRENCY_RATINGS = {
    "USD": "AAA",
    "KES": "BBB",
    "EUR": "AA+",
    "GBP": "AA",
    "AED": "A+",
    "ZAR": "BB-",
    "NGN": "B-",
}
try:
    BACKEND_URL = st.secrets["backend_url"]
except Exception:
    BACKEND_URL = "http://127.0.0.1:8501"

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

    total_gwp = df["gwp_usd"].sum() if "gwp_usd" in df.columns else df["gross_written_premium"].sum()
    total_nep = df["nep_usd"].sum() if "nep_usd" in df.columns else df["net_earned_premium"].sum()
    total_claims = df["claims_paid_usd"].sum() if "claims_paid_usd" in df.columns else df["claims_paid"].sum()
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
        "GWP": ("gwp_usd" if "gwp_usd" in df.columns else "gross_written_premium", "sum"),
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
    """
    Calculate competitor market share dynamically from the available data.
    Falls back to sample data if required columns are missing.
    """

    # Default data if DataFrame is empty
    if df.empty:
        return pd.DataFrame({
            "Competitor": [
                "Partner Re",
                "Hannover Re",
                "Munich Re",
                "Acentria Group",
                "Swiss Re",
                "SCOR",
                "Others"
            ],
            "Market Share": [
                16.8,
                14.7,
                13.4,
                11.2,
                9.6,
                7.8,
                26.5
            ]
        })

    # Possible column names containing competitor names
    possible_competitor_columns = [
        "client",
        "source",
        "reinsurer",
        "cedant",
        "company",
        "competitor",
        "broker"
    ]

    competitor_col = None

    for col in possible_competitor_columns:
        if col in df.columns:
            competitor_col = col
            break

    # Check for required data
    if competitor_col is None or "gwp" not in df.columns:
        st.warning("Unable to calculate market share. Using sample market data.")

        return pd.DataFrame({
            "Competitor": [
                "Partner Re",
                "Hannover Re",
                "Munich Re",
                "Acentria Group",
                "Swiss Re",
                "SCOR",
                "Others"
            ],
            "Market Share": [
                16.8,
                14.7,
                13.4,
                11.2,
                9.6,
                7.8,
                26.5
            ]
        })

    # Calculate market share
    competitor_share = (
        df.groupby(competitor_col)["gwp"]
          .sum()
          .sort_values(ascending=False)
    )

    competitor_share = (
        competitor_share / competitor_share.sum() * 100
    ).round(2)

    return (
        competitor_share
        .reset_index()
        .rename(columns={
            competitor_col: "Competitor",
            "gwp": "Market Share"
        })
    )

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


def filter_portfolio_data(df: pd.DataFrame) -> tuple[pd.DataFrame, str, str, tuple[pd.Timestamp, pd.Timestamp]]:
    data_source = st.sidebar.selectbox("Data Source", ["Sample - Cedants", "Sample - Reinsurers", "Uploaded CSV"])
    uploaded_file = None
    if data_source == "Uploaded CSV":
        uploaded_file = st.sidebar.file_uploader(
            "Upload Kaggle-style reinsurance data CSV",
            type=["csv"],
            help="Use a dataset with columns like policy_id, period, region, line_of_business, gross_written_premium, net_earned_premium, claims_paid, loss_ratio, combined_ratio.",
        )

    if uploaded_file:
        df = load_reinsurance_data(uploaded_file)
        if df.empty:
            st.sidebar.warning("Unable to parse uploaded CSV. Please check the file format.")
    else:
        df = generate_sample_portfolio(data_source)

    if "period" in df.columns and not df.empty:
        min_date = df["period"].min().date()
        max_date = df["period"].max().date()
    else:
        min_date = pd.to_datetime("2024-01-01").date()
        max_date = pd.to_datetime("2024-04-30").date()

    st.sidebar.markdown("---")
    date_range = st.sidebar.date_input(
        "Select timeline",
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date,
    )
    if not (isinstance(date_range,(list, tuple)) and len(date_range) == 2):
        st.warning("Please select both a start and end date for the timeline.")
        st.stop()

    start_date, end_date = date_range

    if "period" in df.columns and not df.empty:
        df = df[(df["period"].dt.date >= start_date) & (df["period"].dt.date <= end_date)]

    st.sidebar.markdown("---")
    line_options = sorted(df["line_of_business"].unique()) if "line_of_business" in df.columns else []
    region_options = sorted(df["region"].unique()) if "region" in df.columns else []
    risk_options = sorted(df["risk_category"].unique()) if "risk_category" in df.columns else []

    line_filter = st.sidebar.multiselect("Line of Business", options=line_options, default=line_options)
    region_filter = st.sidebar.multiselect("Region", options=region_options, default=region_options)
    risk_filter = st.sidebar.multiselect("Risk Category", options=risk_options, default=risk_options)

    if not line_filter:
        line_filter = line_options
    if not region_filter:
        region_filter = region_options
    if not risk_filter:
        risk_filter = risk_options

    if "line_of_business" in df.columns:
        df = df[df["line_of_business"].isin(line_filter)]
    if "region" in df.columns:
        df = df[df["region"].isin(region_filter)]
    if "risk_category" in df.columns:
        df = df[df["risk_category"].isin(risk_filter)]

    return df, data_source, f"{start_date.strftime('%d %b %Y')} - {end_date.strftime('%d %b %Y')}", (pd.Timestamp(start_date), pd.Timestamp(end_date))


def render_executive_overview(df: pd.DataFrame) -> None:
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
    st.markdown('<div class="section-card"><div class="section-header"><div class="section-title">Premium Trend (USD)</div></div></div>', unsafe_allow_html=True)
    trend_df = get_premium_trend(df)
    fig = px.line(trend_df, x="Month", y=["GWP", "NEP"], markers=True)
    st.plotly_chart(
    fig,
    width="stretch")

    st.markdown('<div class="section-card"><div class="section-header"><div class="section-title">Treaty Performance Summary</div></div></div>', unsafe_allow_html=True)
    st.dataframe(get_pricing_summary(df), use_container_width=True, height=300)

    st.markdown('<div class="section-card"><div class="section-header"><div class="section-title">Top Competitors - Market Share</div></div></div>', unsafe_allow_html=True)
    st.dataframe(get_competitor_share(df), use_container_width=True, height=250)

    st.markdown('<div class="section-card"><div class="section-header"><div class="section-title">Emerging Risks Monitor</div></div></div>', unsafe_allow_html=True)
    st.table(pd.DataFrame(get_risk_monitor()))


def render_market_intelligence(df: pd.DataFrame) -> None:
    st.markdown('<div class="section-card"><div class="section-header"><div class="section-title">Market Intelligence Highlights</div></div></div>', unsafe_allow_html=True)
    st.info('Global reinsurance capital increased by 8.7% in Q1 2024, driven by strong investment returns.')
    st.info('Natural catastrophe losses are above the 10-year average by 22%.')
    st.info('Property, Casualty and Agriculture lines are experiencing firming rate conditions.')
    st.info('Inflation remains elevated, affecting claim severity and expense ratios.')

    if "currency" in df.columns:
        st.divider()
        st.markdown('<div class="section-card"><div class="section-header"><div class="section-title">Currency Exposure and Ratings</div></div></div>', unsafe_allow_html=True)
        fx_df = (
            df.groupby(["currency", "currency_rating"])
            .agg(TotalGWP_USD=("gwp_usd", "sum"), CountPolicies=("policy_id", "nunique"))
            .reset_index()
        )
        fx_df["TotalGWP_USD"] = fx_df["TotalGWP_USD"].apply(lambda x: f"USD {x / 1_000_000:.2f}M")
        st.dataframe(fx_df.rename(columns={"currency": "Currency", "currency_rating": "Currency Rating"}), use_container_width=True, height=260)
    st.markdown('<div class="section-card"><div class="section-header"><div class="section-title">Claims Trend (USD)</div></div></div>', unsafe_allow_html=True)
    claims_df = get_claims_trend()
    fig_claims = px.bar(claims_df, x="Month", y=["Paid Claims (USD)", "Incurred Claims (USD)"], barmode="group")
    st.plotly_chart(fig_claims, use_container_width=True)

    st.divider()
    st.markdown('<div class="section-card"><div class="section-header"><div class="section-title">Geographic Exposure (GWP)</div></div></div>', unsafe_allow_html=True)
    geo_df = get_geographic_exposure()
    try:
        fig_geo = px.choropleth(geo_df, locations="country", locationmode="country names", color="gwp", color_continuous_scale="Blues")
        st.plotly_chart(fig_geo, use_container_width=True)
    except Exception:
        st.dataframe(geo_df)


def render_pricing_analytics(df: pd.DataFrame) -> None:
    st.markdown('<div class="section-card"><div class="section-header"><div class="section-title">Pricing Summary</div></div></div>', unsafe_allow_html=True)
    st.dataframe(get_pricing_summary(df), use_container_width=True, height=320)

    st.divider()
    st.markdown('<div class="section-card"><div class="section-header"><div class="section-title">Pricing Simulator (Quick)</div></div></div>', unsafe_allow_html=True)
    sim_col1, sim_col2 = st.columns([2, 1])
    with sim_col1:
        line = st.selectbox("Line of Business", ["Property", "Engineering", "Motor", "Marine", "Accident & Health"])
        expected_loss_ratio = st.slider("Expected Loss Ratio (%)", 40, 110, 62)
        expense_ratio = st.slider("Expense Ratio (%)", 0, 50, 25)
        profit_margin = st.slider("Profit Margin (%)", 0, 30, 12)
        if st.button("Calculate"):
            rate_delta = round((expected_loss_ratio / 100 + expense_ratio / 100 + profit_margin / 100) * 100 - 100, 1)
            st.metric("Indicated Rate Change", f"+{rate_delta}%")
    with sim_col2:
        st.metric("Technical Premium", "148.2M")
        st.metric("Expected Combined Ratio", "99.0%")
        st.markdown("<div style='margin-top:12px; color:#38bdf8; font-weight:700;'>Rate Adequacy: Adequate</div>", unsafe_allow_html=True)

    st.divider()
    st.markdown('<div class="section-card"><div class="section-header"><div class="section-title">Pricing Adequacy Analysis</div></div></div>', unsafe_allow_html=True)
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


def render_cedants_page(df: pd.DataFrame) -> None:
    st.markdown('<div class="section-card"><div class="section-header"><div class="section-title">Cedants Overview</div></div></div>', unsafe_allow_html=True)
    ced_df = get_cedants(df)
    currency_filter = st.multiselect(
        "Currency",
        options=sorted(df["currency"].unique()) if "currency" in df.columns else [],
        default=sorted(df["currency"].unique()) if "currency" in df.columns else [],
    )
    rating_filter = st.multiselect(
        "Filter Cedants by Rating",
        options=sorted(ced_df["Rating"].unique()),
        default=sorted(ced_df["Rating"].unique()),
    )
    region_filter = st.multiselect(
        "Filter Cedants by Region",
        options=sorted(ced_df["Region"].unique()),
        default=sorted(ced_df["Region"].unique()),
    )
    if currency_filter and "Currency" in ced_df.columns:
        ced_df = ced_df[ced_df["Currency"].isin(currency_filter)]
    if rating_filter:
        ced_df = ced_df[ced_df["Rating"].isin(rating_filter)]
    if region_filter:
        ced_df = ced_df[ced_df["Region"].isin(region_filter)]

    st.dataframe(ced_df, use_container_width=True, height=320)
    st.divider()

    gtw = ced_df.groupby("Rating")["Total GWP (KES)" if "Total GWP (KES)" in ced_df.columns else "Total GWP (USD)"].sum().reset_index()
    y_label = "Total GWP (KES)" if "Total GWP (KES)" in ced_df.columns else "Total GWP (USD)"
    fig = px.bar(gtw, x="Rating", y=y_label, title="Cedant GWP by Rating", text_auto=True)
    fig.update_traces(marker_color="#22c55e")
    st.plotly_chart(fig, use_container_width=True)

    risks = ced_df["Risk Categories"].str.split(", ", expand=True).stack().value_counts().reset_index()
    risks.columns = ["Risk Category", "Count"]
    st.markdown('<div class="section-card"><div class="section-header"><div class="section-title">Cedant Risk Categories</div></div></div>', unsafe_allow_html=True)
    st.dataframe(risks, use_container_width=True, height=220)


def render_reinsurers_page(df: pd.DataFrame) -> None:
    st.markdown('<div class="section-card"><div class="section-header"><div class="section-title">Reinsurers Directory</div></div></div>', unsafe_allow_html=True)
    reins_df = get_reinsurers(df)
    rating_filter = st.multiselect(
        "Filter Reinsurers by Rating",
        options=sorted(reins_df["Rating"].unique()),
        default=sorted(reins_df["Rating"].unique()),
    )
    product_options = sorted(
        {product.strip() for products in reins_df["Policies Offered"] for product in products.split(",")}
    )
    product_filter = st.multiselect(
        "Product Lines",
        options=product_options,
        default=product_options,
    )
    if rating_filter:
        reins_df = reins_df[reins_df["Rating"].isin(rating_filter)]
    if product_filter:
        reins_df = reins_df[reins_df["Policies Offered"].apply(lambda s: any(prod in s for prod in product_filter))]

    st.dataframe(reins_df, use_container_width=True, height=320)
    st.divider()

    fig = px.pie(reins_df, names="Rating", values="Market Presence Index", title="Reinsurer Market Presence by Rating", hole=0.4)
    st.plotly_chart(fig, use_container_width=True)
    st.markdown('<div class="section-card"><div class="section-header"><div class="section-title">Capacity & Policy Offerings</div></div></div>', unsafe_allow_html=True)
    st.dataframe(reins_df[["Reinsurer", "Policies Offered", "Estimated Capacity (USD B)", "Market Presence Index"]], use_container_width=True, height=250)


def render_portfolio_management(df: pd.DataFrame) -> None:
    st.markdown('<div class="section-card"><div class="section-header"><div class="section-title">Cedants Overview</div></div></div>', unsafe_allow_html=True)
    st.dataframe(get_cedants(df), use_container_width=True, height=260)

    st.divider()
    st.markdown('<div class="section-card"><div class="section-header"><div class="section-title">Reinsurers Directory</div></div></div>', unsafe_allow_html=True)
    reins = get_reinsurers(df)
    rating_filter = st.multiselect("Filter by Rating", options=sorted(reins["Rating"].unique()), default=sorted(reins["Rating"].unique()))
    if rating_filter:
        reins = reins[reins["Rating"].isin(rating_filter)]
    st.dataframe(reins, use_container_width=True, height=260)


def render_reports_insights(df: pd.DataFrame) -> None:
    st.markdown('<div class="section-card"><div class="section-header"><div class="section-title">Data Overview</div></div></div>', unsafe_allow_html=True)
    st.write(f"Dataset rows: {len(df)}")
    st.write(f"Lines of business: {', '.join(sorted(df['line_of_business'].unique())) if 'line_of_business' in df.columns else 'N/A'}")
    st.write(f"Regions: {', '.join(sorted(df['region'].unique())) if 'region' in df.columns else 'N/A'}")
    st.divider()
    st.markdown('<div class="section-card"><div class="section-header"><div class="section-title">AI Insights</div></div></div>', unsafe_allow_html=True)
    for insight in get_ai_insights():
        st.info(insight)


def render_system_page() -> None:
    import platform

    import pandas as pd
    import plotly 
    import plotly.express as px
    import streamlit as st


    st.markdown('<div class="section-card"><div class="section-header"><div class="section-title">System Information</div></div></div>', unsafe_allow_html=True)
    st.write(f"Python: {platform.python_version()}")
    st.write(f"Pandas: {pd.__version__}")
    st.write(f"Plotly: {plotly.__version__}")
    st.write(f"Streamlit: {st.__version__}")
    st.divider()
    st.write("Project structure:")
    st.write([p.name for p in Path('.').iterdir() if p.is_dir()])


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
                "Rating": ["A-", "A", "A+", "A"],
                "Primary Lines": ["Property, Motor", "Marine, Liability", "Motor, Accident", "Agriculture, Property"],
                "Risk Categories": ["Property, Motor, Cyber", "Marine, Liability, Weather", "Motor, Accident, Operational", "Agriculture, Weather, Market"],
                "Policies": [128, 64, 203, 77],
                "Total GWP (USD)": [1870000000, 980000000, 450000000, 160000000],
            }
        )

    ced = (
        df.groupby("client_name")
        .agg(Region=("region", "first"), Policies=("policy_id", "nunique"), GWP=("gwp_usd" if "gwp_usd" in df.columns else "gross_written_premium", "sum"))
        .reset_index()
        .rename(columns={"client_name": "Cedant", "GWP": "Total GWP (USD)", "Policies": "Policies"})
    )

    rating_map = {
        "Acentria Reinsurance": "A-",
        "Coastal Mutual": "A",
        "Metro Insurers Ltd": "A+",
        "AgriProtect": "A",
    }
    line_map = {
        "Acentria Reinsurance": "Property, Motor",
        "Coastal Mutual": "Marine, Liability",
        "Metro Insurers Ltd": "Motor, Accident",
        "AgriProtect": "Agriculture, Property",
    }
    ced["Rating"] = ced["Cedant"].map(rating_map).fillna("A")
    ced["Primary Lines"] = ced["Cedant"].map(line_map).fillna("Property")
    risk_categories = df.groupby("client_name")["risk_category"].apply(lambda s: ", ".join(sorted(s.unique()[:3]))).to_dict()
    ced["Risk Categories"] = ced["Cedant"].map(risk_categories).fillna("N/A")
    if "currency" in df.columns:
        currency_map = df.groupby("client_name")["currency"].first().to_dict()
        ced["Currency"] = ced["Cedant"].map(currency_map).fillna("USD")
        ced["Currency Rating"] = ced["Currency"].map(CURRENCY_RATINGS).fillna("BBB")
        return ced[["Cedant", "Region", "Currency", "Currency Rating", "Rating", "Primary Lines", "Risk Categories", "Policies", "Total GWP (USD)"]]
    return ced[["Cedant", "Region", "Rating", "Primary Lines", "Risk Categories", "Policies", "Total GWP (USD)"]]


def get_reinsurers(df: pd.DataFrame) -> pd.DataFrame:
    reinsurers = [
        ("Partner Re", "AA", "Property, Casualty", 1.8),
        ("Hannover Re", "AA", "Property, Life", 1.6),
        ("Munich Re", "AA+", "Property, Specialty", 1.9),
        ("Swiss Re", "AA", "Property, Casualty, Specialty", 1.7),
        ("SCOR", "A", "Property, Casualty", 1.4),
        ("Kenya Reinsurance Corporation", "A-", "Property, Agriculture, Casualty", 0.9),
        ("Africa Re", "A", "Property, Reinsurance, Specialty", 2.1),
        ("Old Mutual Re Africa", "A-", "Agriculture, Life, Casualty", 0.8),
        ("Hollard Re", "A", "Motor, Liability, Property", 0.7),
    ]
    df_reins = pd.DataFrame(reinsurers, columns=["Reinsurer", "Rating", "Policies Offered", "Estimated Capacity (USD B)"])
    if not df.empty:
        counts = df["line_of_business"].value_counts()
        df_reins["Market Presence Index"] = df_reins["Policies Offered"].apply(
            lambda s: sum([counts.get(x.strip(), 0) for x in s.split(",")])
        )
    else:
        df_reins["Market Presence Index"] = [128, 110, 96, 88, 70, 45]
    return df_reins


def generate_sample_portfolio(source: str) -> pd.DataFrame:
    rows = []
    clients = ["Acentria Reinsurance", "Coastal Mutual", "Metro Insurers Ltd", "AgriProtect"]
    reins = ["Partner Re", "Hannover Re", "Munich Re", "Swiss Re", "SCOR", "Aspire Re", "Kenya Reinsurance Corporation", "Africa Re", "Old Mutual Re Africa", "Hollard Re"]
    CURRENCY_EXCHANGE_RATES_USD = {
        "USD": 1.0,
        "KES": 0.0073,
        "EUR": 1.09,
    }
    currencies = list(CURRENCY_EXCHANGE_RATES_USD.keys())
    lines = [
        "Property",
        "Engineering",
        "Motor",
        "Marine",
        "Accident & Health",
        "Liability",
        "Energy",
        "Agriculture",
    ]
    regions = [
        "North America",
        "Europe",
        "Asia Pacific",
        "Latin America",
        "Africa",
        "Kenya",
        "Middle East & Africa",
        "Australia & Pacific",
        "Caribbean",
        "Nordics",
    ]
    risks = [
        "Nat Cat",
        "Cyber",
        "Operational",
        "Market",
        "Weather",
        "Political",
        "Liability",
        "Health",
        "Agriculture",
    ]
    import random

    periods = pd.to_datetime(["2024-01-01", "2024-02-01", "2024-03-01", "2024-04-01"])
    for i in range(1, 601):
        if source.startswith("Cedant"):
            client = random.choice(clients)
        elif source.startswith("Reinsurer"):
            client = random.choice(reins)
        else:
            client = random.choice(clients + reins)
        period = random.choice(periods)
        line = random.choice(lines)
        region = random.choice(regions)
        currency = random.choice(currencies)
        CURRENCY_EXCHANGE_RATES_USD = {
            "USD": 1.0,
            "KES": 0.0073,
            "EUR": 1.09,
        }
        exch_rate = CURRENCY_EXCHANGE_RATES_USD[currency]
        gwp = random.randint(15000, 8_000_000)
        nep = int(gwp * random.uniform(0.55, 0.92))
        claims_paid = int(gwp * random.uniform(0.08, 0.64))
        loss_ratio = claims_paid / nep if nep > 0 else 0
        combined_ratio = min(loss_ratio + random.uniform(0.05, 0.48), 1.35)
        policy_id = f"P-{i:05d}"
        premium_rate = round(random.uniform(0.35, 1.35), 3)
        exposure = int(gwp * random.uniform(0.9, 1.5))
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
                "premium_rate": premium_rate,
                "exposure": exposure,
                "currency": currency,
                "gwp_usd": gwp * exch_rate,
                "nep_usd": nep * exch_rate,
                "claims_paid_usd": claims_paid * exch_rate,
                "currency_rating": CURRENCY_RATINGS[currency],
            }
        )
    return pd.DataFrame(rows)

st.sidebar.markdown("---")

st.sidebar.success(
    f"Logged in as {st.session_state.user}"
)

if st.sidebar.button("Logout"):
    st.session_state.logged_in = False
    st.session_state.user = ""
    st.session_state.role = ""
    st.rerun()
    
def build_dashboard() -> None:
    st.set_page_config(
        page_title="Reinsurance intelligence & pricing dashboard",
        layout="wide")
    st.markdown(DARK_THEME_CSS, unsafe_allow_html=True)
    st.markdown(LOGO_HTML, unsafe_allow_html=True)

    st.sidebar.markdown(
        "<div style='padding: 14px 18px; border-radius: 18px; background: linear-gradient(135deg, #0f172a, #111827); border:1px solid rgba(148,163,184,0.12); margin-bottom: 18px;'><strong style='color:#ffffff;'>Acentria Group</strong><br><span style='color:#94a3b8; font-size:0.92rem;'>Reinsurance intelligence suite</span></div>",
        unsafe_allow_html=True,
    )
st.sidebar.markdown("---")

st.sidebar.success(f"👤 {st.session_state.user}")
st.sidebar.caption(f"Role: {st.session_state.role}")

if st.sidebar.button("🚪 Logout", use_container_width=True):
    st.sidebar.markdown("---")

    st.session_state.logged_in = False
    st.session_state.user = ""
    st.session_state.role = ""
    st.session_state.page = "login"
    st.rerun()

page = st.sidebar.radio(
    "Navigation",
    [
        "Executive Overview",
        "Market Intelligence",
        "Pricing Analytics",
        "Cedants",
        "Reinsurers",
        "Reports & Insights",
        "📁 Upload Data",
        "System",
    ],
    label_visibility="collapsed",
)

if "dataset" in st.session_state:

    df = st.session_state.dataset
    data_source = "Uploaded Dataset"
    range_label = "Current"

else:

    df, data_source, range_label, _ = filter_portfolio_data(
        load_reinsurance_data()
    )

report_csv = df.to_csv(index=False)
header_col1, header_col2 = st.columns([4, 1])
with header_col1:
        st.markdown('<div class="top-banner">Market Intelligence · Pricing Analytics · Portfolio Performance</div>', unsafe_allow_html=True)
        st.write(f"Data source: {data_source} | Base currency: USD")
with header_col2:
        st.markdown(f'<div class="header-chip">{range_label}</div>', unsafe_allow_html=True)
        st.download_button("Export Report", report_csv, file_name="acentria_dashboard_data.csv", mime="text/csv")

if page == "Executive Overview":
        render_executive_overview(df)
elif page == "Market Intelligence":
        render_market_intelligence(df)
elif page == "Pricing Analytics":
        render_pricing_analytics(df)
elif page == "Cedants":
        render_cedants_page(df)
elif page == "Reinsurers":
        render_reinsurers_page(df)
elif page == "Reports & Insights":
        render_reports_insights(df)
elif page == "Portfolio Management":
        render_portfolio_management(df)
elif page == "system" or page == "System":
        render_system_page()
elif page == "📁 Upload Data":

    st.header("Dataset Upload")

    st.info(
        "Upload an Excel or CSV dataset for analysis."
    )

    uploaded_file = st.file_uploader(
        "Choose Dataset",
        type=["csv", "xlsx", "xls"],
    )

    if uploaded_file:
 
        if uploaded_file.name.endswith(".csv"):

            df = pd.read_csv(uploaded_file)

        else:

            df = pd.read_excel(uploaded_file)

        st.session_state.dataset = df
        st.session_state.data_source = "Uploaded Dataset"

        st.success("Dataset uploaded successfully.")
        if st.button("Use This Dataset"):

             st.rerun()

        st.dataframe(
            df.head(),
            width="stretch",
        )

        st.metric("Rows", len(df))

        st.metric("Columns", len(df.columns))

if __name__ == "__main__":
    build_dashboard()

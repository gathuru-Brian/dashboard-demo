"""
Theme and styling system for RMIP-DSS / Acentria
Dark premium enterprise aesthetic matching the original design.
"""

# ============================================================================
# COLOR PALETTE – DARK ENTERPRISE
# ============================================================================

# Backgrounds
COLOR_BG_PRIMARY   = "#2C2F35"      # Deep navy (main background)
COLOR_BG_SECONDARY = "#111827"      # Slightly lighter navy
COLOR_BG_SURFACE   = "#1E293B"      # Card / surface background
COLOR_BG_HOVER     = "#334155"      # Hover state

# Text
COLOR_TEXT_PRIMARY   = "#F8FAFC"    # Near white (headings)
COLOR_TEXT_SECONDARY = "#94A3B8"    # Soft gray (body text)
COLOR_TEXT_MUTED     = "#64748B"    # Muted gray (labels)
COLOR_TEXT_INVERSE   = "#0F172A"    # Dark text on bright buttons

# Accent – Cyan / Sky Blue (matches the image)
COLOR_ACCENT_PRIMARY   = "#06B6D4"  # Main cyan
COLOR_ACCENT_SECONDARY = "#0EA5E9"  # Brighter sky blue
COLOR_ACCENT_TERTIARY  = "#22D3EE"  # Light cyan

# State colors
COLOR_SUCCESS = "#22C55E"
COLOR_WARNING = "#F97316"
COLOR_ERROR   = "#EF4444"
COLOR_INFO    = "#3B82F6"

# Borders
COLOR_BORDER_SUBTLE = "rgba(51, 65, 85, 0.6)"
COLOR_BORDER_STRONG = "rgba(6, 182, 212, 0.4)"
COLOR_DIVIDER       = "rgba(148, 163, 184, 0.15)"

# ============================================================================
# SPACING & RADIUS
# ============================================================================

SPACING_XS  = "4px"
SPACING_SM  = "8px"
SPACING_MD  = "16px"
SPACING_LG  = "24px"
SPACING_XL  = "32px"
SPACING_2XL = "48px"

RADIUS_SM = "6px"
RADIUS_MD = "10px"
RADIUS_LG = "14px"

# ============================================================================
# TYPOGRAPHY
# ============================================================================

FONT_FAMILY_BASE = "'Inter', 'Segoe UI', system-ui, sans-serif"
FONT_WEIGHT_NORMAL   = "400"
FONT_WEIGHT_MEDIUM   = "500"
FONT_WEIGHT_SEMIBOLD = "600"
FONT_WEIGHT_BOLD     = "700"

# ============================================================================
# SHADOWS
# ============================================================================

SHADOW_SM = "0 4px 12px rgba(0, 0, 0, 0.25)"
SHADOW_MD = "0 8px 24px rgba(0, 0, 0, 0.35)"
SHADOW_LG = "0 16px 40px rgba(0, 0, 0, 0.45)"

GLOW_ACCENT        = "0 0 20px rgba(6, 182, 212, 0.35)"
GLOW_ACCENT_SUBTLE = "0 0 12px rgba(6, 182, 212, 0.2)"

# ============================================================================
# CUSTOM CSS
# ============================================================================

def get_custom_css() -> str:
    return f"""
    <style>
        /* ===== PAGE BACKGROUND ===== */
        [data-testid="stAppViewContainer"], .stApp {{
            background: linear-gradient(160deg, {COLOR_BG_PRIMARY} 0%, #0F172A 50%, #1E293B 100%);
        }}

        /* ===== SIDEBAR ===== */
        [data-testid="stSidebar"] {{
            background: {COLOR_BG_SECONDARY};
            border-right: 1px solid {COLOR_BORDER_SUBTLE};
        }}

        /* ===== TYPOGRAPHY ===== */
        h1, h2, h3, h4, h5, h6 {{
            color: {COLOR_TEXT_PRIMARY} !important;
            font-weight: {FONT_WEIGHT_BOLD};
            letter-spacing: -0.5px;
        }}

        h1 {{
            font-size: 2.8rem;
            line-height: 1.15;
        }}

        p, span, label, .stCaption {{
            color: {COLOR_TEXT_SECONDARY};
            line-height: 1.65;
        }}

        .stCaption {{
            color: {COLOR_TEXT_MUTED};
        }}

        /* ===== CARDS & CONTAINERS ===== */
        .stContainer, [data-testid="stExpander"] {{
            background: rgba(30, 41, 59, 0.7);
            border: 1px solid {COLOR_BORDER_SUBTLE};
            border-radius: {RADIUS_MD};
            box-shadow: {SHADOW_SM};
            backdrop-filter: blur(12px);
            transition: all 0.25s ease;
        }}

        .stContainer:hover {{
            border-color: {COLOR_BORDER_STRONG};
            box-shadow: {SHADOW_MD};
        }}

        /* ===== BUTTONS ===== */
        .stButton > button {{
            background: linear-gradient(135deg, {COLOR_ACCENT_PRIMARY}, {COLOR_ACCENT_SECONDARY});
            color: {COLOR_TEXT_INVERSE} !important;
            border: none;
            border-radius: {RADIUS_MD};
            padding: 0.7rem 1.6rem;
            font-weight: {FONT_WEIGHT_SEMIBOLD};
            transition: all 0.2s ease;
            box-shadow: 0 4px 14px rgba(6, 182, 212, 0.3);
        }}

        .stButton > button:hover {{
            box-shadow: {GLOW_ACCENT};
            transform: translateY(-2px);
        }}

        /* ===== INPUTS ===== */
        input[type="text"],
        input[type="email"],
        input[type="password"],
        input[type="number"],
        textarea,
        select {{
            background: {COLOR_BG_PRIMARY} !important;
            color: {COLOR_TEXT_PRIMARY} !important;
            border: 1px solid {COLOR_BORDER_SUBTLE} !important;
            border-radius: {RADIUS_SM} !important;
            padding: 0.7rem 0.9rem !important;
        }}

        input:focus, textarea:focus, select:focus {{
            border-color: {COLOR_ACCENT_PRIMARY} !important;
            box-shadow: 0 0 0 3px rgba(6, 182, 212, 0.2) !important;
            background: {COLOR_BG_SECONDARY} !important;
        }}

        input::placeholder {{
            color: {COLOR_TEXT_MUTED} !important;
        }}

        /* ===== TABS ===== */
        [data-testid="stTabs"] [role="tab"] {{
            color: {COLOR_TEXT_SECONDARY};
            font-weight: {FONT_WEIGHT_MEDIUM};
        }}

        [data-testid="stTabs"] [role="tab"][aria-selected="true"] {{
            color: {COLOR_ACCENT_PRIMARY} !important;
            border-bottom: 2px solid {COLOR_ACCENT_PRIMARY};
        }}

        /* ===== METRIC CARDS ===== */
        [data-testid="metric-container"] {{
            background: rgba(30, 41, 59, 0.75);
            border: 1px solid {COLOR_BORDER_SUBTLE};
            border-radius: {RADIUS_MD};
            box-shadow: {SHADOW_SM};
        }}

        /* ===== DATAFRAME ===== */
        [data-testid="stDataFrame"] {{
            background: {COLOR_BG_SURFACE};
            border-radius: {RADIUS_MD};
            border: 1px solid {COLOR_BORDER_SUBTLE};
        }}

        /* ===== UTILITIES ===== */
        .accent-text {{
            color: {COLOR_ACCENT_PRIMARY};
            font-weight: {FONT_WEIGHT_SEMIBOLD};
        }}

        .muted-text {{
            color: {COLOR_TEXT_MUTED};
        }}

        /* ===== DASHBOARD HELPERS ===== */
        .dashboard-header {{
            background: rgba(30, 41, 59, 0.7);
            border: 1px solid {COLOR_BORDER_SUBTLE};
            border-radius: {RADIUS_MD};
            padding: {SPACING_LG};
            margin-bottom: {SPACING_LG};
        }}

        .dashboard-section {{
            background: rgba(30, 41, 59, 0.65);
            border: 1px solid {COLOR_BORDER_SUBTLE};
            border-radius: {RADIUS_MD};
            padding: {SPACING_MD};
            margin-bottom: {SPACING_MD};
            transition: all 0.25s ease;
        }}

        .dashboard-section:hover {{
            border-color: {COLOR_BORDER_STRONG};
            box-shadow: {SHADOW_MD};
        }}
    </style>
    """

def inject_css(streamlit):
    streamlit.markdown(get_custom_css(), unsafe_allow_html=True)
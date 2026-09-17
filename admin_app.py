"""
RMIP-DSS Admin Console — Standalone Application
-------------------------------------------------
A separate app from the main analytics dashboard (app.py). Run this on its
own port so it can be firewalled/restricted independently of the main
customer-facing app:

    streamlit run admin_app.py --server.port 8502

It shares the same auth database (database/users.db) and the same
.streamlit/secrets.toml as the main app, so logins, roles, and the
superuser protection all stay consistent across both apps. Access here is
restricted to roles holding the "users" or "system" permission -- anyone
else who logs in correctly is still rejected from this specific app.
"""

from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from auth.authentication import initialize_admin, login_user, notify_admin_login
from auth.permissions import has_permission
from dashboard.admin import admin_page
from dashboard.system_health import show_system_health

st.set_page_config(
    page_title="RMIP-DSS Admin Console",
    page_icon=":material/admin_panel_settings:",
    layout="wide",
    initial_sidebar_state="expanded",
)


def init_state() -> None:
    defaults = {"logged_in": False, "user": "", "email": "", "role": "", "department": ""}
    for key, value in defaults.items():
        st.session_state.setdefault(key, value)


def is_admin_capable(role: str) -> bool:
    return has_permission(role, "users") or has_permission(role, "system")


def show_login() -> None:
    st.markdown("""
    <style>
    [data-testid="stHeader"], [data-testid="stToolbar"], #MainMenu, footer { display: none; }
    .stApp { background: #030b18; color: #e9f2fb; }
    .block-container { max-width: 1440px; padding: 2.2rem 2.5rem 1.5rem; }
    .login-art, .login-card { min-height: 720px; }
    .login-art {
        position: relative; overflow: hidden; padding: 1.15rem 1.25rem;
        border-right: 1px solid rgba(52, 157, 205, .22);
        background:
          radial-gradient(ellipse at 72% 50%, rgba(0, 129, 211, .20), transparent 29%),
          radial-gradient(ellipse at 40% 72%, rgba(0, 73, 154, .20), transparent 38%),
          linear-gradient(125deg, #030916 16%, #061426 62%, #020914);
    }
    .login-art:after {
        content: ""; position: absolute; inset: 27% -6% 8% -28%; opacity: .7;
        background-image:
          radial-gradient(circle, #20c7ff 0 2px, transparent 2.8px),
          linear-gradient(22deg, transparent 49.4%, rgba(32, 193, 255, .44) 50%, transparent 50.6%),
          linear-gradient(-26deg, transparent 49.5%, rgba(25, 141, 235, .34) 50%, transparent 50.5%);
        background-size: 48px 48px, 84px 84px, 104px 104px;
        transform: perspective(500px) rotateX(35deg) rotateZ(-14deg);
        filter: drop-shadow(0 0 6px rgba(38, 205, 255, .8));
    }
    .eyebrow { position: relative; z-index: 1; color: #b9c6d7; letter-spacing: .25em; font-size: .82rem; }
    .accent-line { position: relative; z-index: 1; height: 3px; width: 68px; margin: 1.1rem 0 3rem; background: #26cbef; }
    .intel { position: relative; z-index: 1; color: #bcc8d6; letter-spacing: .13em; font-size: .82rem; margin-bottom: .6rem; }
    .risk-score { position: relative; z-index: 1; font-size: 2.8rem; font-weight: 700; color: #26c8f1; line-height: 1; }
    .risk-score span { font-size: .78rem; color: #ee7c75; letter-spacing: .08em; vertical-align: middle; }
    .intel-spacer { height: 3.6rem; }
    .mini-line { position: relative; z-index: 1; width: 165px; height: 52px; margin-top: .65rem; border-bottom: 1px solid transparent;
        background: linear-gradient(145deg, transparent 0 19%, #54d4f4 20% 21%, transparent 22% 39%, #54d4f4 40% 41%, transparent 42% 57%, #54d4f4 58% 59%, transparent 60% 100%); opacity: .85; }
    .anomaly { position: absolute; z-index: 1; bottom: 3.6rem; left: 1.25rem; }
    .ring { width: 104px; height: 104px; border: 6px solid #2acaf0; border-left-color: #153e62; border-radius: 50%; display: grid; place-content: center; margin-top: .8rem; color: #27c8ee; font-size: 2.35rem; line-height: .8; }
    .ring small { color: #d6e3ee; font-size: .64rem; letter-spacing: .11em; text-align: center; margin-top: .5rem; }
    .login-card { display: flex; align-items: center; justify-content: center; padding: 1rem 2.5rem; background: linear-gradient(110deg, #071426, #03101f); }
    .card-copy { width: 100%; max-width: 520px; padding: 2.2rem 2.8rem 1.5rem; border: 1px solid rgba(104, 159, 197, .34); border-radius: 17px; background: rgba(7, 22, 39, .78); box-shadow: 0 12px 42px rgba(0,0,0,.2); }
    .brand-shield { color: #23c8f1; font-size: 3.9rem; text-align: center; line-height: 1; }
    .brand { text-align: center; font-size: 2.75rem; font-weight: 750; letter-spacing: -.05em; margin: .25rem 0 .3rem; }
    .brand span { color: #16c7f1; }
    .console-label { text-align: center; color: #f2f6fb; letter-spacing: .35em; font-size: .88rem; margin-bottom: .4rem; }
    .tagline { text-align: center; color: #aab7c8; margin-bottom: 1.25rem; }
    .restriction { margin: .6rem 0 1rem; padding: .75rem .9rem; text-align: center; border: 1px solid #1faed8; border-radius: 7px; box-shadow: inset 0 0 14px rgba(21,199,241,.12); color: #9eeeff; }
    .restriction strong { display:block; font-size: 1.05rem; margin-bottom: .25rem; }
    .restriction small { color: #b9d4df; }
    .access-title { text-align: center; font-size: 1.25rem; font-weight: 650; margin-top: 1rem; }
    .access-copy { text-align: center; color: #aeb9c9; font-size: .9rem; margin: .35rem 0 1rem; }
    .card-copy [data-testid="stForm"] { border: 0; padding: 0; }
    .card-copy [data-testid="stTextInput"] label { color: #e9eff8; font-weight: 600; }
    .card-copy [data-testid="stTextInput"] input { background: #071427; border: 1px solid #38516b; border-radius: 7px; color: #f4f8fc; }
    .card-copy [data-testid="stTextInput"] input:focus { border-color: #25c9ef; box-shadow: 0 0 0 1px #25c9ef; }
    .card-copy [data-testid="stFormSubmitButton"] button { width: 100%; margin-top: .3rem; border: 0; border-radius: 6px; background: linear-gradient(90deg, #16bde0, #087b9d); color: white; letter-spacing: .16em; font-size: 1rem; font-weight: 700; min-height: 3.1rem; }
    .secure-note { text-align: center; color: #a6b4c5; font-size: .78rem; margin: 1rem 0 0; }
    @media (max-width: 850px) { .login-art { display:none; } .login-card { min-height: calc(100vh - 4rem); padding: 1rem; } .card-copy { padding: 2rem 1.5rem; } .block-container { padding: 1rem; } }
    </style>
    """, unsafe_allow_html=True)

    left, right = st.columns([1.05, .95], gap="small", vertical_alignment="center")
    with left:
        st.markdown("""
        <div class="login-art">
          <div class="eyebrow">RISK INTELLIGENCE • ANALYTICS • INSIGHTS</div><div class="accent-line"></div>
          <div class="intel">RISK EXPOSURE</div><div class="risk-score">72.4 <span>▲ HIGH</span></div>
          <div class="intel-spacer"></div><div class="intel">THREAT ACTIVITY</div><div class="mini-line"></div>
          <div class="anomaly"><div class="intel">ANOMALY DETECTION</div><div class="ring">18<small>ACTIVE</small></div></div>
        </div>
        """, unsafe_allow_html=True)
    with right:
        st.markdown("<div class='login-card'><div class='card-copy'><div class='brand-shield'>♢</div><div class='brand'>RMIP-<span>DSS</span></div><div class='console-label'>ADMIN CONSOLE</div><div class='tagline'>Secure • Monitor • Decide</div><div class='restriction'><strong>Restricted Access</strong><small>This console is limited to authorized administrators and IT support roles only.</small></div><div class='access-title'>♙ &nbsp; Restricted Access</div><div class='access-copy'>This console is restricted to authorized administrators only.<br>Unauthorized access is prohibited.</div>", unsafe_allow_html=True)
        with st.form("admin_login_form"):
            email = st.text_input("Username", placeholder="Enter admin username")
            password = st.text_input("Password", type="password", placeholder="Enter password")
            submitted = st.form_submit_button("SIGN IN  →", type="primary", width="stretch")
        st.markdown("<div class='secure-note'>♢ &nbsp; Secure login powered by RMIP-DSS Platform<br>All actions are logged and monitored.</div></div></div>", unsafe_allow_html=True)
        if submitted:
            user = login_user(email.strip().lower(), password)
            if not user:
                st.error("Please verify your login credentials, or this account is temporarily locked due to repeated failed attempts.")
            elif not is_admin_capable(user["role"]):
                st.error("This account does not have administrative access. Contact your admin to reset the password.")
            else:
                notify_admin_login(user)
                st.session_state.update({"logged_in": True, "user": user["fullname"], "email": user["email"], "role": user["role"], "department": user["department"]})
                st.rerun()


def render_topbar() -> None:
    cols = st.columns([5, 1])
    with cols[0]:
        st.caption(f"Signed in as **{st.session_state.user}** • {st.session_state.role}")
    with cols[1]:
        if st.button("Sign out", icon=":material/logout:", use_container_width=True):
            for key in ("logged_in", "user", "email", "role", "department"):
                st.session_state[key] = "" if key != "logged_in" else False
            st.rerun()


def main() -> None:
    init_state()
    initialize_admin()

    if not st.session_state.logged_in:
        show_login()
        return

    render_topbar()
    tab_admin, tab_health = st.tabs([":material/security: Admin console", ":material/monitor_heart: System health"])
    with tab_admin:
        admin_page()
    with tab_health:
        show_system_health()


if __name__ == "__main__":
    main()

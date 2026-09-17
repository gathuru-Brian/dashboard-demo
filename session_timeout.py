"""
Session timeout enforcement
RMIP-DSS
---------------------------------
Auto-logs users out after a period of inactivity. Import and call
enforce_session_timeout() once near the top of main(), after init_state()
and before rendering any authenticated content.
"""

from datetime import datetime, timedelta

import streamlit as st

IDLE_TIMEOUT_MINUTES = 30


def enforce_session_timeout() -> None:
    """
    If the user is logged in but has been idle longer than
    IDLE_TIMEOUT_MINUTES, logs them out and shows a message. Otherwise,
    refreshes their last-activity timestamp.
    """
    if not st.session_state.get("logged_in"):
        return

    now = datetime.now()
    last_active = st.session_state.get("last_active")

    if last_active is not None:
        idle_for = now - last_active
        if idle_for > timedelta(minutes=IDLE_TIMEOUT_MINUTES):
            for key in ("logged_in", "user", "email", "role", "department"):
                st.session_state[key] = "" if key != "logged_in" else False
            st.session_state.page = "welcome"
            st.warning(
                f"You were signed out after {IDLE_TIMEOUT_MINUTES} minutes of inactivity. "
                "Please sign in again."
            )
            st.stop()

    st.session_state.last_active = now
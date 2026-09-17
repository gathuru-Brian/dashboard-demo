import streamlit as st


def initialize_session():

    defaults = {

        "logged_in": False,

        "user": None,

        "fullname": None,

        "role": None,

        "department": None,

        "page": "login"
    }

    for key, value in defaults.items():

        if key not in st.session_state:

            st.session_state[key] = value
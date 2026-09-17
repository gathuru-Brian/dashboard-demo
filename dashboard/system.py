import platform

import pandas as pd

import streamlit as st


def system_page():

    st.title("System")

    st.write(

        "Python",

        platform.python_version()

    )

    st.write(

        "Pandas",

        pd.__version__

    )

    st.write(

        "Current User",

        st.session_state.user

    )

    st.write(

        "Role",

        st.session_state.role

    )
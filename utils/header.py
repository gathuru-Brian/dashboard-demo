import streamlit as st


def dashboard_header():

    left,right=st.columns([6,1])

    with left:

        st.title(

            "Reinsurance Market Intelligence Platform"

        )

        st.caption(

            "Acentria Group"

        )

    with right:

        st.metric(

            "Status",

            "LIVE"

        )
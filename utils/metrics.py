import streamlit as st


def metric_card(title, value, delta, color):

    st.markdown(

        f"""

        <div style="

        background:#111827;

        padding:20px;

        border-radius:18px;

        border-left:6px solid {color};

        box-shadow:0 5px 20px rgba(0,0,0,.25);

        ">

        <h5>{title}</h5>

        <h2>{value}</h2>

        <p>{delta}</p>

        </div>

        """,

        unsafe_allow_html=True

    )
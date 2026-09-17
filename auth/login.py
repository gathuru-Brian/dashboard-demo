import streamlit as st
from auth.authentication import login_user


def login_page():

    st.set_page_config(page_title="RMIP-DSS Login", layout="wide")

    st.markdown("""
    <style>
    .main{
        background:#07111f;
    }

    .login-box{
        background:#0f172a;
        padding:40px;
        border-radius:18px;
        border:1px solid #1e293b;
        box-shadow:0px 0px 25px rgba(0,0,0,.35);
    }

    .title{
        color:white;
        font-size:34px;
        font-weight:bold;
        margin-bottom:0px;
    }

    .subtitle{
        color:#94a3b8;
        margin-bottom:30px;
    }

    .stButton>button{
        width:100%;
        height:50px;
        background:#2563eb;
        color:white;
        border-radius:10px;
        border:none;
        font-weight:bold;
    }

    .stButton>button:hover{
        background:#1d4ed8;
    }
    </style>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1,2,1])

    with col2:

        st.markdown(
            """
            <div class="login-box">

            <h1 class="title">
            ACENTRIA GROUP
            </h1>

            <p class="subtitle">
            Reinsurance Market Intelligence &
            Pricing Dashboard
            </p>

            """,
            unsafe_allow_html=True
        )

        email = st.text_input(
            "Email Address",
            placeholder="Enter your company email"
        )

        password = st.text_input(
            "Password",
            type="password",
            placeholder="Enter password"
        )

        login = st.button("Login")

        st.markdown("</div>", unsafe_allow_html=True)

        if login:

            if email == "" or password == "":

                st.error("Please fill in all fields.")

                return

            user = login_user(email, password)

            if user is not None:

                st.session_state.logged_in = True

                st.session_state.user = user["fullname"]

                st.session_state.email = user["email"]

                st.session_state.role = user["role"]

                st.session_state.department = user["department"]

                st.session_state.page = "landing"

                st.success("Login Successful")

                st.rerun()

            else:

                st.error("Invalid email or password.")

        st.markdown("---")

        c1, c2 = st.columns(2)

        with c1:

            if st.button("Create Account"):

                st.session_state.page = "register"

                st.rerun()

        with c2:

            st.info("RMIP-DSS v2.0")
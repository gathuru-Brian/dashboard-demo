"""
RMIP-DSS Enterprise Registration
Author: Acentria Group
"""

import streamlit as st

from auth.authentication import create_user, notify_user_registration
from auth.roles import get_roles
from auth.departments import get_departments


def register_page():

    st.markdown(
        """
        <style>

        .title{
            font-size:34px;
            font-weight:bold;
            text-align:center;
            color:#003366;
        }

        .subtitle{
            text-align:center;
            color:gray;
            margin-bottom:25px;
        }

        </style>
        """,
        unsafe_allow_html=True
    )

    st.markdown(
        """
        <div class='title'>
            Create RMIP-DSS Account
        </div>

        <div class='subtitle'>
            Reinsurance Market Intelligence Platform
        </div>
        """,
        unsafe_allow_html=True
    )

    with st.form("register_form"):

        fullname = st.text_input(
            "Full Name"
        )

        email = st.text_input(
            "Email Address"
        )

        department = st.selectbox(
            "Department",
            get_departments()
        )

        role = st.selectbox(
            "Role",
            get_roles()
        )

        password = st.text_input(
            "Password",
            type="password"
        )

        confirm_password = st.text_input(
            "Confirm Password",
            type="password"
        )

        register = st.form_submit_button(
            "Create Account"
        )

    if register:
        if fullname.strip() == "":
            st.error("Full Name is required.")
            return

        if email.strip() == "":
            st.error("Email Address is required.")
            return

        if password == "":
            st.error("Password is required.")
            return

        if len(password) < 8:
            st.error("Password must contain at least 8 characters.")
            return

        if password != confirm_password:
            st.error("Passwords do not match.")
            return

        success = create_user(
            fullname=fullname,
            email=email.strip().lower(),
            password=password,
            role=role,
            department=department
        )

        if success:
            notify_user_registration(email.strip().lower(), fullname.strip())
            st.success("Account created successfully!")
            st.info("You can now login.")
            st.session_state.page = "login"
            st.rerun()
        else:
            st.error("An account with this email already exists.")

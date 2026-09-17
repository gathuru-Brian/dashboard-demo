import streamlit as st


def profile_page():

    st.title("👤 User Profile")

    st.write("### Personal Information")

    st.text_input("Full Name", st.session_state.user, disabled=True)

    st.text_input("Email", st.session_state.email, disabled=True)

    st.text_input("Department", st.session_state.department, disabled=True)

    st.text_input("Role", st.session_state.role, disabled=True)

    st.success("Account Active")

    if st.button("← Back"):

        st.session_state.page="landing"

        st.rerun()
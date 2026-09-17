import streamlit as st


def sidebar(role):

    st.sidebar.image(
        "assets/logo.png",
        width=120
    )

    st.sidebar.title("RMIP-DSS")

    st.sidebar.caption("Acentria Group")

    st.sidebar.divider()

    pages = [
        "📊 Executive Overview",
        "🌍 Market Intelligence",
        "💰 Pricing Analytics",
        "🏢 Cedants",
        "🤝 Reinsurers",
        "📈 Reports",
        "📁 Upload Data",
        "⚙ System"
    ]

    if role == "Administrator":

        pages.append("👑 Admin Panel")

    selected = st.sidebar.radio(

        "Navigation",

        pages

    )

    st.sidebar.divider()

    st.sidebar.success(

        f"Logged in as\n\n**{role}**"

    )

    return selected
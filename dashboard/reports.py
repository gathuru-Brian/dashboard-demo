import streamlit as st


def reports_page(df):

    st.title("📄 Reports & Insights")

    st.download_button(

        "Download CSV",

        df.to_csv(index=False),

        "RMIP_Report.csv",

        "text/csv"

    )

    st.write(df.describe())
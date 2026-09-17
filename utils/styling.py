import streamlit as st

def load_css():

    st.markdown("""

<style>

html, body, .stApp{

    background:#071320;
    color:white;

}

section[data-testid="stSidebar"]{

    background:#08111c;
}

section[data-testid="stSidebar"] *{

    color:white;

}

.block-container{

    padding-top:1rem;
    padding-bottom:1rem;
    padding-left:2rem;
    padding-right:2rem;

}

div[data-testid="metric-container"]{

    background:#102033;

    border-radius:15px;

    padding:18px;

    border:1px solid #23384f;

}

h1,h2,h3{

    color:white;

}

</style>

""", unsafe_allow_html=True)
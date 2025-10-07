import streamlit as st

def setup_page(max_width: int = 780):
    """
    Sæt sideopsætning og CSS for hele appen
    """
    st.set_page_config(
        page_title="iRacing – Stint Control",
        page_icon="🏁",   # rent unicode-emoji
        layout="centered"
    )
    st.markdown(
        f"""
        <style>
          .block-container {{
            max-width: {max_width}px;
            padding-top: 1.2rem;
            margin: auto;
          }}
          .stButton>button, .stDownloadButton>button {{
            width: 100%;
          }}
        </style>
        """,
        unsafe_allow_html=True
    )

import streamlit as st

# UI setup (ingen sideeffekter ved import)
from ui.styles import setup_page
from ui.landing import landing
from ui.admin import admin_panel
from ui.user import user_team_pick, user_team_view 
from ui.spectate import spectate_view  

# Core (ingen Streamlit-kald her)
from core.db import ensure_schema
from core.auth import ADMIN_PASS


def admin_login():
    st.header("Admin login")
    pw = st.text_input("Password", type="password", key="admin_pw")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Login", key="admin_login_btn"):
            if pw == ADMIN_PASS:
                st.session_state.view = "ADMIN_PANEL"
                st.rerun()
            else:
                st.error("Forkert password")
    with col2:
        if st.button("◀ Tilbage", key="admin_back"):
            st.session_state.view = "LANDING"
            st.rerun()


def main():
    # 1) UI ramme skal sættes først
    setup_page()

    # 2) Sørg for DB-schema (ingen UI-sideeffekter)
    ensure_schema()

    # 3) Routing state
    st.session_state.setdefault("view", "LANDING")

    # (valgfrit) lille debug i sidebar
    st.sidebar.caption("View-state")
    st.sidebar.code(st.session_state.get("view"))

    from ui.styles import setup_page
from ui.landing import landing
from ui.admin import admin_panel
from ui.user import user_team_pick, user_team_view  # kun disse to

from core.db import ensure_schema
from core.auth import ADMIN_PASS
import streamlit as st

def admin_login():
    st.header("Admin login")
    pw = st.text_input("Password", type="password")
    if st.button("Login"):
        if pw == ADMIN_PASS:
            st.session_state.view = "ADMIN_PANEL"; st.rerun()
        else:
            st.error("Forkert password")
    if st.button("◀ Tilbage"):
        st.session_state.view = "LANDING"; st.rerun()

def main():
    setup_page()
    ensure_schema()

    # init view state KUN én gang
    st.session_state.setdefault("view", "LANDING")

    # DEBUG i sidebar: se state skifte når du klikker
    st.sidebar.caption("View-state")
    st.sidebar.code(st.session_state.get("view"))

    view = st.session_state.view
    if view == "LANDING":
        landing()
    elif view == "ADMIN_LOGIN":
        admin_login()
    elif view == "ADMIN_PANEL":
        admin_panel()
    elif view == "USER_TEAM_PICK":
        user_team_pick()
    elif view == "USER_TEAM_VIEW":
        user_team_view()
    elif view == "SPECTATE_VIEW":               
        spectate_view()
    else:
        # ukendt state → tilbage til LANDING
        st.warning(f"Ukendt view: {view} — resetter.")
        st.session_state.view = "LANDING"
        st.rerun()

if __name__ == "__main__":
    main()


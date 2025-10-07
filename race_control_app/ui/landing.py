import streamlit as st

def landing():
    st.title("🏁 24hlan 2025 – Stint Control")
    st.write("Vælg adgang:")

    c1, c2, c3 = st.columns(3)
    with c1:
        if st.button("👑 ADMIN", key="btn_admin"):
            st.session_state.view = "ADMIN_LOGIN"; st.rerun()
    with c2:
        if st.button("👤 USER", key="btn_user"):
            st.session_state.view = "USER_TEAM_PICK"; st.rerun()
    with c3:
        if st.button("👀 SPECTATE", key="btn_spectate"):
            st.session_state.view = "SPECTATE_VIEW"; st.rerun()

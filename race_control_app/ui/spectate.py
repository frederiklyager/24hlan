# ui/spectate.py
import os, sys
sys.path.append(os.path.dirname(os.path.dirname(__file__)))  # allow "core.*" imports when run directly

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

from core.repo import spectate_grid

REFRESH_MS = 30_000   # 30 sek.

def _enable_autorefresh():
    """Brug streamlit-autorefresh hvis tilgængelig, ellers en lille JS-fallback."""
    try:
        from streamlit_autorefresh import st_autorefresh  # lazy import
        # The return value increments on each refresh, triggering Streamlit's reactive rerun
        count = st_autorefresh(interval=REFRESH_MS, key="spectate_autorefresh")
        return count
    except Exception:
        # Fallback: Use Streamlit's JavaScript to trigger a rerun instead of full page reload
        components.html(
            f"""
            <script>
              setTimeout(function () {{
                  // Use Streamlit's internal rerun mechanism
                  window.parent.postMessage({{
                      type: 'streamlit:setComponentValue',
                      value: Date.now()
                  }}, '*');
              }}, {REFRESH_MS});
            </script>
            """,
            height=0, width=0
        )
        return None

def spectate_view():
    st.header("Spectate ")
    st.caption(f"⏱️ Opdaterer automatisk hvert {REFRESH_MS//1000} sek.")
    
    # Enable auto-refresh at the top of the view
    refresh_count = _enable_autorefresh()

    try:
        df = spectate_grid()
    except Exception as e:
        st.error("Kunne ikke hente data til Spectate.")
        st.exception(e)
        return

    if df.empty:
        st.info("Ingen teams i databasen endnu.")
        return

    display = df.rename(columns={
        "team_no": "Car no.",
        "car_class": "Class",
        "team_name": "Team Name",
        "driver_name": "Driver Name",
    })[["Car no.", "Class", "Team Name", "Driver Name"]]

    display["Car no."] = display["Car no."].apply(
        lambda x: "-" if (pd.isna(x) or x == "") else int(x)
    )
    display["Driver Name"] = display["Driver Name"].fillna("-")

    st.dataframe(display, use_container_width=True, hide_index=True)

    c1, c2 = st.columns(2)
    with c1:
        if st.button("🔄 Opdater"):
            st.rerun()
    with c2:
        if st.button("◀ Tilbage"):
            st.session_state.view = "LANDING"
            st.rerun()

if __name__ == "__main__":
    st.set_page_config(page_title="Spectate – iRacing", page_icon="👀", layout="centered")
    spectate_view()
# ui/spectate.py
import os, sys, time
sys.path.append(os.path.dirname(os.path.dirname(__file__)))  # allow running directly

import pandas as pd
import streamlit as st
from core.repo import spectate_grid


AUTO_REFRESH_SECONDS = 30
TIMER_KEY = "spectate_next_refresh_ts"


def _auto_refresh_every(seconds: int, key: str) -> None:
    """
    Lightweight auto-refresh without external packages.
    Refreshes the page when `seconds` have passed since the last refresh.
    """
    now = time.time()
    if key not in st.session_state:
        # first render — schedule next refresh
        st.session_state[key] = now + seconds
        return

    if now >= st.session_state[key]:
        # schedule the next refresh and rerun
        st.session_state[key] = now + seconds
        st.rerun()


def spectate_view():
    st.header("Spectate 👁️")

    # Auto-refresh every 30s
    _auto_refresh_every(AUTO_REFRESH_SECONDS, TIMER_KEY)
    st.caption(f"⏳ Opdaterer automatisk hvert {AUTO_REFRESH_SECONDS} sek.")

    # Load data
    try:
        df = spectate_grid()
    except Exception as e:
        st.error("Kunne ikke hente data til Spectate.")
        st.exception(e)
        return

    if df.empty:
        st.info("Ingen teams i databasen endnu.")
        return

    # Pretty display
    display = df.rename(
        columns={
            "team_no": "Car no.",
            "car_class": "Class",
            "team_name": "Team Name",
            "driver_name": "Driver Name",
        }
    )

    cols = ["Car no.", "Class", "Team Name", "Driver Name"]
    display = display.reindex(columns=cols)

    # Format car numbers nicely: show '-' when NaN, otherwise int
    def _fmt_no(v):
        if pd.isna(v) or str(v).strip() == "":
            return "-"
        try:
            return int(v)
        except Exception:
            return str(v)

    display["Car no."] = display["Car no."].apply(_fmt_no)

    st.dataframe(display, use_container_width=True, hide_index=True)

    c1, c2 = st.columns(2)
    with c1:
        if st.button("🔄 Opdater"):
            st.rerun()
    with c2:
        if st.button("◀ Tilbage"):
            st.session_state.view = "LANDING"
            st.rerun()


# Allow running this file directly
if __name__ == "__main__":
    st.set_page_config(page_title="Spectate – iRacing", page_icon="👀", layout="centered")
    spectate_view()

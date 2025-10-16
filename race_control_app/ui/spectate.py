# ui/spectate.py
import os, sys
sys.path.append(os.path.dirname(os.path.dirname(__file__)))  # allow "core.*" imports when run directly

import pandas as pd
import streamlit as st
import time
from datetime import datetime

from core.repo import spectate_grid

REFRESH_SEC = 30  # 30 sekunder

def spectate_view():
    st.header("Spectate  👁️")
    
    # Initialize last_update timestamp in session state
    if 'spectate_last_update' not in st.session_state:
        st.session_state.spectate_last_update = time.time()
    
    # Initialize force refresh flag
    if 'spectate_force_refresh' not in st.session_state:
        st.session_state.spectate_force_refresh = False
    
    # Check if manual refresh was triggered
    if st.session_state.spectate_force_refresh:
        st.session_state.spectate_last_update = time.time()
        st.session_state.spectate_force_refresh = False
    
    # Check if it's time to refresh
    current_time = time.time()
    time_elapsed = current_time - st.session_state.spectate_last_update
    
    if time_elapsed >= REFRESH_SEC:
        # Update the timestamp and trigger rerun
        st.session_state.spectate_last_update = current_time
        st.rerun()
    
    # Calculate time until next refresh for display
    time_until_refresh = int(REFRESH_SEC - time_elapsed)
    last_updated = datetime.fromtimestamp(st.session_state.spectate_last_update).strftime("%H:%M:%S")
    
    st.caption(f"⏱️ Opdaterer automatisk hvert {REFRESH_SEC} sek. | Sidst opdateret: {last_updated} | Næste opdatering om: {time_until_refresh} sek.")

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
            st.session_state.spectate_last_update = time.time()
            st.rerun()
    with c2:
        if st.button("◀ Tilbage"):
            # Clean up session state when leaving
            if 'spectate_last_update' in st.session_state:
                del st.session_state.spectate_last_update
            st.session_state.view = "LANDING"
            st.rerun()
    
    # Sleep briefly and rerun to update the countdown timer
    time.sleep(1)
    st.rerun()

if __name__ == "__main__":
    st.set_page_config(page_title="Spectate – iRacing", page_icon="👀", layout="centered")
    spectate_view()
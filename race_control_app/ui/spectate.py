# ui/spectate.py
import pandas as pd
import streamlit as st

# IMPORTANT: this must exist in core/repo.py (we shared it earlier)
# def spectate_grid(): ...  # returns columns: team_no, car_class, team_name, driver_name
from core.repo import spectate_grid


def spectate_view():
    st.header("Spectate")

    try:
        df = spectate_grid()
    except Exception as e:
        st.error("Kunne ikke hente data til Spectate.")
        st.exception(e)
        return

    if df.empty:
        st.info("Ingen teams i databasen endnu.")
        return

    display = df.rename(
        columns={
            "team_no": "Car no.",
            "car_class": "Class",
            "team_name": "Team Name",
            "driver_name": "Driver Name",
        }
    )
    # ønsket kolonneorden
    cols = ["Car no.", "Class", "Team Name", "Driver Name"]
    display = display.reindex(columns=cols)

    # vis '-' for manglende nummer
    display["Car no."] = display["Car no."].apply(lambda x: "-" if pd.isna(x) else int(x))

    st.dataframe(display, use_container_width=True, hide_index=True)

    c1, c2 = st.columns(2)
    with c1:
        if st.button("🔄 Opdater"):
            st.rerun()
    with c2:
        if st.button("◀ Tilbage"):
            st.session_state.view = "LANDING"
            st.rerun()


# Allow this file to run standalone for testing:
if __name__ == "__main__":
    # keep it minimal here so we don't depend on your app's setup_page()
    st.set_page_config(page_title="Spectate – iRacing", page_icon="👀", layout="centered")
    spectate_view()

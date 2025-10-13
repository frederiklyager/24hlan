import os, sys, time
import pandas as pd
import streamlit as st

# Gør det muligt at importere fra projektroden
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from core.repo import spectate_grid
from streamlit_autorefresh import st_autorefresh

REFRESH_INTERVAL_MS = 30_000  # 30 sek.

def spectate_view():
    st.set_page_config(page_title="Spectate", layout="wide")
    st.title("👁️ Spectate")

    # Autorefresh (client-side rerun)
    # Returnerer et tal der stiger ved hver refresh – vi bruger det ikke direkte,
    # men det sørger for periodisk opdatering.
    st_autorefresh(interval=REFRESH_INTERVAL_MS, key="spectate_autorefresh")

    # Init og udregn 'sidst opdateret'
    if "last_run_ts" not in st.session_state:
        st.session_state.last_run_ts = time.time()

    seconds_since = int(time.time() - st.session_state.last_run_ts)

    # UI: statuslinje (viser både tæller og interval)
    st.caption(f"⏳ Opdaterer automatisk hvert 30 sek. — sidst opdateret for {seconds_since} sek. siden")

    # Hent og vis data
    try:
        df = spectate_grid()
        if df is None or (isinstance(df, pd.DataFrame) and df.empty):
            st.warning("Ingen data at vise endnu.")
        else:
            # Sørg for pæn kolonnebredde og fuld bredde
            st.dataframe(df, use_container_width=True)
    except Exception as e:
        st.error(f"Kunne ikke hente data: {e}")

    # Handlinger
    c1, c2 = st.columns([1, 1])
    with c1:
        if st.button("🔄 Opdater nu"):
            st.session_state.last_run_ts = time.time()
            st.rerun()
    with c2:
        # Vis evt. tilbage-link, hvis du har en main-side
        try:
            st.page_link("ui/main.py", label="◀ Tilbage")
        except Exception:
            pass

    # Opdater 'sidst opdateret' til nu i slutningen af run'et
    st.session_state.last_run_ts = time.time()

if __name__ == "__main__":
    spectate_view()

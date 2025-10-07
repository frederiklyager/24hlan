# ui/user.py — FULD VERSION (uden første password)
import streamlit as st
import pandas as pd
from core.repo import (
    list_teams, get_team_id_by_name, get_team_pin,
    team_drivers, current_stint, stint_history, start_stint
)

# ui/user.py
import streamlit as st
import pandas as pd
from core.repo import (
    list_teams, get_team_id_by_name, get_team_pin,
    team_drivers, current_stint, stint_history, start_stint
)

def user_team_pick():
    """Vælg hold fra dropdown + indtast team-PIN."""
    st.header("Vælg dit team")

    teams_df = list_teams(None)
    if teams_df.empty:
        st.info("Ingen teams i databasen endnu.")
        if st.button("◀ Tilbage"):
            st.session_state.view = "LANDING"; st.rerun()
        return

    team_names = teams_df["name"].tolist()
    team_name = st.selectbox("Team", team_names, key="user_pick_team")

    pin = st.text_input("Team password (PIN)", type="password", key="user_team_pin")

    c1, c2 = st.columns(2)
    with c1:
        if st.button("Åbn team", key="user_open_team"):
            team_id = get_team_id_by_name(team_name)
            if team_id is None:
                st.error("Ugyldigt team.")
            elif pin == get_team_pin(team_id):
                st.session_state.update(
                    user_team_id=team_id,
                    user_team_name=team_name,
                    view="USER_TEAM_VIEW",
                )
                st.rerun()
            else:
                st.error("Forkert team password.")
    with c2:
        if st.button("◀ Tilbage", key="user_back"):
            st.session_state.view = "LANDING"; st.rerun()

def user_team_view():
    """Team-siden: vis 'Currently driving', vælg næste kører, og se historik."""
    team_id = st.session_state.get("user_team_id")
    team_name = st.session_state.get("user_team_name")

    if not team_id or not team_name:
        st.warning("Ingen team valgt.")
        st.session_state.view = "USER_TEAM_PICK"; st.rerun()
        return

    st.header(f"USER – {team_name}")

    # Currently driving
    st.subheader("Currently driving")
    curr = current_stint(team_id)
    if curr:
        st.success(f"**{curr['name']}** (siden {curr['start_ts']})")
    else:
        st.warning("Ingen aktiv kører.")

    # Aktive kørere → vælg næste
    drivers = team_drivers(team_id)
    active_drivers = drivers[drivers["is_active"] == 1]
    if active_drivers.empty:
        st.info("Ingen aktive kørere på holdet. Bed en admin aktivere mindst én kører.")
    else:
        # Map kun navn -> id, så dropdown viser rent navn
        driver_map = {r.name: int(r.driver_id) for r in active_drivers.itertuples()}
        selection = st.selectbox(
            "Vælg kører til næste stint",
            options=list(driver_map.keys()),
            key="user_next_driver"
        )
        chosen_driver_id = driver_map[selection]

        if st.button("🚦 Start ny stint", key="user_start_stint"):
            try:
                start_stint(team_id, chosen_driver_id)
                st.success(f"Ny stint startet med {selection}")
                st.rerun()
            except Exception as e:
                st.error(f"Kunne ikke starte stint: {e}")

    # Historik
    st.subheader("Stint-historik (seneste 20)")
    hist = stint_history(team_id, limit=20)
    if hist.empty:
        st.info("Ingen stints registreret endnu.")
    else:
        st.dataframe(hist, use_container_width=True)

    # Log ud
    if st.button("🔒 Log ud", key="user_logout"):
        for k in ["user_team_id", "user_team_name", "user_team_pin", "user_next_driver", "user_pick_team"]:
            st.session_state.pop(k, None)
        st.session_state.view = "LANDING"
        st.rerun()


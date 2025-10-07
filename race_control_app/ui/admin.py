# ui/admin.py — alt UI er indkapslet i admin_panel()
import os
import pandas as pd
import streamlit as st

from core.db import DB_PATH, ensure_schema, get_conn
from core.importers import (
    import_wide_csv, import_csv_to_db,
    fetch_public_sheet_as_df, guess_column
)
from core.repo import (
    list_car_classes, list_teams, team_drivers, current_stint,
    stint_history, start_stint, set_driver_active, set_team_pin
)

# Kolonne-heuristikker
CANDIDATE_TEAM    = ["team", "team name", "team_name", "hold", "holdnavn"]
CANDIDATE_CLASS   = ["class", "car_class", "klasse", "bilklasse", "car category"]
CANDIDATE_DRIVER  = ["driver", "driver name", "driver_name", "kører", "koerer"]
CANDIDATE_TEAM_NO = ["car no", "car no.", "number", "start no", "start nr", "team no", "team nr"]


def _teams_with_pins_df() -> pd.DataFrame:
    with get_conn() as conn:
        return pd.read_sql_query(
            "SELECT id, name, car_class, COALESCE(team_pin,'1234') AS team_pin "
            "FROM team ORDER BY name;", conn
        )


def admin_panel():
    st.header("ADMIN")

    # ─────────────────────────────────────────────────────────────────────────────
    # 1) Importér database (lokal CSV)
    # ─────────────────────────────────────────────────────────────────────────────
    with st.expander("🗂️ Importér / Reset database fra CSV (lokal fil)", expanded=False):
        file = st.file_uploader("Vælg CSV", type=["csv"], key="local_csv")
        if file is not None:
            df = pd.read_csv(file)
            st.write("Forhåndsvisning:", df.head())
            cols = df.columns.tolist()

            guess_team     = guess_column(cols, CANDIDATE_TEAM)  or cols[0]
            guess_class    = guess_column(cols, CANDIDATE_CLASS) or cols[1]
            guess_team_no  = guess_column(cols, CANDIDATE_TEAM_NO)
            driver_candidates = [c for c in cols if any(k in c.lower() for k in ["driver","kører","koerer"])] or cols[2:]

            mode = st.radio(
                "CSV-format",
                ["Bredt ark (Driver name 1..N)", "Langt ark (én driver pr. række)"],
                index=0, key="local_mode"
            )

            c1, c2, c3 = st.columns(3)
            with c1:
                col_team  = st.selectbox("Team-kolonne", options=cols, index=cols.index(guess_team), key="local_team_col")
            with c2:
                col_class = st.selectbox("Bilklasse-kolonne", options=cols, index=cols.index(guess_class), key="local_class_col")
            with c3:
                sel_team_no = st.selectbox(
                    "Team nummer-kolonne (valgfri)", ["(ingen)"] + cols,
                    index=(0 if not guess_team_no else (cols.index(guess_team_no) + 1)),
                    key="local_team_no_col"
                )
                col_team_no = None if sel_team_no == "(ingen)" else sel_team_no

            if mode.startswith("Bredt"):
                chosen_driver_cols = st.multiselect(
                    "Driver-kolonner", options=cols, default=driver_candidates, key="local_driver_cols"
                )
            else:
                col_driver = st.selectbox(
                    "Driver-kolonne", options=cols,
                    index=(cols.index(driver_candidates[0]) if driver_candidates else 0),
                    key="local_driver_col"
                )

            if st.button("📥 Importér til DB", type="primary", use_container_width=True, key="local_import_btn"):
                try:
                    if mode.startswith("Bredt"):
                        import_wide_csv(
                            df, col_team=col_team, col_class=col_class,
                            driver_cols=chosen_driver_cols, col_team_no=col_team_no
                        )
                    else:
                        import_csv_to_db(
                            df, col_team=col_team, col_driver=col_driver, col_class=col_class,
                            col_irid=None, col_team_no=col_team_no
                        )
                    st.success("Import gennemført ✅ (team PIN default = '1234')")
                    st.rerun()
                except Exception as e:
                    st.error(f"Import fejl: {e}")
        else:
            st.caption("Upload en CSV for at se mapping-valgene her.")

    # ─────────────────────────────────────────────────────────────────────────────
    # 1b) Importér fra Google Sheets (offentlig)
    # ─────────────────────────────────────────────────────────────────────────────
    with st.expander("📄 Importér fra Google Sheets (offentlig læsning)", expanded=False):
        st.caption("Gør arket sharebart (Viewer). Indsæt **kun** Spreadsheet ID og **gid** (fanebladstal).")
        gs_id = st.text_input("Spreadsheet ID (fra URL: .../d/<ID>/edit#gid=...)", key="gs_id").strip()
        gid   = st.text_input("gid (fra URL: ...gid=<gid>)", value="0", key="gs_gid").strip()

        mode2 = st.radio(
            "CSV-format",
            ["Bredt ark (Driver name 1..N)", "Langt ark (én driver pr. række)"],
            index=0, key="gs_mode"
        )

        if st.button("Hent & importér fra Google Sheets", key="gs_fetch_btn"):
            try:
                df = fetch_public_sheet_as_df(gs_id, gid)
                st.write("Forhåndsvisning:", df.head())
                cols = df.columns.tolist()

                guess_team     = guess_column(cols, CANDIDATE_TEAM)  or cols[0]
                guess_class    = guess_column(cols, CANDIDATE_CLASS) or cols[1]
                guess_team_no  = guess_column(cols, CANDIDATE_TEAM_NO)
                driver_candidates = [c for c in cols if any(k in c.lower() for k in ["driver","kører","koerer"])] or cols[2:]

                if mode2.startswith("Bredt"):
                    import_wide_csv(
                        df, col_team=guess_team, col_class=guess_class,
                        driver_cols=driver_candidates, col_team_no=guess_team_no
                    )
                else:
                    col_driver = guess_column(cols, CANDIDATE_DRIVER) or driver_candidates[0]
                    import_csv_to_db(
                        df, col_team=guess_team, col_driver=col_driver,
                        col_class=guess_class, col_irid=None, col_team_no=guess_team_no
                    )

                st.success("Import fra Google Sheets fuldført ✅")
                st.rerun()
            except Exception as e:
                st.error(f"Kunne ikke importere fra Google Sheets: {e}")

    # ─────────────────────────────────────────────────────────────────────────────
    # 2) Slet hele databasen (danger zone)
    # ─────────────────────────────────────────────────────────────────────────────
    with st.expander("🧨 Slet hele databasen (irreversibelt)", expanded=False):
        st.warning("Dette sletter **alle** teams, kørere og historik. Kan ikke fortrydes.")
        colA, colB = st.columns(2)
        with colA:
            confirm = st.checkbox("Jeg forstår konsekvensen", key="wipe_confirm")
        with colB:
            typed = st.text_input("Skriv: DELETE", key="wipe_text")

        if st.button("❌ Delete current database", type="secondary", disabled=not confirm):
            if typed.strip().upper() != "DELETE":
                st.error("Bekræft ved at skrive **DELETE**.")
            else:
                try:
                    if os.path.exists(DB_PATH):
                        os.remove(DB_PATH)
                    ensure_schema()
                    st.success("Databasen er slettet og genskabt tom ✅")
                    st.rerun()
                except Exception as e:
                    st.error(f"Kunne ikke slette databasen: {e}")

    # ─────────────────────────────────────────────────────────────────────────────
    # 3) Status og styring
    # ─────────────────────────────────────────────────────────────────────────────
    st.subheader("Status og styring")

    classes = list_car_classes()
    car_class = st.selectbox("Filtrér bilklasse", options=["(Alle)"] + classes, key="admin_class_filter")
    car_class = None if car_class == "(Alle)" else car_class

    teams_df2 = list_teams(car_class)
    if teams_df2.empty:
        st.info("Ingen teams i denne klasse.")
        if st.button("↺ Opdater"): st.rerun()
        st.stop()

    names = teams_df2["name"].tolist()
    team_name = st.selectbox("Vælg team", options=names, key="admin_team_select")
    team_id = int(teams_df2.loc[teams_df2["name"] == team_name, "id"].iloc[0])

    st.markdown(f"**Hold:** {team_name}")
    curr = current_stint(team_id)
    if curr:
        st.success(f"Aktuel kører: **{curr['name']}** (siden {curr['start_ts']})")
    else:
        st.warning("Ingen aktiv kører.")

    st.markdown("**Kørere (toggle aktiv/inaktiv)**")
    drivers = team_drivers(team_id)
    for r in drivers.itertuples():
        toggled = st.toggle(r.name, value=(r.is_active == 1), key=f"toggle_{team_id}_{r.driver_id}")
        if toggled != (r.is_active == 1):
            set_driver_active(team_id, r.driver_id, toggled)
            st.toast(f"{r.name} sat til {'aktiv' if toggled else 'inaktiv'}.")
            st.rerun()

    active_drivers = drivers[drivers["is_active"] == 1]
    if not active_drivers.empty:
        selection = st.selectbox(
            "Start ny stint (aktive kørere)",
            options=[f"{int(rr.driver_id)} – {rr.name}" for rr in active_drivers.itertuples()],
            key="admin_startstint_select"
        )
        chosen_driver_id = int(selection.split(" – ")[0])
        if st.button("🚦 Start ny stint (admin)", key="admin_startstint_btn"):
            try:
                start_stint(team_id, chosen_driver_id)
                st.success("Ny stint startet.")
                st.rerun()
            except Exception as e:
                st.error(f"Fejl: {e}")

    st.markdown("**Stint-historik (seneste 20)**")
    hist = stint_history(team_id, limit=20)
    if hist.empty:
        st.info("Ingen stints registreret.")
    else:
        st.dataframe(hist, use_container_width=True)
        csv = hist.to_csv(index=False).encode("utf-8")
        st.download_button("⬇️ Download historik (CSV)", csv, file_name=f"{team_name}_stints.csv",
                           mime="text/csv", key="admin_hist_dl")
    st.divider()

    # ─────────────────────────────────────────────────────────────────────────────
    # 4) Team passwords (PINs) – nederst
    # ─────────────────────────────────────────────────────────────────────────────
    st.subheader("Team passwords (PINs)")
    pins_df = _teams_with_pins_df()
    if pins_df.empty:
        st.info("Ingen teams i databasen.")
    else:
        for r in pins_df.itertuples():
            st.write(f"**{r.name}** ({r.car_class})")
            new_pin = st.text_input("Team PIN", value=r.team_pin, key=f"pin_{r.id}")
            if st.button("Gem PIN", key=f"savepin_{r.id}"):
                set_team_pin(int(r.id), new_pin.strip() or "1234")
                st.success("PIN opdateret")

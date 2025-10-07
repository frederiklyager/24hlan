# core/repo.py
import pandas as pd
from core.db import get_conn

# ---------- Hjælpere ----------
def normalize_class(val: str) -> str:
    """
    Normaliserer klasse-felter fra CSV/Sheets til faste værdier:
      - "GTP" (eller "LMDh" osv.) -> "GTP"
      - "GT3 AM" -> "GT3 AM"
      - "GT3 PRO" -> "GT3 PRO"
      - Alle andre GT3-varianter -> "GT3"
    """
    if not isinstance(val, str):
        return "GT3"

    v = val.strip().upper()

    # GTP/LMDh
    if "GTP" in v or "LMDH" in v:
        return "GTP"

    if "GT3" in v:
        has_am = "AM" in v
        has_pro = "PRO" in v
        if has_am and not has_pro:
            return "GT3 AM"
        if has_pro and not has_am:
            return "GT3 PRO"
        return "GT3"

    return "GT3"


# ---------- Læsninger ----------
def list_car_classes():
    """Returnér liste af klasser i en fornuftig rækkefølge."""
    with get_conn() as conn:
        df = pd.read_sql_query("SELECT DISTINCT car_class FROM team;", conn)
    classes = df["car_class"].dropna().tolist()

    order = {"GTP": 0, "GT3 PRO": 1, "GT3 AM": 2, "GT3": 3}
    classes.sort(key=lambda x: order.get(x, 99))
    return classes


def list_teams(car_class=None):
    """Returnér teams (id, name, team_no) sorteret på klasse → team_no → name.
       Fallback til schema uden team_no hvis nødvendigt."""
    with get_conn() as conn:
        try:
            if car_class:
                return pd.read_sql_query(
                    "SELECT id, name, team_no FROM team WHERE car_class=? "
                    "ORDER BY team_no IS NULL, team_no, name;",
                    conn, params=(car_class,)
                )
            return pd.read_sql_query(
                "SELECT id, name, team_no FROM team "
                "ORDER BY team_no IS NULL, team_no, name;",
                conn
            )
        except Exception:
            # Fallback til ældre schema uden team_no
            if car_class:
                return pd.read_sql_query(
                    "SELECT id, name FROM team WHERE car_class=? ORDER BY name;",
                    conn, params=(car_class,)
                )
            return pd.read_sql_query(
                "SELECT id, name FROM team ORDER BY name;",
                conn
            )


def spectate_grid():
    """
    Returnerer en DataFrame med nuværende kører pr. team.
    Kolonner: team_no, car_class, team_name, driver_name
    Sortering: GTP -> GT3 PRO -> GT3 AM -> GT3 -> andre; derefter team_no, teamnavn.
    """
    sql = """
    SELECT
      t.team_no,
      t.car_class,
      t.name  AS team_name,
      d.name  AS driver_name
    FROM team t
    LEFT JOIN stint s
      ON s.team_id = t.id AND s.end_ts IS NULL
    LEFT JOIN driver d
      ON d.id = s.driver_id
    ORDER BY
      CASE UPPER(COALESCE(t.car_class,'')) 
        WHEN 'GTP' THEN 0
        WHEN 'GT3 PRO' THEN 1
        WHEN 'GT3 AM' THEN 2
        WHEN 'GT3' THEN 3
        ELSE 9
      END,
      t.team_no IS NULL,
      t.team_no,
      t.name;
    """
    with get_conn() as conn:
        try:
            df = pd.read_sql_query(sql, conn)
        except Exception:
            # Fallback hvis ældre schema uden team_no
            sql_legacy = """
            SELECT
              NULL AS team_no,
              t.car_class,
              t.name AS team_name,
              d.name AS driver_name
            FROM team t
            LEFT JOIN stint s
              ON s.team_id = t.id AND s.end_ts IS NULL
            LEFT JOIN driver d
              ON d.id = s.driver_id
            ORDER BY
              CASE UPPER(COALESCE(t.car_class,'')) 
                WHEN 'GTP' THEN 0
                WHEN 'GT3 PRO' THEN 1
                WHEN 'GT3 AM' THEN 2
                WHEN 'GT3' THEN 3
                ELSE 9
              END,
              t.name;
            """
            df = pd.read_sql_query(sql_legacy, conn)

    # UI-venlig formatering
    if "driver_name" in df.columns:
        df["driver_name"] = df["driver_name"].fillna("-")
    if "team_no" in df.columns:
        df["team_no"] = df["team_no"].astype("Int64")  # bevarer NaN som <NA>
    return df


def get_team_id_by_name(name: str):
    with get_conn() as conn:
        df = pd.read_sql_query("SELECT id FROM team WHERE name=?;", conn, params=(name,))
    return int(df.iloc[0]["id"]) if not df.empty else None


def get_team_pin(team_id: int) -> str:
    with get_conn() as conn:
        df = pd.read_sql_query(
            "SELECT COALESCE(team_pin,'1234') AS team_pin FROM team WHERE id=?;",
            conn, params=(team_id,)
        )
    return df.iloc[0]["team_pin"] if not df.empty else "1234"


def team_drivers(team_id: int):
    sql = """
      SELECT d.id AS driver_id, d.name, td.is_active
      FROM team_driver td
      JOIN driver d ON d.id = td.driver_id
      WHERE td.team_id = ?
      ORDER BY d.name;
    """
    with get_conn() as conn:
        return pd.read_sql_query(sql, conn, params=(team_id,))


def current_stint(team_id: int):
    sql = """
      SELECT s.id, s.team_id, s.driver_id, d.name, s.start_ts
      FROM stint s
      JOIN driver d ON d.id = s.driver_id
      WHERE s.team_id=? AND s.end_ts IS NULL
      LIMIT 1;
    """
    with get_conn() as conn:
        df = pd.read_sql_query(sql, conn, params=(team_id,))
    return df.iloc[0].to_dict() if not df.empty else None


def stint_history(team_id: int, limit: int = 20):
    sql = """
      SELECT d.name AS driver, s.start_ts, COALESCE(s.end_ts,'(active)') AS end_ts
      FROM stint s
      JOIN driver d ON d.id = s.driver_id
      WHERE s.team_id=?
      ORDER BY s.start_ts DESC
      LIMIT ?;
    """
    with get_conn() as conn:
        return pd.read_sql_query(sql, conn, params=(team_id, limit))


# ---------- Skrivninger ----------
def start_stint(team_id: int, driver_id: int):
    with get_conn() as conn:
        cur = conn.cursor()
        # Slut evt. eksisterende aktiv stint for teamet
        cur.execute("UPDATE stint SET end_ts=datetime('now') WHERE team_id=? AND end_ts IS NULL;", (team_id,))
        # Start ny
        cur.execute(
            "INSERT INTO stint (team_id, driver_id, start_ts, end_ts) VALUES (?, ?, datetime('now'), NULL);",
            (team_id, driver_id)
        )
        conn.commit()


def set_driver_active(team_id: int, driver_id: int, is_active: bool):
    with get_conn() as conn:
        conn.execute(
            "UPDATE team_driver SET is_active=? WHERE team_id=? AND driver_id=?;",
            (1 if is_active else 0, team_id, driver_id)
        )
        conn.commit()


def set_team_pin(team_id: int, new_pin: str):
    with get_conn() as conn:
        conn.execute("UPDATE team SET team_pin=? WHERE id=?;", (new_pin, team_id))
        conn.commit()

def set_team_number(team_id: int, team_no: int | None):
    with get_conn() as conn:
        conn.execute("UPDATE team SET team_no=? WHERE id=?;", (team_no, team_id))
        conn.commit()

def set_team_class(team_id: int, car_class: str):
    with get_conn() as conn:
        conn.execute("UPDATE team SET car_class=? WHERE id=?;", (car_class, team_id))
        conn.commit()

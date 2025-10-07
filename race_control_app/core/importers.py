# core/importers.py
import pandas as pd
from typing import Iterable, Optional

from core.db import get_conn
from core.repo import normalize_class

# -------------- Small helpers --------------

def guess_column(cols: Iterable[str], candidates: Iterable[str]) -> Optional[str]:
    """Find first column in 'cols' that loosely matches any of the 'candidates'."""
    cl = [c.lower() for c in cols]
    for cand in candidates:
        k = cand.lower()
        for i, c in enumerate(cl):
            if k in c:
                return list(cols)[i]
    return None


# -------------- Insert helpers --------------

def _get_or_create_team(conn, name: str, car_class: str, team_no: Optional[int]):
    cur = conn.cursor()
    # Try by name first
    cur.execute("SELECT id FROM team WHERE name=?;", (name,))
    row = cur.fetchone()
    if row:
        team_id = row[0]
        # keep team_no / class in sync if provided
        if team_no is not None:
            cur.execute("UPDATE team SET team_no=? WHERE id=?;", (team_no, team_id))
        if car_class:
            cur.execute("UPDATE team SET car_class=? WHERE id=?;", (car_class, team_id))
        conn.commit()
        return team_id

    # Create
    cur.execute(
        "INSERT INTO team (name, car_class, team_no) VALUES (?, ?, ?);",
        (name, car_class, team_no)
    )
    conn.commit()
    return cur.lastrowid


def _get_or_create_driver(conn, name: str):
    cur = conn.cursor()
    cur.execute("SELECT id FROM driver WHERE name=?;", (name,))
    row = cur.fetchone()
    if row:
        return row[0]
    cur.execute("INSERT INTO driver (name) VALUES (?);", (name,))
    conn.commit()
    return cur.lastrowid


def _ensure_team_driver(conn, team_id: int, driver_id: int):
    cur = conn.cursor()
    cur.execute(
        "SELECT 1 FROM team_driver WHERE team_id=? AND driver_id=?;",
        (team_id, driver_id)
    )
    if not cur.fetchone():
        cur.execute(
            "INSERT INTO team_driver (team_id, driver_id, is_active) VALUES (?, ?, 1);",
            (team_id, driver_id)
        )
        conn.commit()


# -------------- Public importers --------------

def import_wide_csv(
    df: pd.DataFrame,
    *,
    col_team: str,
    col_class: str,
    driver_cols: Iterable[str],
    col_team_no: Optional[str] = None,
) -> None:
    """
    Wide format: one row per team; multiple 'Driver name N' columns.

    col_team_no is optional: if provided, we will store/update team_no.
    """
    cols = df.columns.tolist()
    assert col_team in cols and col_class in cols, "Missing team/class columns"

    with get_conn() as conn:
        for _, row in df.iterrows():
            team_name = str(row[col_team]).strip()
            if not team_name:
                continue

            raw_class = str(row[col_class]).strip()
            car_class = normalize_class(raw_class)

            team_no = None
            if col_team_no and col_team_no in cols:
                try:
                    v = row[col_team_no]
                    team_no = int(v) if pd.notna(v) and str(v).strip() != "" else None
                except Exception:
                    team_no = None

            team_id = _get_or_create_team(conn, team_name, car_class, team_no)

            for dc in driver_cols:
                if dc not in cols:
                    continue
                val = row[dc]
                if pd.isna(val):
                    continue
                name = str(val).strip()
                if not name:
                    continue

                driver_id = _get_or_create_driver(conn, name)
                _ensure_team_driver(conn, team_id, driver_id)


def import_csv_to_db(
    df: pd.DataFrame,
    *,
    col_team: str,
    col_driver: str,
    col_class: str,
    col_irid: Optional[str] = None,     # kept for future use
    col_team_no: Optional[str] = None,  # NEW: optional team number column
) -> None:
    """
    Long format: each row is a driver/team pair.
    """
    cols = df.columns.tolist()
    assert col_team in cols and col_driver in cols and col_class in cols, "Missing columns"

    with get_conn() as conn:
        for _, row in df.iterrows():
            team_name = str(row[col_team]).strip()
            driver_name = str(row[col_driver]).strip()
            if not team_name or not driver_name:
                continue

            raw_class = str(row[col_class]).strip()
            car_class = normalize_class(raw_class)

            team_no = None
            if col_team_no and col_team_no in cols:
                try:
                    v = row[col_team_no]
                    team_no = int(v) if pd.notna(v) and str(v).strip() != "" else None
                except Exception:
                    team_no = None

            team_id = _get_or_create_team(conn, team_name, car_class, team_no)
            driver_id = _get_or_create_driver(conn, driver_name)
            _ensure_team_driver(conn, team_id, driver_id)


# -------------- Google Sheets fetcher --------------

def fetch_public_sheet_as_df(spreadsheet_id: str, gid: str | int) -> pd.DataFrame:
    """
    Download a public Google Sheet tab as CSV and return DF.
    """
    import io, requests
    url = f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}/export?format=csv&gid={gid}"
    r = requests.get(url, timeout=30)
    r.raise_for_status()
    return pd.read_csv(io.StringIO(r.text))

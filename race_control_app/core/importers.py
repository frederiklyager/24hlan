# core/importers.py
from __future__ import annotations

import io
import unicodedata
from typing import Iterable, Optional

import pandas as pd
import requests

from core.db import get_conn
from core.repo import normalize_class

__all__ = [
    "guess_column",
    "import_wide_csv",
    "import_csv_to_db",
    "fetch_public_sheet_as_df",
    "_fix_mojibake",
    "fix_mojibake",
]

# -------------- Små hjælpere --------------

def guess_column(cols: Iterable[str], candidates: Iterable[str]) -> Optional[str]:
    """Find første kolonnenavn i 'cols' der (løst) matcher en af 'candidates'."""
    cl = [c.lower() for c in cols]
    for cand in candidates:
        k = cand.lower()
        for i, c in enumerate(cl):
            if k in c:
                return list(cols)[i]
    return None


def _fix_mojibake(text: str) -> str:
    """
    Ret klassisk UTF-8→latin1 mojibake for nordiske tegn (æøå m.fl.).
    Bevarer andre tegn og normaliserer resultatet til NFC.
    """
    if text is None:
        return text
    if not isinstance(text, str):
        text = str(text)

    # Almindelige fejlsekvenser ved UTF-8 der fejltolkes som latin-1
    repl = {
        # dansk/nordisk
        "Ã¦": "æ", "Ã¸": "ø", "Ã¥": "å",
        "Ã†": "Æ", "Ã˜": "Ø", "Ã…": "Å",
        # svensk/tysk/andre hyppige
        "Ã¤": "ä", "Ã¶": "ö", "Ã¼": "ü", "Ã": "ß",
        "Ã©": "é", "Ã¨": "è", "Ãª": "ê",
        "Ã³": "ó", "Ã´": "ô", "Ãº": "ú", "Ã¡": "á",
        # “støj” der ofte optræder
        "Â": "",
    }
    bad_hit = False
    for bad, good in repl.items():
        if bad in text:
            bad_hit = True
            text = text.replace(bad, good)

    # Hvis vi har set typiske mojibake-tegn, så prøv også en
    # defensiv latin1→utf8 runde (uden at crashe ved fejl)
    if bad_hit:
        try:
            text = text.encode("latin-1").decode("utf-8")
        except Exception:
            pass

    return unicodedata.normalize("NFC", text)


# offentligt alias hvis du hellere vil importere uden underscore
fix_mojibake = _fix_mojibake


def _apply_fix_to_cols(df: pd.DataFrame, cols: Iterable[str]) -> pd.DataFrame:
    """Kør mojibake-fix på valgte tekstkolonner, hvis de findes."""
    for c in cols:
        if c and c in df.columns and pd.api.types.is_object_dtype(df[c]):
            df[c] = df[c].apply(_fix_mojibake)
    return df


# -------------- Insert-hjælpere --------------

def _get_or_create_team(conn, name: str, car_class: str, team_no: Optional[int]):
    cur = conn.cursor()
    cur.execute("SELECT id FROM team WHERE name=?;", (name,))
    row = cur.fetchone()
    if row:
        team_id = row[0]
        if team_no is not None:
            cur.execute("UPDATE team SET team_no=? WHERE id=?;", (team_no, team_id))
        if car_class:
            cur.execute("UPDATE team SET car_class=? WHERE id=?;", (car_class, team_id))
        conn.commit()
        return team_id

    cur.execute(
        "INSERT INTO team (name, car_class, team_no) VALUES (?, ?, ?);",
        (name, car_class, team_no),
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
        (team_id, driver_id),
    )
    if not cur.fetchone():
        cur.execute(
            "INSERT INTO team_driver (team_id, driver_id, is_active) VALUES (?, ?, 1);",
            (team_id, driver_id),
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
    Wide-format: én række pr. team med flere 'Driver name N' kolonner.
    col_team_no er valgfri; angives den, opdateres/indsættes team_no.
    """
    cols = df.columns.tolist()
    assert col_team in cols and col_class in cols, "Missing team/class columns"

    # Mojibake-fix for relevante kolonner, før vi læser værdier ud
    text_cols: set[str] = {col_team, col_class, *(driver_cols or [])}
    if col_team_no:
        text_cols.add(col_team_no)
    _apply_fix_to_cols(df, text_cols)

    with get_conn() as conn:
        for _, row in df.iterrows():
            team_name = str(row[col_team]).strip()
            if not team_name:
                continue

            raw_class = str(row[col_class]).strip()
            car_class = normalize_class(raw_class)

            team_no: Optional[int] = None
            if col_team_no and col_team_no in cols:
                v = row[col_team_no]
                try:
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
    col_irid: Optional[str] = None,     # reserveret til fremtidig brug
    col_team_no: Optional[str] = None,  # valgfri kolonne for team nummer
) -> None:
    """
    Long-format: én række pr. (team, driver)-par.
    """
    cols = df.columns.tolist()
    assert col_team in cols and col_driver in cols and col_class in cols, "Missing columns"

    # Mojibake-fix for relevante kolonner
    text_cols: set[str] = {col_team, col_driver, col_class}
    if col_team_no:
        text_cols.add(col_team_no)
    _apply_fix_to_cols(df, text_cols)

    with get_conn() as conn:
        for _, row in df.iterrows():
            team_name = str(row[col_team]).strip()
            driver_name = str(row[col_driver]).strip()
            if not team_name or not driver_name:
                continue

            raw_class = str(row[col_class]).strip()
            car_class = normalize_class(raw_class)

            team_no: Optional[int] = None
            if col_team_no and col_team_no in cols:
                v = row[col_team_no]
                try:
                    team_no = int(v) if pd.notna(v) and str(v).strip() != "" else None
                except Exception:
                    team_no = None

            team_id = _get_or_create_team(conn, team_name, car_class, team_no)
            driver_id = _get_or_create_driver(conn, driver_name)
            _ensure_team_driver(conn, team_id, driver_id)


# -------------- Google Sheets fetcher --------------

def fetch_public_sheet_as_df(sheet_id: str, gid: str) -> pd.DataFrame:
    """
    Henter et offentligt (viewer) Google Sheet-faneblad som CSV og returnerer et DataFrame.
    Vi dekoder altid som UTF-8 (errors='replace') og kører derefter en mojibake-rettelse
    på alle object-kolonner.
    """
    url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid}"
    r = requests.get(url, timeout=30)
    r.raise_for_status()

    # Tving UTF-8 (replace = vis evt. fejltegn i stedet for at crashe)
    text = r.content.decode("utf-8", errors="replace")
    df = pd.read_csv(io.StringIO(text), encoding="utf-8")

    # Ret typisk mojibake i ALLE object-kolonner
    for c in df.select_dtypes(include="object").columns:
        df[c] = df[c].apply(_fix_mojibake)

    return df

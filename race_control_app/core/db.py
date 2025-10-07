# core/db.py
import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "iracing.db")

def get_conn():
    return sqlite3.connect(DB_PATH)

def ensure_schema():
    """Opretter minimal database hvis den ikke findes."""
    conn = get_conn()
    cur = conn.cursor()

    # Minimal tables — just enough to not crash
    cur.execute("""
    CREATE TABLE IF NOT EXISTS team (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        car_class TEXT,
        team_pin TEXT
    )
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS driver (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT
    )
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS team_driver (
        team_id INTEGER,
        driver_id INTEGER,
        is_active INTEGER DEFAULT 1,
        PRIMARY KEY (team_id, driver_id)
    )
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS stint (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        team_id INTEGER,
        driver_id INTEGER,
        start_ts TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        end_ts TIMESTAMP
    )
    """)
    # --- MIGRATIONS: tilføj team_no hvis den mangler ---
    cur.execute("PRAGMA table_info(team);")
    team_cols = [r[1] for r in cur.fetchall()]
    if "team_no" not in team_cols:
        cur.execute("ALTER TABLE team ADD COLUMN team_no INTEGER;")

    cur.execute("PRAGMA table_info(driver);")
    cols = [r[1] for r in cur.fetchall()]
    if "iracing_id" not in cols:
        cur.execute("ALTER TABLE driver ADD COLUMN iracing_id TEXT;")

    conn.commit()
    conn.close()

def db_empty():
    """Returner True hvis der ikke er nogen teams i DB."""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM team")
    count = cur.fetchone()[0]
    conn.close()
    return count == 0

from core.db import get_conn
con = get_conn(); cur = con.cursor()
print(cur.execute("PRAGMA table_info(team);").fetchall())
con.close()


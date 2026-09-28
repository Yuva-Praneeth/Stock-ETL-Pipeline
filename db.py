"""
db.py
Handles all SQLite connections and schema (table) creation for the
Bronze / Silver / Gold layers.
"""

import sqlite3
from contextlib import contextmanager

DB_PATH = "stocks.db"


@contextmanager
def get_connection(db_path: str = DB_PATH):
    """Context-managed SQLite connection so we always close cleanly."""
    conn = sqlite3.connect(db_path)
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db(db_path: str = DB_PATH):
    """Create all Bronze/Silver/Gold tables if they don't already exist."""
    with get_connection(db_path) as conn:
        cur = conn.cursor()

        # ---------- BRONZE: raw, as-fetched data ----------
        cur.execute("""
            CREATE TABLE IF NOT EXISTS bronze_prices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticker TEXT NOT NULL,
                date TEXT NOT NULL,
                open REAL,
                high REAL,
                low REAL,
                close REAL,
                volume INTEGER,
                source TEXT,
                ingested_at TEXT NOT NULL
            )
        """)

        # ---------- SILVER: cleaned, typed, enriched ----------
        cur.execute("""
            CREATE TABLE IF NOT EXISTS silver_prices (
                ticker TEXT NOT NULL,
                date TEXT NOT NULL,
                open REAL,
                high REAL,
                low REAL,
                close REAL,
                volume INTEGER,
                daily_return REAL,
                ma_7 REAL,
                ma_30 REAL,
                processed_at TEXT NOT NULL,
                PRIMARY KEY (ticker, date)
            )
        """)

        # ---------- GOLD: aggregated, dashboard-ready ----------
        cur.execute("""
            CREATE TABLE IF NOT EXISTS gold_monthly_summary (
                ticker TEXT NOT NULL,
                year_month TEXT NOT NULL,
                avg_close REAL,
                min_close REAL,
                max_close REAL,
                total_volume INTEGER,
                volatility REAL,
                PRIMARY KEY (ticker, year_month)
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS gold_latest_snapshot (
                ticker TEXT PRIMARY KEY,
                last_date TEXT,
                last_close REAL,
                change_pct_1d REAL,
                ma_7 REAL,
                ma_30 REAL,
                updated_at TEXT
            )
        """)

"""
etl/bronze.py
BRONZE LAYER: land the raw API data with almost no transformation, just
metadata added (source, ingestion timestamp). This is the "single source
of truth" for what the API actually gave us -- useful for debugging and
re-processing later without hitting the API again.
"""

from datetime import datetime, timezone
import pandas as pd

from db import get_connection


def load_bronze(ticker: str, raw_df: pd.DataFrame, source: str = "yfinance") -> int:
    """
    Insert raw price rows into bronze_prices.
    Returns the number of rows inserted.
    """
    ingested_at = datetime.now(timezone.utc).isoformat()

    rows = [
        (
            ticker,
            row["date"],
            float(row["open"]) if pd.notna(row["open"]) else None,
            float(row["high"]) if pd.notna(row["high"]) else None,
            float(row["low"]) if pd.notna(row["low"]) else None,
            float(row["close"]) if pd.notna(row["close"]) else None,
            int(row["volume"]) if pd.notna(row["volume"]) else None,
            source,
            ingested_at,
        )
        for _, row in raw_df.iterrows()
    ]

    with get_connection() as conn:
        cur = conn.cursor()
        cur.executemany(
            """
            INSERT INTO bronze_prices
                (ticker, date, open, high, low, close, volume, source, ingested_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            rows,
        )

    return len(rows)


def read_bronze(ticker: str = None) -> pd.DataFrame:
    """Read back bronze rows (optionally filtered by ticker) for inspection."""
    with get_connection() as conn:
        if ticker:
            return pd.read_sql_query(
                "SELECT * FROM bronze_prices WHERE ticker = ? ORDER BY date",
                conn, params=(ticker,),
            )
        return pd.read_sql_query("SELECT * FROM bronze_prices ORDER BY ticker, date", conn)

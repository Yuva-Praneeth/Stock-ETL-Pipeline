"""
etl/silver.py
SILVER LAYER: clean, de-duplicated, correctly typed data with a couple of
derived columns (daily return, moving averages). This is the layer
analysts/other pipelines would actually query.
"""

from datetime import datetime, timezone
import pandas as pd

from db import get_connection


def transform_to_silver(bronze_df: pd.DataFrame) -> pd.DataFrame:
    """
    Clean a bronze DataFrame (for a single ticker) into silver shape:
      - drop exact duplicate rows
      - drop rows missing a close price (can't do much without it)
      - sort by date
      - add daily_return, 7-day and 30-day moving averages
    """
    df = bronze_df.drop_duplicates(subset=["ticker", "date"]).copy()
    df = df.dropna(subset=["close"])
    df = df.sort_values("date").reset_index(drop=True)

    df["daily_return"] = df["close"].pct_change()
    df["ma_7"] = df["close"].rolling(window=7, min_periods=1).mean()
    df["ma_30"] = df["close"].rolling(window=30, min_periods=1).mean()

    df["processed_at"] = datetime.now(timezone.utc).isoformat()

    cols = [
        "ticker", "date", "open", "high", "low", "close", "volume",
        "daily_return", "ma_7", "ma_30", "processed_at",
    ]
    return df[cols]


def load_silver(silver_df: pd.DataFrame) -> int:
    """Upsert silver rows (replace on ticker+date conflict)."""
    rows = [tuple(r) for r in silver_df.itertuples(index=False, name=None)]

    with get_connection() as conn:
        cur = conn.cursor()
        cur.executemany(
            """
            INSERT INTO silver_prices
                (ticker, date, open, high, low, close, volume,
                 daily_return, ma_7, ma_30, processed_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(ticker, date) DO UPDATE SET
                open=excluded.open, high=excluded.high, low=excluded.low,
                close=excluded.close, volume=excluded.volume,
                daily_return=excluded.daily_return, ma_7=excluded.ma_7,
                ma_30=excluded.ma_30, processed_at=excluded.processed_at
            """,
            rows,
        )
    return len(rows)


def read_silver(ticker: str = None) -> pd.DataFrame:
    with get_connection() as conn:
        if ticker:
            return pd.read_sql_query(
                "SELECT * FROM silver_prices WHERE ticker = ? ORDER BY date",
                conn, params=(ticker,),
            )
        return pd.read_sql_query("SELECT * FROM silver_prices ORDER BY ticker, date", conn)

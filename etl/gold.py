"""
etl/gold.py
GOLD LAYER: aggregated, dashboard-ready tables built on top of Silver.
  - gold_monthly_summary: one row per ticker per month
  - gold_latest_snapshot: one row per ticker, latest known state
"""

from datetime import datetime, timezone
import pandas as pd

from db import get_connection


def build_monthly_summary(silver_df: pd.DataFrame) -> pd.DataFrame:
    df = silver_df.copy()
    df["year_month"] = pd.to_datetime(df["date"]).dt.strftime("%Y-%m")

    grouped = df.groupby(["ticker", "year_month"]).agg(
        avg_close=("close", "mean"),
        min_close=("close", "min"),
        max_close=("close", "max"),
        total_volume=("volume", "sum"),
        volatility=("daily_return", "std"),
    ).reset_index()

    grouped["volatility"] = grouped["volatility"].fillna(0.0)
    return grouped


def build_latest_snapshot(silver_df: pd.DataFrame) -> pd.DataFrame:
    df = silver_df.sort_values("date")
    latest = df.groupby("ticker").tail(1).copy()
    prev = df.groupby("ticker").nth(-2) if len(df) > 1 else None

    latest["change_pct_1d"] = latest["daily_return"] * 100
    latest["updated_at"] = datetime.now(timezone.utc).isoformat()

    return latest.rename(columns={"date": "last_date", "close": "last_close"})[
        ["ticker", "last_date", "last_close", "change_pct_1d", "ma_7", "ma_30", "updated_at"]
    ]


def load_gold(monthly_df: pd.DataFrame, snapshot_df: pd.DataFrame) -> None:
    with get_connection() as conn:
        cur = conn.cursor()

        cur.executemany(
            """
            INSERT INTO gold_monthly_summary
                (ticker, year_month, avg_close, min_close, max_close, total_volume, volatility)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(ticker, year_month) DO UPDATE SET
                avg_close=excluded.avg_close, min_close=excluded.min_close,
                max_close=excluded.max_close, total_volume=excluded.total_volume,
                volatility=excluded.volatility
            """,
            [tuple(r) for r in monthly_df.itertuples(index=False, name=None)],
        )

        cur.executemany(
            """
            INSERT INTO gold_latest_snapshot
                (ticker, last_date, last_close, change_pct_1d, ma_7, ma_30, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(ticker) DO UPDATE SET
                last_date=excluded.last_date, last_close=excluded.last_close,
                change_pct_1d=excluded.change_pct_1d, ma_7=excluded.ma_7,
                ma_30=excluded.ma_30, updated_at=excluded.updated_at
            """,
            [tuple(r) for r in snapshot_df.itertuples(index=False, name=None)],
        )


def read_gold_monthly(ticker: str = None) -> pd.DataFrame:
    with get_connection() as conn:
        if ticker:
            return pd.read_sql_query(
                "SELECT * FROM gold_monthly_summary WHERE ticker = ? ORDER BY year_month",
                conn, params=(ticker,),
            )
        return pd.read_sql_query(
            "SELECT * FROM gold_monthly_summary ORDER BY ticker, year_month", conn
        )


def read_gold_snapshot() -> pd.DataFrame:
    with get_connection() as conn:
        return pd.read_sql_query("SELECT * FROM gold_latest_snapshot", conn)

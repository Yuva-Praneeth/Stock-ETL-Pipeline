"""
pipeline.py
Orchestrates the full medallion pipeline: API -> Bronze -> Silver -> Gold.
This is the single function the Streamlit app calls when the user hits
"Run Pipeline".
"""

from db import init_db
from api_client import fetch_price_history, APIFetchError
from etl import bronze, silver, gold


def run_pipeline(tickers: list[str], start_date: str, end_date: str) -> dict:
    """
    Run the full pipeline for a list of tickers.
    Returns a summary dict the UI can display, including any per-ticker errors.
    """
    init_db()

    summary = {"tickers_run": [], "errors": [], "rows": {}}

    for ticker in tickers:
        ticker = ticker.strip().upper()
        if not ticker:
            continue
        try:
            raw_df = fetch_price_history(ticker, start_date, end_date)
            n_bronze = bronze.load_bronze(ticker, raw_df)

            bronze_df = bronze.read_bronze(ticker)
            silver_df = silver.transform_to_silver(bronze_df)
            n_silver = silver.load_silver(silver_df)

            monthly_df = gold.build_monthly_summary(silver_df)
            snapshot_df = gold.build_latest_snapshot(silver_df)
            gold.load_gold(monthly_df, snapshot_df)

            summary["tickers_run"].append(ticker)
            summary["rows"][ticker] = {
                "bronze": n_bronze,
                "silver": n_silver,
                "gold_months": len(monthly_df),
            }

        except APIFetchError as e:
            summary["errors"].append(f"{ticker}: {e}")
        except Exception as e:  # pragma: no cover - safety net for the demo
            summary["errors"].append(f"{ticker}: unexpected error - {e}")

    return summary

# Stock Market ETL Pipeline — Medallion Architecture

A small, self-contained project showing an API → ETL (Bronze/Silver/Gold) →
SQLite → Streamlit pipeline, using Python .

## Architecture

```
Streamlit UI (app.py)
        │  user clicks "Run Pipeline"
        ▼
pipeline.py  ── orchestrates the run
        │
        ▼
api_client.py ── pulls raw OHLCV data from Alpha Vantage (TIME_SERIES_DAILY)
        │
        ▼
🥉 BRONZE  (etl/bronze.py)   raw data + ingestion metadata, no cleaning
        │
        ▼
🥈 SILVER  (etl/silver.py)   deduped, typed, + daily_return / MA7 / MA30
        │
        ▼
🥇 GOLD    (etl/gold.py)     monthly summary + latest snapshot (dashboard-ready)
        │
        ▼
SQLite (stocks.db) ── one file, one table per layer
        │
        ▼
Streamlit reads Gold + Silver back and renders the dashboard
```

## Files

| File | Purpose |
|---|---|
| `db.py` | SQLite connection + creates Bronze/Silver/Gold tables |
| `api_client.py` | Wraps the yfinance API call |
| `etl/bronze.py` | Raw ingestion layer |
| `etl/silver.py` | Cleaning + enrichment layer |
| `etl/gold.py` | Aggregation layer |
| `pipeline.py` | Orchestrates Bronze → Silver → Gold for a list of tickers |
| `app.py` | Streamlit UI — the only entry point you run |

## Setup

1. Copy `.env.example` to `.env` and paste in your Alpha Vantage key:
   ```
   ALPHAVANTAGE_API_KEY=your_real_key_here
   ```
   (`.env` is in `.gitignore` — your key never gets committed.)

2. Install and run:
   ```bash
   pip install -r requirements.txt
   streamlit run app.py
   ```

**Rate limits:** Alpha Vantage's free tier is limited (5 requests/min, 25/day
as of writing). `api_client.py` detects Alpha Vantage's rate-limit response
(it replies with HTTP 200 + a `"Note"`/`"Information"` field rather than an
error code), retries twice with a short backoff, then raises a clear error
if still limited. If you're demoing with several tickers back to back, add
a short pause between runs.

Then in the sidebar: enter one or more tickers (e.g. `AAPL, MSFT, TSLA`),
pick a date range, and click **Run ETL Pipeline**. Use the tabs to inspect
each medallion layer directly — Bronze shows the raw API rows, Silver shows
the cleaned/enriched rows, and Gold shows the aggregates and charts.


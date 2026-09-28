"""
app.py
Streamlit front-end. Lets the user pick tickers + a date range, trigger the
Bronze -> Silver -> Gold pipeline, then browse each layer and see charts
built from the Gold layer.
"""

from datetime import date, timedelta

import streamlit as st
import pandas as pd
from dotenv import load_dotenv

load_dotenv()  # reads ALPHAVANTAGE_API_KEY from a local .env file, if present

from db import init_db
from pipeline import run_pipeline
from etl import bronze, silver, gold

st.set_page_config(page_title="Stock ETL - Medallion Architecture", layout="wide")

init_db()

# ---------------------------------------------------------------- sidebar --
st.sidebar.title("⚙️ Pipeline Controls")

tickers_input = st.sidebar.text_input(
    "Ticker(s), comma-separated", value="AAPL, MSFT"
)

col1, col2 = st.sidebar.columns(2)
start_date = col1.date_input("Start date", value=date.today() - timedelta(days=180))
end_date = col2.date_input("End date", value=date.today())

run_clicked = st.sidebar.button("▶️ Run ETL Pipeline", use_container_width=True)

st.sidebar.markdown("---")
st.sidebar.caption(
    "Bronze → raw API data\n\nSilver → cleaned + enriched\n\nGold → aggregated for reporting"
)

# ---------------------------------------------------------------- header --
st.title("📊 Stock Market ETL Pipeline")
st.caption("API ingestion → Medallion architecture (Bronze / Silver / Gold) → SQLite → Streamlit")

if run_clicked:
    tickers = [t for t in tickers_input.split(",") if t.strip()]
    if not tickers:
        st.warning("Enter at least one ticker symbol.")
    else:
        with st.spinner("Running pipeline: fetching API data, then Bronze → Silver → Gold..."):
            result = run_pipeline(tickers, str(start_date), str(end_date))

        if result["tickers_run"]:
            st.success(f"Pipeline completed for: {', '.join(result['tickers_run'])}")
            with st.expander("Row counts per layer"):
                st.json(result["rows"])
        if result["errors"]:
            for err in result["errors"]:
                st.error(err)

# ---------------------------------------------------------------- tabs --
tab_gold, tab_silver, tab_bronze = st.tabs(["🥇 Gold (Dashboard)", "🥈 Silver", "🥉 Bronze (Raw)"])

with tab_gold:
    snapshot_df = gold.read_gold_snapshot()
    if snapshot_df.empty:
        st.info("No data yet — run the pipeline from the sidebar first.")
    else:
        st.subheader("Latest Snapshot")
        st.dataframe(snapshot_df, use_container_width=True, hide_index=True)

        st.subheader("Price History (from Silver)")
        all_silver = silver.read_silver()
        for ticker in sorted(all_silver["ticker"].unique()):
            t_df = all_silver[all_silver["ticker"] == ticker].set_index("date")
            st.markdown(f"**{ticker}**")
            st.line_chart(t_df[["close", "ma_7", "ma_30"]])

        st.subheader("Monthly Summary")
        monthly_df = gold.read_gold_monthly()
        st.dataframe(monthly_df, use_container_width=True, hide_index=True)

        for ticker in sorted(monthly_df["ticker"].unique()):
            t_monthly = monthly_df[monthly_df["ticker"] == ticker].set_index("year_month")
            st.markdown(f"**{ticker} — avg close by month**")
            st.bar_chart(t_monthly["avg_close"])

with tab_silver:
    silver_df = silver.read_silver()
    if silver_df.empty:
        st.info("No data yet — run the pipeline from the sidebar first.")
    else:
        st.dataframe(silver_df, use_container_width=True, hide_index=True)

with tab_bronze:
    bronze_df = bronze.read_bronze()
    if bronze_df.empty:
        st.info("No data yet — run the pipeline from the sidebar first.")
    else:
        st.dataframe(bronze_df, use_container_width=True, hide_index=True)

"""
api_client.py
Thin wrapper around the Alpha Vantage API. Keeping this isolated means the
rest of the pipeline never needs to know *where* the data came from -- the
function signature and returned DataFrame shape are the "contract" that
Bronze/Silver/Gold rely on, so swapping providers again later only means
rewriting this one file.
"""

import os
import time

import requests
import pandas as pd

ALPHA_VANTAGE_BASE_URL = "https://www.alphavantage.co/query"


class APIFetchError(Exception):
    """Raised when the external API returns no usable data, an error, or is rate-limited."""
    pass


def _get_api_key() -> str:
    """
    Read the Alpha Vantage API key from environment variable ALPHAVANTAGE_API_KEY
    (loaded from a .env file -- see .env.example). Never hard-code the key in source.
    """
    key = os.getenv("ALPHAVANTAGE_API_KEY")
    if not key:
        raise APIFetchError(
            "ALPHAVANTAGE_API_KEY is not set. Copy .env.example to .env and add your key, "
            "or set the environment variable directly."
        )
    return key


def fetch_price_history(
    ticker: str,
    start_date: str,
    end_date: str,
    max_retries: int = 3,
) -> pd.DataFrame:
    """
    Pull raw daily OHLCV data for one ticker from Alpha Vantage
    (TIME_SERIES_DAILY endpoint), filtered to [start_date, end_date].

    Returns a DataFrame with columns:
    ['date', 'open', 'high', 'low', 'close', 'volume']
    """
    api_key = _get_api_key()
    params = {
        "function": "TIME_SERIES_DAILY",
        "symbol": ticker,
        "outputsize": "compact",  # "full" so older start_dates aren't cut off at ~100 days
        "apikey": api_key,
        "datatype": "json",
    }

    payload = None
    for attempt in range(max_retries):
        response = requests.get(ALPHA_VANTAGE_BASE_URL, params=params, timeout=15)
        response.raise_for_status()
        payload = response.json()

        # Alpha Vantage doesn't use HTTP error codes for this -- it returns
        # 200 OK with an explanatory message instead.
        if "Note" in payload or "Information" in payload:
            # Typically a rate-limit message (free tier: 25 requests/day, 5/min)
            msg = payload.get("Note") or payload.get("Information")
            if attempt < max_retries - 1:
                time.sleep(15)  # back off and retry once or twice before giving up
                continue
            raise APIFetchError(f"Alpha Vantage rate limit / info message for '{ticker}': {msg}")

        break

    if payload is None:
        raise APIFetchError(f"No response received from Alpha Vantage for '{ticker}'.")

    if "Error Message" in payload:
        raise APIFetchError(
            f"Alpha Vantage error for '{ticker}': {payload['Error Message']} "
            "(check the ticker symbol is valid)"
        )

    series = payload.get("Time Series (Daily)")
    if not series:
        raise APIFetchError(
            f"No time series data returned for '{ticker}'. Raw response keys: {list(payload.keys())}"
        )

    df = pd.DataFrame.from_dict(series, orient="index")
    df.index.name = "date"
    df = df.reset_index()

    df = df.rename(columns={
        "1. open": "open",
        "2. high": "high",
        "3. low": "low",
        "4. close": "close",
        "5. volume": "volume",
    })

    for col in ["open", "high", "low", "close"]:
        df[col] = df[col].astype(float)
    df["volume"] = df["volume"].astype(int)

    df = df[(df["date"] >= start_date) & (df["date"] <= end_date)]
    df = df.sort_values("date").reset_index(drop=True)

    if df.empty:
        raise APIFetchError(
            f"'{ticker}' returned data, but none fell between {start_date} and {end_date}."
        )

    return df[["date", "open", "high", "low", "close", "volume"]]

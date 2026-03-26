from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd
import requests
import os

from src.utils.io import ensure_dir, write_json, write_parquet
from src.utils.time_utils import to_utc_timestamp

RAW_DIR = Path("data/raw/kalshi")
PROCESSED_PATH = Path("data/processed/kalshi_markets_current.parquet")
BASE_URL = os.getenv(
    "KALSHI_BASE_URL",
    "https://api.elections.kalshi.com/trade-api/v2/markets",
)


def fetch_current_markets(
    limit: int = 1000,
    max_pages: int = 5,
    max_markets: int = 5000,
) -> list[dict[str, Any]]:
    all_markets: list[dict[str, Any]] = []
    cursor = None
    page_count = 0

    while True:
        if page_count >= max_pages:
            break
        if len(all_markets) >= max_markets:
            break

        params = {
            "limit": limit,
            "status": "open",
        }
        if cursor:
            params["cursor"] = cursor

        try:
            resp = requests.get(BASE_URL, params=params, timeout=30)
            resp.raise_for_status()
        except requests.RequestException as exc:
            raise RuntimeError(f"Kalshi request failed for {BASE_URL}: {exc}") from exc
        data = resp.json()

        markets = data.get("markets", [])
        all_markets.extend(markets)
        page_count += 1

        if len(all_markets) >= max_markets:
            all_markets = all_markets[:max_markets]
            break

        cursor = data.get("cursor")
        if not cursor:
            break

    return all_markets


def _to_float_or_none(value):
    try:
        if value is None or value == "":
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def normalize_market(raw: dict[str, Any]) -> dict[str, Any]:
    yes_ask = raw.get("yes_ask")
    yes_bid = raw.get("yes_bid")
    no_ask = raw.get("no_ask")
    no_bid = raw.get("no_bid")

    # Fallback to Kalshi dollar-denominated fields if direct fields are absent
    if yes_ask is None:
        yes_ask = raw.get("yes_ask_dollars")
    if yes_bid is None:
        yes_bid = raw.get("yes_bid_dollars")
    if no_ask is None:
        no_ask = raw.get("no_ask_dollars")
    if no_bid is None:
        no_bid = raw.get("no_bid_dollars")

    return {
        "market_id": raw.get("ticker"),
        "ticker": raw.get("ticker"),
        "question": raw.get("title"),
        "subtitle": raw.get("subtitle"),
        "status": raw.get("status"),
        "yes_ask": _to_float_or_none(yes_ask),
        "yes_bid": _to_float_or_none(yes_bid),
        "no_ask": _to_float_or_none(no_ask),
        "no_bid": _to_float_or_none(no_bid),
        "volume": raw.get("volume"),
        "open_interest": raw.get("open_interest"),
        "close_time": raw.get("close_time"),
        "open_time": raw.get("open_time"),
        "result": raw.get("result"),
        "market_type": raw.get("market_type"),
        "event_ticker": raw.get("event_ticker"),
        "series_ticker": raw.get("series_ticker"),
        "strike_type": raw.get("strike_type"),
        "custom_strike": raw.get("custom_strike"),
        "liquidity": raw.get("liquidity"),
        "last_price": raw.get("last_price"),
        "raw_market": raw,
    }

def filter_candidate_markets(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()

    out["ticker"] = out["ticker"].astype(str)
    out["question"] = out["question"].astype(str)

    # keep rows with at least some live quote
    has_quotes = out[["yes_ask", "yes_bid", "no_ask", "no_bid"]].notna().any(axis=1)
    out = out[has_quotes].copy()

    # exclude obvious multivariate baskets
    out = out[~out["ticker"].str.startswith("KXMVE", na=False)].copy()

    # exclude rows with obviously bundled wording
    out = out[
        ~out["question"].str.contains(
            "wins by over|points scored|goals scored|yes .*?,yes |no .*?,no ",
            case=False,
            na=False,
        )
    ].copy()

    return out

def run_kalshi_current_ingestion(
    limit: int = 1000,
    max_pages: int = 5,
    max_markets: int = 5000,
) -> None:
    ensure_dir(RAW_DIR)
    ensure_dir(PROCESSED_PATH.parent)

    raw_markets = fetch_current_markets(
        limit=limit,
        max_pages=max_pages,
        max_markets=max_markets,
    )
    write_json(raw_markets, RAW_DIR / "current_markets.json")

    df = pd.DataFrame([normalize_market(m) for m in raw_markets])
    if "open_time" in df.columns:
        df["open_time"] = df["open_time"].apply(to_utc_timestamp)
    if "close_time" in df.columns:
        df["close_time"] = df["close_time"].apply(to_utc_timestamp)

    write_parquet(df, PROCESSED_PATH)

    print(f"[OK] Saved current Kalshi markets to {RAW_DIR / 'current_markets.json'}")
    print(f"[OK] Saved normalized parquet to {PROCESSED_PATH}")
    print(f"[INFO] Rows written: {len(df)}")


if __name__ == "__main__":
    run_kalshi_current_ingestion()
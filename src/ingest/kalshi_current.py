from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd
import requests

from src.utils.io import ensure_dir, write_json, write_parquet
from src.utils.time_utils import to_utc_timestamp

RAW_DIR = Path("data/raw/kalshi")
PROCESSED_PATH = Path("data/processed/kalshi_markets_current.parquet")
BASE_URL = "https://api.elections.kalshi.com/trade-api/v2/markets"


def fetch_current_markets(limit: int = 1000) -> list[dict[str, Any]]:
    all_markets: list[dict[str, Any]] = []
    cursor = None

    while True:
        params = {
            "limit": limit,
            "status": "open",
        }
        if cursor:
            params["cursor"] = cursor

        resp = requests.get(BASE_URL, params=params, timeout=30)
        resp.raise_for_status()
        data = resp.json()

        markets = data.get("markets", [])
        all_markets.extend(markets)

        cursor = data.get("cursor")
        if not cursor:
            break

    return all_markets


def normalize_market(raw: dict[str, Any]) -> dict[str, Any]:
    return {
        "market_id": raw.get("ticker"),
        "ticker": raw.get("ticker"),
        "question": raw.get("title"),
        "subtitle": raw.get("subtitle"),
        "status": raw.get("status"),
        "yes_ask": raw.get("yes_ask"),
        "yes_bid": raw.get("yes_bid"),
        "no_ask": raw.get("no_ask"),
        "no_bid": raw.get("no_bid"),
        "volume": raw.get("volume"),
        "open_interest": raw.get("open_interest"),
        "close_time": raw.get("close_time"),
        "open_time": raw.get("open_time"),
        "result": raw.get("result"),
        "raw_market": raw,
    }


def run_kalshi_current_ingestion() -> None:
    ensure_dir(RAW_DIR)
    ensure_dir(PROCESSED_PATH.parent)

    raw_markets = fetch_current_markets()
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
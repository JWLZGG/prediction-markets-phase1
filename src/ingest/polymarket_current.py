from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd
import requests

from src.utils.io import ensure_dir, write_json, write_parquet
from src.utils.time_utils import to_utc_timestamp

RAW_DIR = Path("data/raw/polymarket")
PROCESSED_PATH = Path("data/processed/polymarket_markets_current.parquet")

GAMMA_MARKETS_URL = "https://gamma-api.polymarket.com/markets"


def fetch_current_markets(limit: int = 500, offset: int = 0) -> list[dict[str, Any]]:
    params = {
        "limit": limit,
        "offset": offset,
        "active": "true",
        "closed": "false",
        "archived": "false",
    }

    response = requests.get(GAMMA_MARKETS_URL, params=params, timeout=30)
    response.raise_for_status()
    data = response.json()

    if not isinstance(data, list):
        raise ValueError("Expected list response from Polymarket Gamma API")

    return data


def normalize_market(raw: dict[str, Any]) -> dict[str, Any]:
    return {
        "market_id": raw.get("id"),
        "question": raw.get("question"),
        "description": raw.get("description"),
        "category": raw.get("category"),
        "active": raw.get("active"),
        "closed": raw.get("closed"),
        "archived": raw.get("archived"),
        "volume": raw.get("volume"),
        "liquidity": raw.get("liquidity"),
        "end_date": raw.get("endDate"),
        "created_at": raw.get("createdAt"),
        "outcomes": raw.get("outcomes"),
        "outcome_prices": raw.get("outcomePrices"),
        "raw_market": raw,
    }


def build_current_markets_dataframe(raw_markets: list[dict[str, Any]]) -> pd.DataFrame:
    df = pd.DataFrame([normalize_market(m) for m in raw_markets])

    if "created_at" in df.columns:
        df["created_at"] = df["created_at"].apply(to_utc_timestamp)
    if "end_date" in df.columns:
        df["end_date"] = df["end_date"].apply(to_utc_timestamp)

    return df


def run_polymarket_current_ingestion(limit: int = 500, offset: int = 0) -> None:
    ensure_dir(RAW_DIR)
    ensure_dir(PROCESSED_PATH.parent)

    raw_markets = fetch_current_markets(limit=limit, offset=offset)
    write_json(raw_markets, RAW_DIR / "current_markets.json")

    df = build_current_markets_dataframe(raw_markets)
    write_parquet(df, PROCESSED_PATH)

    print(f"[OK] Saved current Polymarket markets to {RAW_DIR / 'current_markets.json'}")
    print(f"[OK] Saved normalized parquet to {PROCESSED_PATH}")
    print(f"[INFO] Rows written: {len(df)}")


if __name__ == "__main__":
    run_polymarket_current_ingestion()
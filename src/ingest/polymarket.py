from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd
import requests

from src.utils.io import ensure_dir, write_json, write_parquet
from src.utils.time_utils import to_utc_timestamp

RAW_DIR = Path("data/raw/polymarket")
PROCESSED_PATH = Path("data/processed/polymarket_markets_raw.parquet")

GAMMA_MARKETS_URL = "https://gamma-api.polymarket.com/markets"


def fetch_markets(
    limit: int = 200,
    closed: bool = True,
    extra_params: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """
    Fetch markets from the Polymarket Gamma API.
    """
    params: dict[str, Any] = {
        "limit": limit,
        "closed": str(closed).lower(),
    }

    if extra_params:
        params.update(extra_params)

    response = requests.get(GAMMA_MARKETS_URL, params=params, timeout=30)
    response.raise_for_status()
    data = response.json()

    if not isinstance(data, list):
        raise ValueError(f"Expected list response from Polymarket Gamma API, got: {type(data)}")

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


def build_raw_markets_dataframe(raw_markets: list[dict[str, Any]]) -> pd.DataFrame:
    records = [normalize_market(m) for m in raw_markets]
    df = pd.DataFrame(records)

    if "created_at" in df.columns:
        df["created_at"] = df["created_at"].apply(to_utc_timestamp)
    if "end_date" in df.columns:
        df["end_date"] = df["end_date"].apply(to_utc_timestamp)

    return df


def save_probe(name: str, raw_markets: list[dict[str, Any]]) -> None:
    """
    Save a raw probe response so we can compare which query shapes return newer markets.
    """
    ensure_dir(RAW_DIR)
    path = RAW_DIR / f"{name}.json"
    write_json(raw_markets, path)
    print(f"[OK] Saved probe response to {path}")


def run_polymarket_ingestion(
    limit: int = 200,
    offset: int = 0,
    output_name: str = "polymarket_markets_raw.parquet",
    raw_name: str = "resolved_markets.json",
) -> None:
    """
    End-to-end ingestion:
    1. fetch raw markets
    2. save raw json
    3. normalize and save parquet
    """
    ensure_dir(RAW_DIR)
    ensure_dir(Path("data/processed"))

    raw_markets = fetch_markets(
        limit=limit,
        closed=True,
        extra_params={"offset": offset},
    )
    write_json(raw_markets, RAW_DIR / raw_name)

    df = build_raw_markets_dataframe(raw_markets)
    output_path = Path("data/processed") / output_name
    write_parquet(df, output_path)

    print(f"[OK] Saved raw Polymarket markets to {RAW_DIR / raw_name}")
    print(f"[OK] Saved normalized parquet to {output_path}")
    print(f"[INFO] Rows written: {len(df)}")
    if "end_date" in df.columns:
        print(f"[INFO] max end_date: {df['end_date'].max()}")
        print(f"[INFO] min end_date: {df['end_date'].min()}")


if __name__ == "__main__":
    run_polymarket_ingestion()
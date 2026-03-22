from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd
import requests

from src.utils.io import ensure_dir, write_json, write_parquet

MARKETS_PATH = Path("data/processed/polymarket_markets_current.parquet")
RAW_DIR = Path("data/raw/polymarket_orderbooks")
PROCESSED_PATH = Path("data/processed/polymarket_orderbooks_current.parquet")

# Polymarket CLOB endpoint
CLOB_BOOK_URL = "https://clob.polymarket.com/book"


def _parse_raw_market(raw_market: Any) -> dict[str, Any]:
    if isinstance(raw_market, dict):
        return raw_market
    if isinstance(raw_market, str):
        text = raw_market.strip()
        if not text:
            return {}
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return {}
    return {}


def _parse_token_ids(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(x) for x in value]
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return []
        try:
            parsed = json.loads(text)
            if isinstance(parsed, list):
                return [str(x) for x in parsed]
        except json.JSONDecodeError:
            return []
    return []


def fetch_orderbook(token_id: str) -> dict[str, Any]:
    response = requests.get(
        CLOB_BOOK_URL,
        params={"token_id": token_id},
        timeout=30,
    )
    response.raise_for_status()
    return response.json()


def _normalize_side(levels: Any) -> list[dict[str, float]]:
    if not isinstance(levels, list):
        return []

    normalized: list[dict[str, float]] = []
    for level in levels:
        if not isinstance(level, dict):
            continue

        price = level.get("price")
        size = level.get("size")

        try:
            price_f = float(price)
            size_f = float(size)
        except (TypeError, ValueError):
            continue

        if size_f <= 0:
            continue

        normalized.append({
            "price": price_f,
            "size": size_f,
        })

    return normalized


def normalize_orderbook(
    market_id: str,
    question: str | None,
    token_id: str,
    token_side: str,
    raw_book: dict[str, Any],
) -> dict[str, Any]:
    bids = _normalize_side(raw_book.get("bids"))
    asks = _normalize_side(raw_book.get("asks"))

    return {
        "market_id": market_id,
        "question": question,
        "token_id": token_id,
        "token_side": token_side,
        "bids": bids,
        "asks": asks,
        "raw_book": raw_book,
    }


def run_polymarket_orderbook_ingestion(limit_markets: int | None = 100) -> None:
    ensure_dir(RAW_DIR)
    ensure_dir(PROCESSED_PATH.parent)

    markets_df = pd.read_parquet(MARKETS_PATH).copy()
    if limit_markets is not None:
        markets_df = markets_df.head(limit_markets).copy()

    rows: list[dict[str, Any]] = []
    raw_books: list[dict[str, Any]] = []

    for _, row in markets_df.iterrows():
        raw_market = _parse_raw_market(row.get("raw_market"))
        token_ids = _parse_token_ids(raw_market.get("clobTokenIds"))

        # For binary markets we expect 2 token IDs: Yes, No
        if len(token_ids) != 2:
            continue

        market_id = str(row.get("market_id"))
        question = row.get("question")

        token_side_map = {
            "yes": token_ids[0],
            "no": token_ids[1],
        }

        for token_side, token_id in token_side_map.items():
            try:
                raw_book = fetch_orderbook(token_id)
            except Exception as exc:
                raw_books.append({
                    "market_id": market_id,
                    "question": question,
                    "token_id": token_id,
                    "token_side": token_side,
                    "error": str(exc),
                })
                continue

            raw_books.append({
                "market_id": market_id,
                "question": question,
                "token_id": token_id,
                "token_side": token_side,
                "raw_book": raw_book,
            })

            rows.append(
                normalize_orderbook(
                    market_id=market_id,
                    question=question,
                    token_id=token_id,
                    token_side=token_side,
                    raw_book=raw_book,
                )
            )

    write_json(raw_books, RAW_DIR / "current_orderbooks.json")

    df = pd.DataFrame(rows)
    write_parquet(df, PROCESSED_PATH)

    print(f"[OK] Saved raw orderbook payloads to {RAW_DIR / 'current_orderbooks.json'}")
    print(f"[OK] Saved normalized parquet to {PROCESSED_PATH}")
    print(f"[INFO] Rows written: {len(df)}")


if __name__ == "__main__":
    run_polymarket_orderbook_ingestion()
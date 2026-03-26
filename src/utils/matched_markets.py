from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


MATCHED_PREDICTION_MARKETS_PATH = Path("configs/matched_prediction_markets.yaml")


def load_matched_prediction_pairs(
    path: Path = MATCHED_PREDICTION_MARKETS_PATH,
) -> list[dict[str, Any]]:
    if not path.exists():
        raise FileNotFoundError(f"Matched market config not found: {path}")

    with path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    pairs = data.get("pairs", [])
    if not isinstance(pairs, list):
        raise ValueError("Expected 'pairs' to be a list")

    seen_pair_ids: set[str] = set()
    normalized: list[dict[str, Any]] = []

    for pair in pairs:
        if not isinstance(pair, dict):
            raise ValueError("Each pair entry must be a dict")

        pair_id = str(pair.get("pair_id", "")).strip()
        label = str(pair.get("label", "")).strip()

        polymarket = pair.get("polymarket")
        kalshi = pair.get("kalshi")

        if not pair_id:
            raise ValueError("Each pair must have a non-empty pair_id")
        if pair_id in seen_pair_ids:
            raise ValueError(f"Duplicate pair_id found: {pair_id}")
        seen_pair_ids.add(pair_id)

        if not label:
            raise ValueError(f"Pair {pair_id} is missing label")

        if not isinstance(polymarket, dict):
            raise ValueError(f"Pair {pair_id} has invalid polymarket config")
        if not isinstance(kalshi, dict):
            raise ValueError(f"Pair {pair_id} has invalid kalshi config")

        polymarket_market_id = str(polymarket.get("market_id", "")).strip()
        polymarket_side = str(polymarket.get("side", "")).strip().lower()

        kalshi_ticker = str(kalshi.get("ticker", "")).strip()
        kalshi_side = str(kalshi.get("side", "")).strip().lower()

        if not polymarket_market_id:
            raise ValueError(f"Pair {pair_id} missing polymarket.market_id")
        if polymarket_side not in {"yes", "no"}:
            raise ValueError(f"Pair {pair_id} invalid polymarket.side: {polymarket_side}")

        if not kalshi_ticker:
            raise ValueError(f"Pair {pair_id} missing kalshi.ticker")
        if kalshi_side not in {"yes", "no"}:
            raise ValueError(f"Pair {pair_id} invalid kalshi.side: {kalshi_side}")

        normalized.append(
            {
                "pair_id": pair_id,
                "label": label,
                "polymarket": {
                    "market_id": polymarket_market_id,
                    "side": polymarket_side,
                },
                "kalshi": {
                    "ticker": kalshi_ticker,
                    "side": kalshi_side,
                },
            }
        )

    return normalized
from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from src.detect.edge import compute_cross_venue_edge
from src.detect.executable_pricing import walk_book
from src.utils.matched_markets import (
    MATCHED_PREDICTION_MARKETS_PATH,
    load_matched_prediction_pairs,
)


POLYMARKET_ORDERBOOKS_PATH = Path("data/processed/polymarket_orderbooks_current.parquet")
KALSHI_CURRENT_PATH = Path("data/processed/kalshi_markets_current.parquet")


def _r(x: float, ndigits: int = 6) -> float:
    return round(float(x), ndigits)


def _normalize_levels(levels: Any) -> list[dict[str, float]]:
    if levels is None:
        return []

    if hasattr(levels, "tolist") and not isinstance(levels, list):
        try:
            levels = levels.tolist()
        except Exception:
            return []

    if not isinstance(levels, list):
        return []

    out: list[dict[str, float]] = []
    for level in levels:
        if hasattr(level, "as_py"):
            try:
                level = level.as_py()
            except Exception:
                continue

        if not isinstance(level, dict):
            if hasattr(level, "items"):
                try:
                    level = dict(level.items())
                except Exception:
                    continue
            else:
                continue

        try:
            price = float(level["price"])
            size = float(level["size"])
        except (KeyError, TypeError, ValueError):
            continue

        if size <= 0:
            continue

        out.append({"price": price, "size": size})

    return out


def load_polymarket_orderbooks(path: Path = POLYMARKET_ORDERBOOKS_PATH) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame(columns=["market_id", "question", "token_id", "token_side", "bids", "asks"])
    return pd.read_parquet(path).copy()


def load_kalshi_current(path: Path = KALSHI_CURRENT_PATH) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame(columns=["ticker", "question", "yes_ask", "yes_bid", "no_ask", "no_bid", "raw_market"])
    return pd.read_parquet(path).copy()


def extract_polymarket_side_books(
    df: pd.DataFrame,
    market_id: str,
    side: str,
) -> dict[str, Any] | None:
    subset = df[df["market_id"].astype(str) == str(market_id)].copy()
    if subset.empty:
        return None

    token_rows = subset[subset["token_side"].astype(str).str.strip().str.lower() == side]
    if token_rows.empty:
        return None

    row = token_rows.iloc[0]
    asks = _normalize_levels(row.get("asks"))
    bids = _normalize_levels(row.get("bids"))

    if not asks and not bids:
        return None

    return {
        "venue": "polymarket",
        "market_id": str(row.get("market_id")),
        "question": row.get("question"),
        "side": side,
        "asks": asks,
        "bids": bids,
    }


def extract_kalshi_side_books(
    df: pd.DataFrame,
    ticker: str,
    side: str,
) -> dict[str, Any] | None:
    subset = df[df["ticker"].astype(str) == str(ticker)].copy()
    if subset.empty:
        return None

    row = subset.iloc[0]

    if side == "yes":
        ask = row.get("yes_ask")
        bid = row.get("yes_bid")
    else:
        ask = row.get("no_ask")
        bid = row.get("no_bid")

    try:
        ask_f = float(ask) if ask is not None else None
    except (TypeError, ValueError):
        ask_f = None

    try:
        bid_f = float(bid) if bid is not None else None
    except (TypeError, ValueError):
        bid_f = None

    asks: list[dict[str, float]] = []
    bids: list[dict[str, float]] = []

    # v1: top-of-book only, synthetic size 100 if quote exists
    if ask_f is not None and 0 < ask_f < 1:
        asks = [{"price": ask_f, "size": 100.0}]
    if bid_f is not None and 0 < bid_f < 1:
        bids = [{"price": bid_f, "size": 100.0}]

    if not asks and not bids:
        return None

    return {
        "venue": "kalshi",
        "ticker": str(row.get("ticker")),
        "question": row.get("question"),
        "side": side,
        "asks": asks,
        "bids": bids,
    }


def scan_matched_crossvenue_pairs(
    matched_config_path: Path = MATCHED_PREDICTION_MARKETS_PATH,
    polymarket_orderbooks_path: Path = POLYMARKET_ORDERBOOKS_PATH,
    kalshi_current_path: Path = KALSHI_CURRENT_PATH,
    target_size: float = 100.0,
    threshold_bps: float = 100.0,
    fee_config: dict[str, Any] | None = None,
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    if fee_config is None:
        fee_config = {
            "venues": {
                "polymarket": {
                    "taker_fee_bps": 0,
                    "slippage_buffer_bps": 10,
                    "fixed_buffer": 0.0,
                },
                "kalshi": {
                    "taker_fee_bps": 25,
                    "slippage_buffer_bps": 50,
                    "fixed_buffer": 0.0,
                },
            }
        }

    matched_pairs = load_matched_prediction_pairs(matched_config_path)
    poly_df = load_polymarket_orderbooks(polymarket_orderbooks_path)
    kalshi_df = load_kalshi_current(kalshi_current_path)

    stats = {
        "pairs_total": len(matched_pairs),
        "pairs_found_on_both_venues": 0,
        "pairs_with_usable_buy_sell_paths": 0,
        "flags_emitted": 0,
    }

    flags: list[dict[str, Any]] = []

    for pair in matched_pairs:
        pair_id = pair["pair_id"]
        label = pair["label"]

        poly = extract_polymarket_side_books(
            poly_df,
            market_id=pair["polymarket"]["market_id"],
            side=pair["polymarket"]["side"],
        )
        kalshi = extract_kalshi_side_books(
            kalshi_df,
            ticker=pair["kalshi"]["ticker"],
            side=pair["kalshi"]["side"],
        )

        if poly is None or kalshi is None:
            continue

        stats["pairs_found_on_both_venues"] += 1

        usable_paths = 0

        directions = [
            {
                "buy_venue": "polymarket",
                "sell_venue": "kalshi",
                "buy_book": poly["asks"],
                "sell_book": kalshi["bids"],
            },
            {
                "buy_venue": "kalshi",
                "sell_venue": "polymarket",
                "buy_book": kalshi["asks"],
                "sell_book": poly["bids"],
            },
        ]

        for direction in directions:
            buy_book = direction["buy_book"]
            sell_book = direction["sell_book"]

            if not buy_book or not sell_book:
                continue

            buy_result = walk_book(buy_book, target_size=target_size, side="buy")
            sell_result = walk_book(sell_book, target_size=target_size, side="sell")

            if not buy_result.executable or not sell_result.executable:
                continue

            usable_paths += 1

            edge_result = compute_cross_venue_edge(
                buy_avg_price=buy_result.avg_price,
                sell_avg_price=sell_result.avg_price,
                total_cost=0.0,  # keep v1 simple; venue-cost layering can be added next
                target_size=target_size,
                threshold_bps=threshold_bps,
            )

            if not edge_result.should_flag:
                continue

            flags.append(
                {
                    "flag_type": "cross_venue_divergence",
                    "pair_id": pair_id,
                    "label": label,
                    "polymarket_market_id": pair["polymarket"]["market_id"],
                    "kalshi_ticker": pair["kalshi"]["ticker"],
                    "buy_venue": direction["buy_venue"],
                    "sell_venue": direction["sell_venue"],
                    "target_size": target_size,
                    "details": {
                        "buy_avg_price": _r(buy_result.avg_price, 6),
                        "sell_avg_price": _r(sell_result.avg_price, 6),
                        "buy_levels_used": buy_result.levels_used,
                        "sell_levels_used": sell_result.levels_used,
                        "gross_edge": _r(edge_result.gross_edge, 6),
                        "total_cost": _r(edge_result.total_cost, 6),
                        "net_edge": _r(edge_result.net_edge, 6),
                        "net_edge_bps": _r(edge_result.net_edge_bps, 2),
                        "should_flag": edge_result.should_flag,
                    },
                }
            )

        if usable_paths > 0:
            stats["pairs_with_usable_buy_sell_paths"] += 1

    stats["flags_emitted"] = len(flags)
    return flags, stats


if __name__ == "__main__":
    flags, stats = scan_matched_crossvenue_pairs()
    print("[INFO] Matched cross-venue scan stats:")
    print(stats)
    print("\n[INFO] Sample flags:")
    for flag in flags[:10]:
        print(flag)
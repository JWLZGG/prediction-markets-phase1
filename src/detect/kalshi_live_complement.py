from __future__ import annotations

import json
import ast
from pathlib import Path
from typing import Any

import pandas as pd

from src.detect.scanner_core import flag_to_dict, scan_complement_market

KALSHI_CURRENT_PATH = Path("data/processed/kalshi_markets_current.parquet")


def _to_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        if isinstance(value, str) and value.strip() == "":
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


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
            pass

        try:
            parsed = ast.literal_eval(text)
            if isinstance(parsed, dict):
                return parsed
        except (ValueError, SyntaxError):
            pass

    return {}


def load_kalshi_current_markets(path: Path = KALSHI_CURRENT_PATH) -> pd.DataFrame:
    return pd.read_parquet(path).copy()

def inspect_kalshi_row(row: pd.Series) -> dict[str, Any]:
    raw = _parse_raw_market(row.get("raw_market"))

    status = str(row.get("status", "")).lower()
    market_type = str(raw.get("market_type", "")).lower()

    is_active = status == "active"
    is_binary = market_type == "binary"

    # Direct fields
    yes_ask = _to_float(row.get("yes_ask"))
    no_ask = _to_float(row.get("no_ask"))
    yes_bid = _to_float(row.get("yes_bid"))
    no_bid = _to_float(row.get("no_bid"))

    # Raw fallbacks
    if yes_ask is None:
        yes_ask = _to_float(raw.get("yes_ask_dollars"))
    if no_ask is None:
        no_ask = _to_float(raw.get("no_ask_dollars"))
    if yes_bid is None:
        yes_bid = _to_float(raw.get("yes_bid_dollars"))
    if no_bid is None:
        no_bid = _to_float(raw.get("no_bid_dollars"))

    yes_ask_size = _to_float(raw.get("yes_ask_size_fp"))
    no_ask_size = _to_float(raw.get("no_ask_size_fp"))
    yes_bid_size = _to_float(raw.get("yes_bid_size_fp"))
    no_bid_size = _to_float(raw.get("no_bid_size_fp"))

    usable_yes_direct = (
        yes_ask is not None and yes_ask_size is not None and yes_ask_size > 0 and 0 < yes_ask < 1
    )
    usable_yes_derived = (
        no_bid is not None and no_bid_size is not None and no_bid_size > 0 and 0 <= no_bid < 1
    )
    usable_no_direct = (
        no_ask is not None and no_ask_size is not None and no_ask_size > 0 and 0 < no_ask < 1
    )
    usable_no_derived = (
        yes_bid is not None and yes_bid_size is not None and yes_bid_size > 0 and 0 <= yes_bid < 1
    )

    usable_yes_side = usable_yes_direct or usable_yes_derived
    usable_no_side = usable_no_direct or usable_no_derived

    return {
        "is_active": is_active,
        "is_binary": is_binary,
        "usable_yes_side": usable_yes_side,
        "usable_no_side": usable_no_side,
        "usable_yes_direct": usable_yes_direct,
        "usable_yes_derived": usable_yes_derived,
        "usable_no_direct": usable_no_direct,
        "usable_no_derived": usable_no_derived,
    }

def extract_kalshi_top_book(row: pd.Series) -> dict[str, Any] | None:
    raw = _parse_raw_market(row.get("raw_market"))

    market_type = raw.get("market_type")
    if market_type is not None and str(market_type).lower() != "binary":
        return None

    status = row.get("status")
    if status is None or str(status).lower() != "active":
        return None

    # Direct fields from flattened columns if present
    yes_ask = _to_float(row.get("yes_ask"))
    no_ask = _to_float(row.get("no_ask"))
    yes_bid = _to_float(row.get("yes_bid"))
    no_bid = _to_float(row.get("no_bid"))

    # Fallback to raw market
    if yes_ask is None:
        yes_ask = _to_float(raw.get("yes_ask_dollars"))
    if no_ask is None:
        no_ask = _to_float(raw.get("no_ask_dollars"))
    if yes_bid is None:
        yes_bid = _to_float(raw.get("yes_bid_dollars"))
    if no_bid is None:
        no_bid = _to_float(raw.get("no_bid_dollars"))

    yes_ask_size = _to_float(raw.get("yes_ask_size_fp"))
    no_ask_size = _to_float(raw.get("no_ask_size_fp"))
    yes_bid_size = _to_float(raw.get("yes_bid_size_fp"))
    no_bid_size = _to_float(raw.get("no_bid_size_fp"))

    # Build executable YES ask
    yes_ask_price = None
    yes_ask_executable_size = None

    if yes_ask is not None and yes_ask_size is not None and yes_ask_size > 0 and 0 < yes_ask < 1:
        yes_ask_price = yes_ask
        yes_ask_executable_size = yes_ask_size
    elif no_bid is not None and no_bid_size is not None and no_bid_size > 0 and 0 <= no_bid < 1:
        # Complementary synthetic YES ask from NO bid
        yes_ask_price = 1.0 - no_bid
        yes_ask_executable_size = no_bid_size

    # Build executable NO ask
    no_ask_price = None
    no_ask_executable_size = None

    if no_ask is not None and no_ask_size is not None and no_ask_size > 0 and 0 < no_ask < 1:
        no_ask_price = no_ask
        no_ask_executable_size = no_ask_size
    elif yes_bid is not None and yes_bid_size is not None and yes_bid_size > 0 and 0 <= yes_bid < 1:
        # Complementary synthetic NO ask from YES bid
        no_ask_price = 1.0 - yes_bid
        no_ask_executable_size = yes_bid_size

    if yes_ask_price is None or no_ask_price is None:
        return None
    if yes_ask_executable_size is None or no_ask_executable_size is None:
        return None
    if yes_ask_executable_size <= 0 or no_ask_executable_size <= 0:
        return None

    market_id = row.get("market_id")
    ticker = row.get("ticker")
    question = row.get("question")

    return {
        "market_id": str(market_id),
        "ticker": str(ticker) if ticker is not None else None,
        "question": str(question) if question is not None else None,
        "yes_asks": [{"price": yes_ask_price, "size": yes_ask_executable_size}],
        "no_asks": [{"price": no_ask_price, "size": no_ask_executable_size}],
    }


def scan_kalshi_complements(
    path: Path = KALSHI_CURRENT_PATH,
    target_size: float = 100.0,
    fee_config: dict | None = None,
    threshold_bps: float = 100.0,
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    if fee_config is None:
        fee_config = {
            "venues": {
                "kalshi": {
                    "taker_fee_bps": 25,
                    "slippage_buffer_bps": 10,
                    "fixed_buffer": 0.0,
                }
            }
        }

    df = load_kalshi_current_markets(path)

    stats = {
        "rows_total": int(len(df)),
        "active_rows": 0,
        "active_binary_rows": 0,
        "usable_yes_side": 0,
        "usable_no_side": 0,
        "usable_both_sides": 0,
        "usable_yes_direct": 0,
        "usable_yes_derived": 0,
        "usable_no_direct": 0,
        "usable_no_derived": 0,
        "eligible_top_book": 0,
        "sufficient_size": 0,
        "flags_emitted": 0,
    }

    flags: list[dict[str, Any]] = []

    for _, row in df.iterrows():
        inspection = inspect_kalshi_row(row)

        if inspection["is_active"]:
            stats["active_rows"] += 1

        if inspection["is_active"] and inspection["is_binary"]:
            stats["active_binary_rows"] += 1

        if inspection["usable_yes_side"]:
            stats["usable_yes_side"] += 1

        if inspection["usable_no_side"]:
            stats["usable_no_side"] += 1

        if inspection["usable_yes_side"] and inspection["usable_no_side"]:
            stats["usable_both_sides"] += 1

        if inspection["usable_yes_direct"]:
            stats["usable_yes_direct"] += 1

        if inspection["usable_yes_derived"]:
            stats["usable_yes_derived"] += 1

        if inspection["usable_no_direct"]:
            stats["usable_no_direct"] += 1

        if inspection["usable_no_derived"]:
            stats["usable_no_derived"] += 1

        top_book = extract_kalshi_top_book(row)
        if top_book is None:
            continue

        stats["eligible_top_book"] += 1

        yes_size = float(top_book["yes_asks"][0]["size"])
        no_size = float(top_book["no_asks"][0]["size"])

        if yes_size < target_size or no_size < target_size:
            continue

        stats["sufficient_size"] += 1

        flag = scan_complement_market(
            market_id=top_book["market_id"],
            venue="kalshi",
            yes_asks=top_book["yes_asks"],
            no_asks=top_book["no_asks"],
            target_size=target_size,
            fee_config=fee_config,
            threshold_bps=threshold_bps,
        )

        if flag is not None:
            flag_dict = flag_to_dict(flag)
            flag_dict["ticker"] = top_book["ticker"]
            flag_dict["question"] = top_book["question"]
            flags.append(flag_dict)

    stats["flags_emitted"] = len(flags)
    return flags, stats


if __name__ == "__main__":
    flags, stats = scan_kalshi_complements()
    print("[INFO] Kalshi live complement scan stats:")
    print(stats)
    print("\n[INFO] Sample flags:")
    for flag in flags[:10]:
        print(flag)
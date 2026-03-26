from __future__ import annotations

import ast                    
import json
from pathlib import Path
from typing import Any

import pandas as pd

from src.detect.executable_pricing import get_executable_buy_price
from src.detect.scanner_core import flag_to_dict, scan_complement_market
from src.config.scanner_fee_config import get_default_fee_config

POLYMARKET_ORDERBOOKS_PATH = Path("data/processed/polymarket_orderbooks_current.parquet")


EXPECTED_COLUMNS = [
    "market_id",
    "question",
    "token_id",
    "token_side",
    "bids",
    "asks",
    "raw_book",
]

def load_polymarket_orderbooks(path: Path = POLYMARKET_ORDERBOOKS_PATH) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame(columns=EXPECTED_COLUMNS)

    df = pd.read_parquet(path).copy()

    for col in EXPECTED_COLUMNS:
        if col not in df.columns:
            df[col] = None

    return df[EXPECTED_COLUMNS].copy()


def _normalize_levels(levels: Any) -> list[dict[str, float]]:
    if levels is None:
        return []

    # String-encoded JSON or Python literal
    if isinstance(levels, str):
        text = levels.strip()
        if not text:
            return []
        try:
            levels = json.loads(text)
        except json.JSONDecodeError:
            try:
                levels = ast.literal_eval(text)
            except (ValueError, SyntaxError):
                return []

    # Handle numpy/pandas/pyarrow-ish containers
    if not isinstance(levels, list):
        if hasattr(levels, "tolist"):
            try:
                levels = levels.tolist()
            except Exception:
                pass

    if not isinstance(levels, list):
        if isinstance(levels, tuple):
            levels = list(levels)
        else:
            return []

    out: list[dict[str, float]] = []

    for level in levels:
        # pyarrow scalar -> python object
        if hasattr(level, "as_py"):
            try:
                level = level.as_py()
            except Exception:
                continue

        # numpy void / struct-ish row -> dict
        if not isinstance(level, dict):
            if hasattr(level, "items"):
                try:
                    level = dict(level.items())
                except Exception:
                    pass
            elif hasattr(level, "tolist"):
                try:
                    maybe = level.tolist()
                    if isinstance(maybe, dict):
                        level = maybe
                except Exception:
                    pass

        if not isinstance(level, dict):
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


def pair_market_books(df: pd.DataFrame) -> list[dict[str, Any]]:
    if df.empty:
        return []

    required = {"market_id", "token_side", "token_id", "question", "asks"}
    if not required.issubset(df.columns):
        return []

    paired: list[dict[str, Any]] = []

    grouped = df.groupby("market_id", dropna=False)

    for market_id, group in grouped:
        if len(group) < 2:
            continue

        yes_rows = group[group["token_side"] == "yes"]
        no_rows = group[group["token_side"] == "no"]

        if yes_rows.empty or no_rows.empty:
            continue

        yes_row = yes_rows.iloc[0]
        no_row = no_rows.iloc[0]

        yes_asks = _normalize_levels(yes_row.get("asks"))
        no_asks = _normalize_levels(no_row.get("asks"))

        paired.append(
            {
                "market_id": str(market_id),
                "question": yes_row.get("question"),
                "yes_token_id": yes_row.get("token_id"),
                "no_token_id": no_row.get("token_id"),
                "yes_asks": yes_asks,
                "no_asks": no_asks,
            }
        )

    return paired


def scan_polymarket_complements(
    path: Path = POLYMARKET_ORDERBOOKS_PATH,
    target_size: float = 100.0,
    fee_config: dict | None = None,
    threshold_bps: float = 100.0,
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    if fee_config is None:
        fee_config = get_default_fee_config()

    df = load_polymarket_orderbooks(path)
    paired_books = pair_market_books(df)

    stats = {
        "rows_total": int(len(df)),
        "paired_markets": 0,
        "markets_with_yes_asks": 0,
        "markets_with_no_asks": 0,
        "markets_with_both_asks": 0,
        "sufficient_size": 0,
        "flags_emitted": 0,
    }

    flags: list[dict[str, Any]] = []

    for market in paired_books:
        stats["paired_markets"] += 1

        has_yes = len(market["yes_asks"]) > 0
        has_no = len(market["no_asks"]) > 0

        if has_yes:
            stats["markets_with_yes_asks"] += 1
        if has_no:
            stats["markets_with_no_asks"] += 1
        if has_yes and has_no:
            stats["markets_with_both_asks"] += 1

        if not has_yes or not has_no:
            continue

        yes_execution = get_executable_buy_price(market["yes_asks"], target_size=target_size)
        no_execution = get_executable_buy_price(market["no_asks"], target_size=target_size)

        if not yes_execution.executable or not no_execution.executable:
            continue

        stats["sufficient_size"] += 1

        flag = scan_complement_market(
            market_id=market["market_id"],
            venue="polymarket",
            yes_asks=market["yes_asks"],
            no_asks=market["no_asks"],
            target_size=target_size,
            fee_config=fee_config,
            threshold_bps=threshold_bps,
        )

        if flag is not None:
            flag_dict = flag_to_dict(flag)
            flag_dict["question"] = market["question"]
            flag_dict["yes_token_id"] = market["yes_token_id"]
            flag_dict["no_token_id"] = market["no_token_id"]
            flags.append(flag_dict)

    stats["flags_emitted"] = len(flags)
    return flags, stats


if __name__ == "__main__":
    flags, stats = scan_polymarket_complements(target_size=100.0, threshold_bps=100.0)
    print("[INFO] Polymarket live complement scan stats:")
    print(stats)
    print("\n[INFO] Sample flags:")
    for flag in flags[:10]:
        print(flag)

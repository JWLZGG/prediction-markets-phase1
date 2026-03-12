from __future__ import annotations

from pathlib import Path
import json

import pandas as pd

from src.utils.io import read_parquet, write_parquet
from src.utils.time_utils import to_utc_timestamp

RAW_INPUT = Path("data/processed/polymarket_markets_raw.parquet")
OUTPUT = Path("data/processed/markets.parquet")


def parse_json_list(value):
    if value is None:
        return None

    if isinstance(value, list):
        return value

    if isinstance(value, str):
        try:
            return json.loads(value)
        except Exception:
            return None

    return None


def classify_terminal_prices(prices, eps: float = 1e-3) -> str:
    if prices is None:
        return "invalid"

    try:
        vals = [float(p) for p in prices]
    except Exception:
        return "invalid"

    if len(vals) != 2:
        return "invalid"

    if abs(vals[0] - 1.0) < eps and abs(vals[1] - 0.0) < eps:
        return "yes_won"

    if abs(vals[0] - 0.0) < eps and abs(vals[1] - 1.0) < eps:
        return "no_won"

    if vals[0] == 0.0 and vals[1] == 0.0:
        return "double_zero"

    return "ambiguous"


def infer_resolved_outcome_from_status(label_status: str) -> int | None:
    if label_status == "yes_won":
        return 1
    if label_status == "no_won":
        return 0
    return None


def build_market_table() -> None:
    df = read_parquet(RAW_INPUT).copy()

    df = df[df["closed"] == True].copy()

    df["platform"] = "polymarket"
    df["open_ts"] = df["created_at"].apply(to_utc_timestamp)
    df["close_ts"] = df["end_date"].apply(to_utc_timestamp)

    df["parsed_outcomes"] = df["outcomes"].apply(parse_json_list)
    df["parsed_outcome_prices"] = df["outcome_prices"].apply(parse_json_list)
    df["parsed_token_ids"] = df["raw_market"].apply(
        lambda m: parse_json_list(m.get("clobTokenIds")) if isinstance(m, dict) else None
    )

    df["label_status"] = df["parsed_outcome_prices"].apply(classify_terminal_prices)
    df["resolved_outcome"] = df["label_status"].apply(infer_resolved_outcome_from_status)

    df["duration_hours"] = (df["close_ts"] - df["open_ts"]).dt.total_seconds() / 3600.0

    df = df[
        df["open_ts"].notna()
        & df["close_ts"].notna()
        & (df["close_ts"] > df["open_ts"])
    ].copy()

    keep_cols = [
        "market_id",
        "platform",
        "question",
        "category",
        "open_ts",
        "close_ts",
        "duration_hours",
        "parsed_outcomes",
        "parsed_outcome_prices",
        "parsed_token_ids",
        "label_status",
        "resolved_outcome",
        "volume",
        "liquidity",
    ]

    market_df = df[keep_cols].copy()

    write_parquet(market_df, OUTPUT)

    print(f"[OK] Saved cleaned market table to {OUTPUT}")
    print(f"[INFO] Rows written: {len(market_df)}")
    print("[INFO] label_status breakdown:")
    print(market_df["label_status"].value_counts(dropna=False))
    print(f"[INFO] Non-null resolved outcomes: {market_df['resolved_outcome'].notna().sum()}")


if __name__ == "__main__":
    build_market_table()
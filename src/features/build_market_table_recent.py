from __future__ import annotations

from pathlib import Path
import json

import pandas as pd

from src.utils.io import read_parquet, write_parquet
from src.utils.time_utils import to_utc_timestamp

RAW_INPUT = Path("data/processed/polymarket_markets_recent.parquet")
OUTPUT = Path("data/processed/markets_recent.parquet")
STRATIFIED_OUTPUT = Path("data/processed/markets_recent_stratified.parquet")

MIN_VOLUME_THRESHOLD = 1000
TARGET_STRATIFIED_SAMPLE_SIZE = 120


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


def infer_category_from_question(question: str) -> str:
    q = (question or "").lower()

    if any(word in q for word in [
        "trump", "biden", "election", "senate", "president",
        "congress", "supreme court", "republican", "democrat",
        "harris", "kamala", "rfk", "poll", "vote"
    ]):
        return "Politics"

    if any(word in q for word in [
        "bitcoin", "btc", "eth", "ethereum", "sol", "crypto",
        "airdrop", "defi", "token", "coinbase", "eigenlayer",
        "usde", "fdv", "market cap", "xrp"
    ]):
        return "Crypto"

    if any(word in q for word in [
        "nba", "nfl", "mlb", "soccer", "football", "tennis",
        "ufc", "fight", "olympics", "championship", "super bowl",
        "starship", "launches", "warriors", "lakers"
    ]):
        return "Sports"

    if any(word in q for word in [
        "apple", "google", "openai", "gpt", "twitter", "x remove",
        "tesla", "spacex", "company", "airbnb"
    ]):
        return "Business/Tech"

    if any(word in q for word in [
        "bond", "drake", "rihanna", "movie", "album", "celebrity",
        "logan paul", "james bond", "cosmo jarvis", "tom hardy"
    ]):
        return "Culture/Entertainment"

    if any(word in q for word in [
        "covid", "coronavirus", "vaccine", "cases", "health", "science"
    ]):
        return "Science/Health"

    return "Other"


def build_stratified_sample(df: pd.DataFrame, target_n: int, random_state: int = 42) -> pd.DataFrame:
    if df.empty:
        return df.copy()

    df = df.copy()
    df = df[df["category_fallback"].notna()].copy()

    bucket_counts = df["category_fallback"].value_counts(dropna=False)
    n_buckets = len(bucket_counts)
    per_bucket = max(1, target_n // n_buckets)

    sampled_parts = []
    used_market_ids = set()

    for bucket in bucket_counts.index:
        bucket_df = df[df["category_fallback"] == bucket].copy()
        take_n = min(len(bucket_df), per_bucket)

        part = bucket_df.sample(n=take_n, random_state=random_state)
        sampled_parts.append(part)
        used_market_ids.update(part["market_id"].tolist())

    sampled = pd.concat(sampled_parts, ignore_index=True)

    if len(sampled) < target_n:
        remaining = df[~df["market_id"].isin(used_market_ids)].copy()
        needed = target_n - len(sampled)

        if not remaining.empty:
            top_up = remaining.sample(n=min(len(remaining), needed), random_state=random_state)
            sampled = pd.concat([sampled, top_up], ignore_index=True)

    sampled = sampled.reset_index(drop=True)
    return sampled


def build_market_table_recent() -> None:
    df = read_parquet(RAW_INPUT).copy()

    print(f"[INFO] Raw recent rows: {len(df)}")

    df = df[df["closed"] == True].copy()
    print(f"[INFO] Closed rows: {len(df)}")

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

    df["volume_num"] = pd.to_numeric(df["volume"], errors="coerce")
    df["liquidity_num"] = pd.to_numeric(df["liquidity"], errors="coerce")

    df = df[
        df["open_ts"].notna()
        & df["close_ts"].notna()
        & (df["close_ts"] > df["open_ts"])
    ].copy()

    print(f"[INFO] Rows after timestamp sanity checks: {len(df)}")

    df = df[df["resolved_outcome"].notna()].copy()
    print(f"[INFO] Rows after resolved-outcome filter: {len(df)}")

    df = df[df["volume_num"].fillna(0) >= MIN_VOLUME_THRESHOLD].copy()
    print(f"[INFO] Volume threshold applied: >= {MIN_VOLUME_THRESHOLD}")
    print(f"[INFO] Rows after volume threshold: {len(df)}")

    df["category_fallback"] = df["question"].apply(infer_category_from_question)

    keep_cols = [
        "market_id",
        "platform",
        "question",
        "category",
        "category_fallback",
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
        "volume_num",
        "liquidity_num",
    ]

    market_df = df[keep_cols].copy()
    stratified_df = build_stratified_sample(
        market_df,
        target_n=TARGET_STRATIFIED_SAMPLE_SIZE,
        random_state=42,
    )

    write_parquet(market_df, OUTPUT)
    write_parquet(stratified_df, STRATIFIED_OUTPUT)

    print(f"[OK] Saved cleaned recent market table to {OUTPUT}")
    print(f"[INFO] Rows written: {len(market_df)}")
    print("[INFO] label_status breakdown:")
    print(market_df["label_status"].value_counts(dropna=False))
    print(f"[INFO] Non-null resolved outcomes: {market_df['resolved_outcome'].notna().sum()}")

    print("\n[INFO] Fallback category breakdown:")
    print(market_df["category_fallback"].value_counts(dropna=False))

    print(f"\n[OK] Saved stratified sample to {STRATIFIED_OUTPUT}")
    print(f"[INFO] Stratified sample rows: {len(stratified_df)}")
    print("[INFO] Stratified sample category breakdown:")
    print(stratified_df["category_fallback"].value_counts(dropna=False))

    liquidity_missing_rate = market_df["liquidity_num"].isna().mean()
    print(f"\n[INFO] Liquidity missing rate: {liquidity_missing_rate:.2%}")


if __name__ == "__main__":
    build_market_table_recent()
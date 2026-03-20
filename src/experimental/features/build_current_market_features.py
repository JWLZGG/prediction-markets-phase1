from __future__ import annotations

from pathlib import Path
import json

import numpy as np
import pandas as pd

from src.ingest.price_history import fetch_price_history, history_to_df
from src.utils.io import read_parquet, write_parquet
from src.utils.time_utils import to_utc_timestamp

INPUT_PATH = Path("data/processed/polymarket_markets_current.parquet")
OUTPUT_PATH = Path("data/processed/current_polymarket_features.parquet")


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


def extract_first_token_id(token_ids):
    if token_ids is None:
        return None
    if isinstance(token_ids, list) and len(token_ids) >= 1:
        return str(token_ids[0])
    if isinstance(token_ids, str):
        try:
            parsed = json.loads(token_ids)
            if isinstance(parsed, list) and len(parsed) >= 1:
                return str(parsed[0])
        except Exception:
            return None
    return None


def categorize_question(text: str) -> str:
    t = str(text).lower()

    politics_terms = ["trump", "biden", "election", "senate", "president", "house", "governor", "democrat", "republican"]
    crypto_terms = ["btc", "bitcoin", "eth", "ethereum", "sol", "crypto", "token", "airdrop", "defi", "fdv"]
    sports_terms = ["nba", "nfl", "mlb", "fifa", "ufc", "tennis", "goal", "match", "win the", "championship"]
    culture_terms = ["movie", "album", "oscar", "actor", "actress", "james bond", "netflix", "song"]
    business_terms = ["openai", "tesla", "apple", "amazon", "meta", "microsoft", "fed", "rate cut", "market cap"]

    if any(k in t for k in politics_terms):
        return "Politics"
    if any(k in t for k in crypto_terms):
        return "Crypto"
    if any(k in t for k in sports_terms):
        return "Sports"
    if any(k in t for k in culture_terms):
        return "Culture/Entertainment"
    if any(k in t for k in business_terms):
        return "Business/Tech"
    return "Other"


def price_at_or_before(hist_df: pd.DataFrame, target_ts: pd.Timestamp):
    if hist_df.empty:
        return None
    work = hist_df.copy()
    work["ts"] = pd.to_datetime(work["ts"], utc=True, errors="coerce")
    work = work.dropna(subset=["ts", "price"]).sort_values("ts")
    eligible = work[work["ts"] <= target_ts]
    if eligible.empty:
        return None
    return float(eligible.iloc[-1]["price"])


def run_build_current_market_features() -> None:
    df = read_parquet(INPUT_PATH).copy()

    now_ts = pd.Timestamp.utcnow().tz_localize("UTC") if pd.Timestamp.utcnow().tzinfo is None else pd.Timestamp.utcnow().tz_convert("UTC")

    df = df[df["closed"] == False].copy()
    df["platform"] = "polymarket"
    df["open_ts"] = df["created_at"].apply(to_utc_timestamp)
    df["close_ts"] = df["end_date"].apply(to_utc_timestamp)

    df = df[df["open_ts"].notna() & df["close_ts"].notna() & (df["close_ts"] > now_ts)].copy()
    df = df.reset_index(drop=True)

    df["parsed_outcomes"] = df["outcomes"].apply(parse_json_list)
    df["parsed_token_ids"] = df["raw_market"].apply(
        lambda m: parse_json_list(m.get("clobTokenIds")) if isinstance(m, dict) else None
    )
    df["market_token_id"] = df["parsed_token_ids"].apply(extract_first_token_id)

    df["category_fallback"] = df["question"].apply(categorize_question)
    df["duration_hours"] = (df["close_ts"] - df["open_ts"]).dt.total_seconds() / 3600.0
    df["time_to_close_hours"] = (df["close_ts"] - now_ts).dt.total_seconds() / 3600.0
    df["log_volume"] = np.log1p(pd.to_numeric(df["volume"], errors="coerce"))

    probs = []
    dist_05 = []
    change_24h = []
    hist_counts = []

    for i, row in df.iterrows():
        token_id = row["market_token_id"]

        if token_id is None:
            probs.append(None)
            dist_05.append(None)
            change_24h.append(None)
            hist_counts.append(0)
            continue

        try:
            hist_json = fetch_price_history(
                token_id=token_id,
                interval="max",
                fidelity=720,
                timeout=30,
            )
            hist_df = history_to_df(hist_json)

            current_prob = price_at_or_before(hist_df, now_ts)
            prob_24h_ago = price_at_or_before(hist_df, now_ts - pd.Timedelta(hours=24))

            probs.append(current_prob)
            dist_05.append(None if current_prob is None else abs(current_prob - 0.5))
            change_24h.append(None if (current_prob is None or prob_24h_ago is None) else current_prob - prob_24h_ago)

            if hist_df.empty:
                hist_counts.append(0)
            else:
                hist_df["ts"] = pd.to_datetime(hist_df["ts"], utc=True, errors="coerce")
                hist_counts.append(int((hist_df["ts"] <= now_ts).sum()))

        except Exception as e:
            print(f"[WARN] row={i} market_id={row.get('market_id')} failed: {repr(e)}")
            probs.append(None)
            dist_05.append(None)
            change_24h.append(None)
            hist_counts.append(0)

        if (i + 1) % 25 == 0:
            print(f"[INFO] processed {i + 1}/{len(df)} rows")

    df["market_implied_prob"] = probs
    df["distance_from_0_5"] = dist_05
    df["prob_change_24h"] = change_24h
    df["history_points_count"] = hist_counts

    keep_cols = [
        "market_id",
        "platform",
        "question",
        "category",
        "category_fallback",
        "open_ts",
        "close_ts",
        "time_to_close_hours",
        "duration_hours",
        "volume",
        "log_volume",
        "market_token_id",
        "market_implied_prob",
        "distance_from_0_5",
        "prob_change_24h",
        "history_points_count",
    ]

    out_df = df[keep_cols].copy()
    write_parquet(out_df, OUTPUT_PATH)

    print(f"[OK] Wrote current market features to {OUTPUT_PATH}")
    print(f"[INFO] Rows written: {len(out_df)}")
    print(f"[INFO] Non-null market_implied_prob: {out_df['market_implied_prob'].notna().sum()}")


if __name__ == "__main__":
    run_build_current_market_features()
from __future__ import annotations

from pathlib import Path
from typing import Any
import json

import numpy as np
import pandas as pd

from src.ingest.price_history import fetch_price_history, history_to_df
from src.utils.io import write_parquet


def extract_first_token_id(token_ids: Any) -> str | None:
    if token_ids is None:
        return None

    if isinstance(token_ids, (list, tuple)):
        return str(token_ids[0]) if len(token_ids) >= 1 else None

    try:
        if hasattr(token_ids, "__len__") and not isinstance(token_ids, str):
            return str(token_ids[0]) if len(token_ids) >= 1 else None
    except Exception:
        pass

    if isinstance(token_ids, str):
        try:
            parsed = json.loads(token_ids)
            if isinstance(parsed, list) and len(parsed) >= 1:
                return str(parsed[0])
        except Exception:
            return None

    return None


def normalize_ts(ts: Any) -> pd.Timestamp:
    ts = pd.Timestamp(ts)
    if ts.tzinfo is None:
        return ts.tz_localize("UTC")
    return ts.tz_convert("UTC")


def price_at_or_before(hist_df: pd.DataFrame, target_ts: pd.Timestamp) -> float | None:
    if hist_df.empty:
        return None

    target_ts = normalize_ts(target_ts)
    work = hist_df.copy()
    work["ts"] = pd.to_datetime(work["ts"], utc=True, errors="coerce")
    work = work.dropna(subset=["ts", "price"]).sort_values("ts")

    eligible = work[work["ts"] <= target_ts]
    if eligible.empty:
        return None

    return float(eligible.iloc[-1]["price"])


def history_features_for_snapshot(hist_df: pd.DataFrame, target_ts: pd.Timestamp) -> dict[str, float | int | None]:
    if hist_df.empty:
        return {
            "history_points_count": 0,
            "market_implied_prob": None,
            "distance_from_0_5": None,
            "prob_change_24h": None,
            "prob_change_12h": None,
            "realized_volatility": None,
        }

    target_ts = normalize_ts(target_ts)

    work = hist_df.copy()
    work["ts"] = pd.to_datetime(work["ts"], utc=True, errors="coerce")
    work["price"] = pd.to_numeric(work["price"], errors="coerce")
    work = work.dropna(subset=["ts", "price"]).sort_values("ts")

    up_to_target = work[work["ts"] <= target_ts].copy()

    if up_to_target.empty:
        return {
            "history_points_count": 0,
            "market_implied_prob": None,
            "distance_from_0_5": None,
            "prob_change_24h": None,
            "prob_change_12h": None,
            "realized_volatility": None,
        }

    current_prob = float(up_to_target.iloc[-1]["price"])

    prob_24h_ago = price_at_or_before(work, target_ts - pd.Timedelta(hours=24))
    prob_12h_ago = price_at_or_before(work, target_ts - pd.Timedelta(hours=12))

    prob_change_24h = None if prob_24h_ago is None else current_prob - prob_24h_ago
    prob_change_12h = None if prob_12h_ago is None else current_prob - prob_12h_ago

    diffs = up_to_target["price"].diff().dropna()
    realized_volatility = None if diffs.empty else float(diffs.std())

    return {
        "history_points_count": int(len(up_to_target)),
        "market_implied_prob": current_prob,
        "distance_from_0_5": abs(current_prob - 0.5),
        "prob_change_24h": prob_change_24h,
        "prob_change_12h": prob_change_12h,
        "realized_volatility": realized_volatility,
    }


def enrich_history_features_file(input_path: Path, output_path: Path) -> None:
    df = pd.read_parquet(input_path).copy()

    df["market_token_id"] = df["parsed_token_ids"].apply(extract_first_token_id)

    feature_rows = []
    cache: dict[str, pd.DataFrame] = {}

    non_null_token_ids = df["market_token_id"].notna().sum()
    print(df["market_token_id"].head(10))
    print("non-null token ids:", non_null_token_ids)

    for i, row in df.iterrows():
        token_id = row["market_token_id"]
        target_ts = row["target_ts"]

        if token_id is None or pd.isna(target_ts):
            feature_rows.append({
                "history_points_count": 0,
                "market_implied_prob": None,
                "distance_from_0_5": None,
                "prob_change_24h": None,
                "prob_change_12h": None,
                "realized_volatility": None,
            })
            continue

        try:
            if token_id not in cache:
                history_json = fetch_price_history(
                    token_id=token_id,
                    interval="max",
                    fidelity=720,
                    timeout=30,
                )
                cache[token_id] = history_to_df(history_json)

            feats = history_features_for_snapshot(
                hist_df=cache[token_id],
                target_ts=pd.Timestamp(target_ts),
            )
            feature_rows.append(feats)

        except Exception as e:
            print(f"[WARN] row={i} market_id={row.get('market_id')} failed: {repr(e)}")
            feature_rows.append({
                "history_points_count": 0,
                "market_implied_prob": None,
                "distance_from_0_5": None,
                "prob_change_24h": None,
                "prob_change_12h": None,
                "realized_volatility": None,
            })

        if (i + 1) % 25 == 0:
            print(f"[INFO] processed {i + 1}/{len(df)} rows")

    feats_df = pd.DataFrame(feature_rows)
    out_df = pd.concat([df.reset_index(drop=True), feats_df.reset_index(drop=True)], axis=1)

    write_parquet(out_df, output_path)

    print(f"[OK] Wrote history-feature enriched file to {output_path}")
    print(f"[INFO] Rows written: {len(out_df)}")
    print(f"[INFO] Non-null market_implied_prob: {out_df['market_implied_prob'].notna().sum()}")
    print(f"[INFO] Non-null prob_change_24h: {out_df['prob_change_24h'].notna().sum()}")
    print(f"[INFO] Non-null prob_change_12h: {out_df['prob_change_12h'].notna().sum()}")
    print(f"[INFO] Non-null realized_volatility: {out_df['realized_volatility'].notna().sum()}")


def enrich_history_features_recent_24h() -> None:
    enrich_history_features_file(
        input_path=Path("data/processed/features_24h_recent.parquet"),
        output_path=Path("data/processed/features_24h_recent_history_enriched.parquet"),
    )


def enrich_history_features_recent_mid() -> None:
    enrich_history_features_file(
        input_path=Path("data/processed/features_mid_recent.parquet"),
        output_path=Path("data/processed/features_mid_recent_history_enriched.parquet"),
    )


if __name__ == "__main__":
    enrich_history_features_recent_24h()
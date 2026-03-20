from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.utils.io import read_parquet

INPUT_PATH = Path("data/processed/current_polymarket_features.parquet")
OUTPUT_PATH = Path("artifacts/outputs/current_polymarket_top_edges.csv")


def heuristic_model_score(row: pd.Series) -> float | None:
    p = row.get("market_implied_prob")
    if pd.isna(p):
        return None

    score = float(p)

    dist = row.get("distance_from_0_5")
    if pd.notna(dist):
        score += 0.08 * float(dist)

    mom24 = row.get("prob_change_24h")
    if pd.notna(mom24):
        score += 0.25 * float(mom24)

    hist_n = row.get("history_points_count")
    if pd.notna(hist_n):
        score += -0.0004 * float(hist_n)

    score = max(0.001, min(0.999, score))
    return score


def run_score_current_polymarket() -> None:
    df = read_parquet(INPUT_PATH).copy()

    df = df[df["market_implied_prob"].notna()].copy()
    df["model_prob"] = df.apply(heuristic_model_score, axis=1)
    df = df[df["model_prob"].notna()].copy()

    df["model_minus_market"] = df["model_prob"] - df["market_implied_prob"]
    df["abs_edge"] = df["model_minus_market"].abs()

    ranked = df.sort_values(["abs_edge", "log_volume"], ascending=[False, False]).copy()

    keep_cols = [
        "market_id",
        "question",
        "category_fallback",
        "time_to_close_hours",
        "volume",
        "market_implied_prob",
        "model_prob",
        "model_minus_market",
        "abs_edge",
    ]

    ranked[keep_cols].head(50).to_csv(OUTPUT_PATH, index=False)

    print(f"[OK] Wrote ranked current markets to {OUTPUT_PATH}")
    print("\n[INFO] Top 10 candidate edges:")
    print(ranked[keep_cols].head(10).to_string(index=False))


if __name__ == "_main_":
    run_score_current_polymarket()
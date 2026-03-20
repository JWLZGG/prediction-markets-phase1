from __future__ import annotations

from pathlib import Path
import pickle

import numpy as np
import pandas as pd

INPUT_PATH = Path("data/processed/current_polymarket_features.parquet")
MODEL_PATH = Path("artifacts/models/best_24h_model.pkl")
OUTPUT_CSV_PATH = Path("artifacts/outputs/current_polymarket_top_edges_trained.csv")
OUTPUT_PARQUET_PATH = Path("data/processed/current_polymarket_scored_trained.parquet")


def edge_bucket(x: float) -> str:
    x = abs(float(x))
    if x >= 0.15:
        return "large"
    if x >= 0.08:
        return "medium"
    return "small"


def run_score_current_polymarket_trained() -> None:
    df = pd.read_parquet(INPUT_PATH).copy()

    df["log_volume"] = np.log1p(pd.to_numeric(df["volume"], errors="coerce"))

    print(f"[INFO] Starting current rows: {len(df)}")

    df = df[df["market_implied_prob"].notna()].copy()
    print(f"[INFO] After non-null market_implied_prob: {len(df)}")

    df = df[pd.to_numeric(df["volume"], errors="coerce") >= 1000].copy()
    print(f"[INFO] After volume >= 1000: {len(df)}")

    df = df[pd.to_numeric(df["history_points_count"], errors="coerce") >= 20].copy()
    print(f"[INFO] After history_points_count >= 20: {len(df)}")

    df = df[pd.to_numeric(df["time_to_close_hours"], errors="coerce") >= 6].copy()
    print(f"[INFO] After time_to_close_hours >= 6: {len(df)}")

    df = df[pd.to_numeric(df["time_to_close_hours"], errors="coerce") <= 720].copy()
    print(f"[INFO] After time_to_close_hours <= 720: {len(df)}")

    if df.empty:
        print("[WARN] No current markets remain after filtering. Nothing to score.")
        return

    feature_cols = [
        "category_fallback",
        "duration_hours",
        "market_implied_prob",
        "log_volume",
        "distance_from_0_5",
        "prob_change_24h",
        "history_points_count",
    ]

    X = df[feature_cols].copy()

    if X.empty:
        print("[WARN] Feature matrix is empty after filtering. Nothing to score.")
        return

    with open(MODEL_PATH, "rb") as f:
        model = pickle.load(f)

    df["model_prob"] = model.predict_proba(X)[:, 1]
    df["model_minus_market"] = df["model_prob"] - df["market_implied_prob"]
    df["abs_edge"] = df["model_minus_market"].abs()
    df["edge_bucket"] = df["abs_edge"].apply(edge_bucket)
    df["direction"] = df["model_minus_market"].apply(
        lambda x: "bullish_vs_market" if x > 0 else "bearish_vs_market"
    )
    df["eligible_for_scoring"] = True

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
        "direction",
        "edge_bucket",
        "eligible_for_scoring",
    ]

    OUTPUT_CSV_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PARQUET_PATH.parent.mkdir(parents=True, exist_ok=True)

    ranked[keep_cols].head(50).to_csv(OUTPUT_CSV_PATH, index=False)
    ranked.to_parquet(OUTPUT_PARQUET_PATH, index=False)

    print(f"[OK] Wrote trained-model ranked current markets to {OUTPUT_CSV_PATH}")
    print(f"[OK] Wrote full scored parquet to {OUTPUT_PARQUET_PATH}")
    print("\n[INFO] Top 10 candidate edges:")
    print(ranked[keep_cols].head(10).to_string(index=False))


if __name__ == "__main__":
    run_score_current_polymarket_trained()
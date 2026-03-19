from __future__ import annotations

from pathlib import Path
import pickle

import pandas as pd

INPUT_PATH = Path("data/processed/kalshi_current_features.parquet")
MODEL_PATH = Path("reports/best_24h_model.pkl")
OUTPUT_CSV_PATH = Path("reports/kalshi_current_top_edges_trained.csv")
OUTPUT_PARQUET_PATH = Path("data/processed/kalshi_current_scored_trained.parquet")


def edge_bucket(x: float) -> str:
    x = abs(float(x))
    if x >= 0.15:
        return "large"
    if x >= 0.08:
        return "medium"
    return "small"


def confidence_band(row) -> str:
    ttc = pd.to_numeric(row.get("time_to_close_hours"), errors="coerce")
    vol = pd.to_numeric(row.get("volume_num"), errors="coerce")
    oi = pd.to_numeric(row.get("open_interest_num"), errors="coerce")

    if pd.notna(ttc) and pd.notna(vol) and pd.notna(oi):
        if 6 <= ttc <= 168 and vol >= 50 and oi >= 25:
            return "high_confidence"
        if 6 <= ttc <= 336 and vol >= 10 and oi > 0:
            return "exploratory"
    return "low_quality"


def run_score_current_kalshi() -> None:
    df = pd.read_parquet(INPUT_PATH).copy()

    print(f"[INFO] Starting Kalshi rows: {len(df)}")

    df = df[df["market_implied_prob"].notna()].copy()
    print(f"[INFO] After non-null market_implied_prob: {len(df)}")

    df = df[pd.to_numeric(df["time_to_close_hours"], errors="coerce") >= 6].copy()
    print(f"[INFO] After time_to_close_hours >= 6: {len(df)}")

    df = df[pd.to_numeric(df["time_to_close_hours"], errors="coerce") <= 336].copy()
    print(f"[INFO] After time_to_close_hours <= 336: {len(df)}")

    df = df[pd.to_numeric(df["volume_num"], errors="coerce") > 0].copy()
    print(f"[INFO] After volume_num > 0: {len(df)}")

    df = df[pd.to_numeric(df["open_interest_num"], errors="coerce") > 0].copy()
    print(f"[INFO] After open_interest_num > 0: {len(df)}")

    df = df[pd.to_numeric(df["volume_num"], errors="coerce") >= 10].copy()
    print(f"[INFO] After volume_num >= 10: {len(df)}")

    if df.empty:
        print("[WARN] No Kalshi markets remain after filtering. Nothing to score.")
        return

    X = pd.DataFrame({
        "category_fallback": df["category_fallback"],
        "duration_hours": df["duration_hours"],
        "market_implied_prob": df["market_implied_prob"],
        "log_volume": df["log_volume"],
        "distance_from_0_5": (df["market_implied_prob"] - 0.5).abs(),
        "prob_change_24h": 0.0,
        "history_points_count": 0.0,
    })

    with open(MODEL_PATH, "rb") as f:
        model = pickle.load(f)

    df["model_prob"] = model.predict_proba(X)[:, 1]
    df["model_minus_market"] = df["model_prob"] - df["market_implied_prob"]
    df["abs_edge"] = df["model_minus_market"].abs()
    df["direction"] = df["model_minus_market"].apply(
        lambda x: "bullish_vs_market" if x > 0 else "bearish_vs_market"
    )
    df["edge_bucket"] = df["abs_edge"].apply(edge_bucket)
    df["eligible_for_scoring"] = True
    df["confidence_band"] = df.apply(confidence_band, axis=1)

    df = df[df["confidence_band"] != "low_quality"].copy()

    ranked = df.sort_values(
        ["confidence_band", "abs_edge", "log_volume"],
        ascending=[True, False, False]
    ).copy()

    keep_cols = [
        "market_id",
        "ticker",
        "question",
        "category_fallback",
        "time_to_close_hours",
        "volume_num",
        "open_interest_num",
        "market_implied_prob",
        "model_prob",
        "model_minus_market",
        "abs_edge",
        "direction",
        "edge_bucket",
        "confidence_band",
        "eligible_for_scoring",
    ]

    OUTPUT_CSV_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PARQUET_PATH.parent.mkdir(parents=True, exist_ok=True)

    ranked[keep_cols].head(50).to_csv(OUTPUT_CSV_PATH, index=False)
    ranked.to_parquet(OUTPUT_PARQUET_PATH, index=False)

    print(f"[OK] Wrote Kalshi ranked CSV to {OUTPUT_CSV_PATH}")
    print(f"[OK] Wrote full Kalshi scored parquet to {OUTPUT_PARQUET_PATH}")
    print("\n[INFO] Top 10 Kalshi candidate edges:")
    print(ranked[keep_cols].head(10).to_string(index=False))


if __name__ == "__main__":
    run_score_current_kalshi()
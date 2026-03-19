from __future__ import annotations

from pathlib import Path
import pandas as pd

POLY_PATH = Path("data/processed/current_polymarket_scored_trained.parquet")
KALSHI_PATH = Path("data/processed/kalshi_current_scored_trained.parquet")


def summarize_scores(df: pd.DataFrame, venue: str, volume_col: str) -> None:
    print(f"\n{'=' * 80}")
    print(f"[INFO] Venue: {venue}")
    print(f"[INFO] Rows: {len(df)}")

    if len(df) == 0:
        print("[WARN] No rows to summarize.")
        return

    print("\n[INFO] model_prob distribution:")
    print(df["model_prob"].describe().to_string())

    print("\n[INFO] market_implied_prob distribution:")
    print(df["market_implied_prob"].describe().to_string())

    print("\n[INFO] Top 10 by abs_edge:")
    cols = [c for c in [
        "question", "category_fallback", "time_to_close_hours",
        volume_col, "market_implied_prob", "model_prob",
        "model_minus_market", "abs_edge"
    ] if c in df.columns]
    print(df.sort_values("abs_edge", ascending=False)[cols].head(10).to_string(index=False))

    print("\n[INFO] Top 10 by liquidity/volume proxy:")
    if volume_col in df.columns:
        print(df.sort_values(volume_col, ascending=False)[cols].head(10).to_string(index=False))

    print("\n[INFO] Suspicious extremes:")
    extreme = df[
        (df["model_prob"] <= 0.01)
        | (df["model_prob"] >= 0.99)
        | (df["abs_edge"] >= 0.25)
    ].copy()
    print(f"[INFO] Extreme rows: {len(extreme)}")
    if len(extreme) > 0:
        print(extreme[cols].head(20).to_string(index=False))


def run_sanity_check_current_scores() -> None:
    if POLY_PATH.exists():
        poly = pd.read_parquet(POLY_PATH)
        summarize_scores(poly, "Polymarket", "volume")
    else:
        print(f"[WARN] Missing {POLY_PATH}")

    if KALSHI_PATH.exists():
        kalshi = pd.read_parquet(KALSHI_PATH)
        summarize_scores(kalshi, "Kalshi", "volume_num")
    else:
        print(f"[WARN] Missing {KALSHI_PATH}")


if __name__ == "__main__":
    run_sanity_check_current_scores()
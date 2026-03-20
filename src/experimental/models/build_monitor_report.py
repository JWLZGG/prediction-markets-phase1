from __future__ import annotations

from pathlib import Path
import pandas as pd

POLY_PATH = Path("data/processed/current_polymarket_scored_trained.parquet")
KALSHI_PATH = Path("data/processed/kalshi_current_scored_trained.parquet")
REPORT_PATH = Path("reports/current_monitor_report.md")


def load_top(df: pd.DataFrame, venue: str, volume_col: str, n: int = 20) -> pd.DataFrame:
    cols = [c for c in [
        "question", "category_fallback", "time_to_close_hours",
        volume_col, "market_implied_prob", "model_prob",
        "model_minus_market", "abs_edge", "direction", "edge_bucket"
    ] if c in df.columns]

    top = df.sort_values(["abs_edge", volume_col], ascending=[False, False]).head(n).copy()
    top["venue"] = venue
    return top[["venue"] + cols]


def load_top_filtered(
    df: pd.DataFrame,
    venue: str,
    volume_col: str,
    n: int = 20,
    confidence_band: str | None = None,
) -> pd.DataFrame:
    work = df.copy()
    if confidence_band is not None and "confidence_band" in work.columns:
        work = work[work["confidence_band"] == confidence_band].copy()

    cols = [c for c in [
        "question", "category_fallback", "time_to_close_hours",
        volume_col, "market_implied_prob", "model_prob",
        "model_minus_market", "abs_edge", "direction", "edge_bucket",
        "confidence_band"
    ] if c in work.columns]

    top = work.sort_values(["abs_edge", volume_col], ascending=[False, False]).head(n).copy()
    top["venue"] = venue
    return top[["venue"] + cols]


def markdown_table(df: pd.DataFrame) -> str:
    if df.empty:
        return "_No rows_"

    cols = list(df.columns)
    header = "| " + " | ".join(cols) + " |"
    sep = "| " + " | ".join(["---"] * len(cols)) + " |"

    rows = []
    for _, row in df.iterrows():
        vals = []
        for c in cols:
            v = row[c]
            if pd.isna(v):
                vals.append("")
            else:
                vals.append(str(v).replace("\n", " ").replace("|", "\\|"))
        rows.append("| " + " | ".join(vals) + " |")

    return "\n".join([header, sep] + rows)


def run_build_monitor_report() -> None:
    sections = []

    sections.append("# Current Monitor Report\n")
    sections.append("## Filters used\n")
    sections.append(
        "- Polymarket: trained current scorer with current-market feature filters already applied.\n"
        "- Kalshi: current binary markets, non-combo products, 6 <= time_to_close_hours <= 336, volume_num > 0, open_interest_num > 0, volume_num >= 10.\n"
    )

    sections.append("## Caveats\n")
    sections.append(
        "- Polymarket scores are closer to the model's training domain.\n"
        "- Kalshi scores are exploratory cross-venue outputs using a Polymarket-trained model.\n"
        "- Kalshi rows are split into high-confidence and exploratory bands based on time-to-close, volume, and open interest.\n"
        "- Large edges on low-volume or poorly categorized rows should be treated cautiously.\n"
    )

    if POLY_PATH.exists():
        poly = pd.read_parquet(POLY_PATH)
        top_poly = load_top(poly, "Polymarket", "volume", n=20)
        sections.append("\n## Top 20 Polymarket edges\n")
        sections.append(markdown_table(top_poly))
        sections.append("\n")
    else:
        sections.append("\n## Top 20 Polymarket edges\nMissing Polymarket scored parquet.\n")

    if KALSHI_PATH.exists():
        kalshi = pd.read_parquet(KALSHI_PATH)

        top_kalshi_high = load_top_filtered(
            kalshi, "Kalshi", "volume_num", n=20, confidence_band="high_confidence"
        )
        top_kalshi_exploratory = load_top_filtered(
            kalshi, "Kalshi", "volume_num", n=20, confidence_band="exploratory"
        )

        sections.append("\n## Top 20 Kalshi high-confidence edges\n")
        sections.append(markdown_table(top_kalshi_high))
        sections.append("\n")

        sections.append("\n## Top 20 Kalshi exploratory edges\n")
        sections.append(markdown_table(top_kalshi_exploratory))
        sections.append("\n")
    else:
        sections.append("\n## Top 20 Kalshi edges\nMissing Kalshi scored parquet.\n")

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text("\n".join(sections), encoding="utf-8")

    print(f"[OK] Wrote monitor report to {REPORT_PATH}")


if __name__ == "__main__":
    run_build_monitor_report()
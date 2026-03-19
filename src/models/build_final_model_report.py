from __future__ import annotations

from pathlib import Path

OFFLINE_SUMMARY_PATH = Path("reports/offline_snapshot_summary.md")
MONITOR_REPORT_PATH = Path("reports/current_monitor_report.md")
COEFFICIENTS_PATH = Path("reports/best_24h_coefficients.md")
OUTPUT_PATH = Path("reports/final_model_report.md")


def safe_read(path: Path, fallback: str) -> str:
    if path.exists():
        return path.read_text(encoding="utf-8")
    return fallback


def run_build_final_model_report() -> None:
    offline_summary = safe_read(
        OFFLINE_SUMMARY_PATH,
        "_Offline snapshot summary missing._"
    )
    monitor_report = safe_read(
        MONITOR_REPORT_PATH,
        "_Current monitor report missing._"
    )
    coefficients = safe_read(
        COEFFICIENTS_PATH,
        "_Coefficient export missing._"
    )

    parts = [
        "# Final Model Report\n",
        "## 1. Objective\n",
        "Build a reproducible prediction-market research and monitoring pipeline that benchmarks model skill against naive and market baselines, then applies the learned model to current markets.\n",

        "## 2. Dataset and framing\n",
        "- Historical resolved-market pipeline built on recent Polymarket data.\n"
        "- Snapshot framing evaluated at open, midpoint, and 24h-before-close.\n"
        "- Current-market monitoring built for Polymarket and exploratory Kalshi scoring.\n",

        "## 3. Key conclusions\n",
        "- The 24h-before-close snapshot is the strongest offline setting.\n"
        "- Midpoint retains some signal, but is weaker than 24h.\n"
        "- Open is not currently robust in the evaluation frame.\n"
        "- Polymarket current scoring is cleaner because it is closer to the model’s training domain.\n"
        "- Kalshi current scoring works as an exploratory cross-venue monitor, but remains noisier and should be interpreted cautiously.\n",

        "## 4. Offline snapshot summary\n",
        offline_summary,
        "\n## 5. Best 24h feature directionality / coefficients\n",
        coefficients,
        "\n## 6. Current monitor outputs\n",
        monitor_report,
        "\n## 7. Interpretation\n",
        "- Offline results suggest the model adds the most value close to resolution.\n"
        "- The 24h snapshot beats both naive and market baselines in the current evaluation summary.\n"
        "- Current Polymarket outputs are the most presentation-ready monitor leg.\n"
        "- Kalshi outputs are useful for exploratory discrepancy ranking, especially after filtering and confidence banding, but still show many suspicious extremes.\n",

        "## 8. Caveats\n",
        "- Cross-venue scoring from a Polymarket-trained model to Kalshi is not a fully validated production setup.\n"
        "- Large edges on low-volume or lower-confidence rows should not be treated as strong signals without additional review.\n"
        "- Category heuristics are still lightweight and may misclassify some contracts.\n",

        "## 9. Recommended next steps\n",
        "- Add venue-specific historical training for Kalshi if historical data becomes available.\n"
        "- Tighten or tier Kalshi confidence rules further.\n"
        "- Add a lightweight dashboard or automated point-in-time export.\n"
        "- Continue monitoring calibration and Brier Skill Score as the feature set evolves.\n",
    ]

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text("\n".join(parts), encoding="utf-8")

    print(f"[OK] Wrote final model report to {OUTPUT_PATH}")


if __name__ == "__main__":
    run_build_final_model_report()
from __future__ import annotations

from pathlib import Path

from src.features.enrich_market_probs_generic import enrich_file


def enrich_market_probs_recent() -> None:
    enrich_file(
        Path("data/processed/features_24h_recent.parquet"),
        Path("data/processed/features_24h_recent_enriched.parquet"),
    )


if __name__ == "__main__":
    enrich_market_probs_recent()
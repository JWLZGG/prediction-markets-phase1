from __future__ import annotations

import sys

from src.ingest.polymarket import run_polymarket_ingestion
from src.features.build_market_table import build_market_table
from src.features.build_snapshots import build_snapshots
from src.models.baseline_logreg import run_baseline_model


def main() -> None:
    if len(sys.argv) < 2:
        raise SystemExit("Usage: python -m src.main [ingest|features|snapshots|model]")

    command = sys.argv[1]

    if command == "ingest":
        run_polymarket_ingestion()
    elif command == "features":
        build_market_table()
    elif command == "snapshots":
        build_snapshots()
    elif command == "model":
        run_baseline_model()
    else:
        raise SystemExit(f"Unknown command: {command}")


if __name__ == "__main__":
    main()
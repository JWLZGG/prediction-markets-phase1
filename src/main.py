from __future__ import annotations

import sys

from src.ingest.polymarket import run_polymarket_ingestion
from src.features.build_market_table import build_market_table
from src.features.build_snapshots import build_snapshots
from src.features.enrich_market_probs import enrich_market_probs
from src.models.baseline_logreg import run_baseline_model
from src.features.build_market_table_recent import build_market_table_recent
from src.features.build_snapshots_recent import build_snapshots_recent
from src.features.enrich_market_probs_recent import enrich_market_probs_recent
from src.features.enrich_market_probs_mid_recent import enrich_market_probs_mid_recent
from src.features.enrich_market_probs_open_recent import enrich_market_probs_open_recent
from src.models.baseline_logreg_recent import run_baseline_model_recent
from src.models.evaluate_recent import evaluate_recent
from src.models.evaluate_mid_recent import evaluate_mid_recent
from src.features.enrich_history_features_recent import (
    enrich_history_features_recent_24h,
    enrich_history_features_recent_mid,
)
from src.models.baseline_logreg_history_recent import run_baseline_model_history_recent
from src.models.baseline_logreg_history_mid_recent import run_baseline_model_history_mid_recent
from src.features.run_integrity_checks_recent import run_integrity_checks_recent
from src.models.baseline_logreg_recent_clean import run_baseline_model_recent_clean
from src.models.baseline_logreg_narrow_history_recent import run_baseline_model_narrow_history_recent
from src.models.baseline_logreg_narrow_history_recent_24hchange import run_baseline_model_narrow_history_recent_24hchange

def main() -> None:
    if len(sys.argv) < 2:
        raise SystemExit(
            "Usage: python -m src.main [ingest|features|snapshots|enrich_probs|model|features_recent|snapshots_recent|enrich_probs_recent|enrich_probs_mid_recent|enrich_probs_open_recent|model_recent|evaluate_recent|evaluate_mid_recent]"
        )

    command = sys.argv[1]

    if command == "ingest":
        run_polymarket_ingestion()
    elif command == "features":
        build_market_table()
    elif command == "snapshots":
        build_snapshots()
    elif command == "enrich_probs":
        enrich_market_probs()
    elif command == "model":
        run_baseline_model()
    elif command == "features_recent":
        build_market_table_recent()
    elif command == "snapshots_recent":
        build_snapshots_recent()
    elif command == "enrich_probs_recent":
        enrich_market_probs_recent()
    elif command == "enrich_probs_mid_recent":
        enrich_market_probs_mid_recent()
    elif command == "enrich_probs_open_recent":
        enrich_market_probs_open_recent()
    elif command == "model_recent":
        run_baseline_model_recent()
    elif command == "evaluate_recent":
        evaluate_recent()
    elif command == "evaluate_mid_recent":
        evaluate_mid_recent()
    elif command == "enrich_history_24h_recent":
        enrich_history_features_recent_24h()
    elif command == "enrich_history_mid_recent":
        enrich_history_features_recent_mid()
    elif command == "model_history_recent":
        run_baseline_model_history_recent()
    elif command == "model_history_mid_recent":
        run_baseline_model_history_mid_recent()
    elif command == "integrity_checks_recent":
        run_integrity_checks_recent()
    elif command == "model_recent_clean":
        run_baseline_model_recent_clean()
    elif command == "model_narrow_history_recent":
        run_baseline_model_narrow_history_recent()
    elif command == "model_narrow_history_recent_24hchange":
        run_baseline_model_narrow_history_recent_24hchange()
    else:
        raise SystemExit(f"Unknown command: {command}")
    


if __name__ == "__main__":
    main()
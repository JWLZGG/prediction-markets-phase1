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
from src.models.evaluate_narrow_history_recent_24hchange import run_evaluate_narrow_history_recent_24hchange
from src.ingest.polymarket_current import run_polymarket_current_ingestion
from src.features.build_current_market_features import run_build_current_market_features
from src.models.score_current_polymarket import run_score_current_polymarket
from src.models.train_best_24h_model import run_train_best_24h_model
from src.models.score_current_polymarket_trained import run_score_current_polymarket_trained
from src.ingest.kalshi_current import run_kalshi_current_ingestion
from src.features.build_kalshi_current_features import run_build_kalshi_current_features
from src.models.score_current_kalshi import run_score_current_kalshi
from src.models.sanity_check_current_scores import run_sanity_check_current_scores
from src.models.build_monitor_report import run_build_monitor_report
from src.models.summarize_offline_results import run_summarize_offline_results
from src.models.export_best_24h_coefficients import run_export_best_24h_coefficients
from src.models.build_final_model_report import run_build_final_model_report
from src.detect.prediction_scanner import get_scanner_status
from src.backtest.replay_pred import get_replay_status
from src.detect.prediction_scanner import run_prediction_scanner

def main() -> None:
    if len(sys.argv) < 2:
        raise SystemExit(
            "Usage: python -m src.main <command>\n"
            "Examples:\n"
            "  Historical pipeline: features_recent, snapshots_recent, enrich_probs_recent, enrich_history_24h_recent\n"
            "  Evaluation: evaluate_recent, evaluate_mid_recent, evaluate_narrow_history_recent_24hchange\n"
            "  Current scoring: ingest_current, features_current, score_current_polymarket_trained\n"
            "  Kalshi scoring: ingest_kalshi_current, features_kalshi_current, score_current_kalshi\n"
            "  Reporting: sanity_check_current_scores, summarize_offline_results, export_best_24h_coefficients, build_monitor_report, build_final_model_report"
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
    elif command == "evaluate_narrow_history_recent_24hchange":
        run_evaluate_narrow_history_recent_24hchange()
    elif command == "ingest_current":
        run_polymarket_current_ingestion()
    elif command == "features_current":
        run_build_current_market_features()
    elif command == "score_current_polymarket":
        run_score_current_polymarket()
    elif command == "train_best_24h_model":
        run_train_best_24h_model()
    elif command == "score_current_polymarket_trained":
        run_score_current_polymarket_trained()
    elif command == "ingest_kalshi_current":
        run_kalshi_current_ingestion()
    elif command == "features_kalshi_current":
        run_build_kalshi_current_features()
    elif command == "score_current_kalshi":
        run_score_current_kalshi()
    elif command == "sanity_check_current_scores":
        run_sanity_check_current_scores()
    elif command == "build_monitor_report":
        run_build_monitor_report()
    elif command == "summarize_offline_results":
        run_summarize_offline_results()
    elif command == "export_best_24h_coefficients":
        run_export_best_24h_coefficients()
    elif command == "build_final_model_report":
        run_build_final_model_report()
    elif command == "scanner_status":
        print(get_scanner_status())
    elif command == "replay_status":
        print(get_replay_status())
    elif command == "run_pred":
        run_prediction_scanner()
    else:
        raise SystemExit(f"Unknown command: {command}")
    


if __name__ == "__main__":
    main()
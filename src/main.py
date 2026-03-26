from __future__ import annotations

import argparse

from src.backtest.replay_pred import get_replay_status, run_replay_pred
from src.detect.prediction_scanner import get_scanner_status, run_prediction_scanner
from src.ingest.kalshi_current import run_kalshi_current_ingestion
from src.ingest.polymarket_current import run_polymarket_current_ingestion
from src.ingest.polymarket_orderbook import run_polymarket_orderbook_ingestion
from src.models.baseline_logreg import run_baseline_model
from src.models.evaluate import run_evaluate
from src.models.score_current_kalshi import run_score_current_kalshi
from src.models.score_current_polymarket import run_score_current_polymarket


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "command",
        choices=[
            "ingest_current",
            "ingest_kalshi_current",
            "ingest_polymarket_orderbooks",
            "baseline_model",
            "evaluate",
            "score_current_polymarket",
            "score_current_kalshi",
            "scanner_status",
            "replay_status",
            "run_pred",
            "replay_pred",
        ],
        help="Top-level project command",
    )
    parser.add_argument(
        "--mode",
        choices=[
            "live",
            "synthetic",
            "live_complement",
            "live_complement_polymarket",
            "live_complement_polymarket_loop",
            "live_crossvenue_matched_loop",
        ],
        default="live",
        help="Scanner mode used with run_pred",
    )
    parser.add_argument(
        "--limit-markets",
        type=int,
        default=100,
        help="Polymarket orderbook market limit used with ingest_polymarket_orderbooks",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()

    if args.command == "ingest_current":
        run_polymarket_current_ingestion()
    elif args.command == "ingest_kalshi_current":
        run_kalshi_current_ingestion()
    elif args.command == "ingest_polymarket_orderbooks":
        run_polymarket_orderbook_ingestion(limit_markets=args.limit_markets)
    elif args.command == "baseline_model":
        run_baseline_model()
    elif args.command == "evaluate":
        run_evaluate()
    elif args.command == "score_current_polymarket":
        run_score_current_polymarket()
    elif args.command == "score_current_kalshi":
        run_score_current_kalshi()
    elif args.command == "scanner_status":
        print(get_scanner_status())
    elif args.command == "replay_status":
        print(get_replay_status())
    elif args.command == "run_pred":
        run_prediction_scanner(mode=args.mode)
    elif args.command == "replay_pred":
        run_replay_pred()


if __name__ == "__main__":
    main()

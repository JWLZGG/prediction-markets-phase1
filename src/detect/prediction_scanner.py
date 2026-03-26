from __future__ import annotations

import argparse

from src.detect.scanner_runtime import (
    ComplementRunEvent,
    ScannerRunEvent,
    ScannerStatus,
    append_jsonl,
    get_scanner_status,
    load_config,
    maybe_fail_kalshi_once,
    run_one_cycle,
    run_one_polymarket_complement_cycle,
    run_prediction_scanner,
    run_prediction_scanner_live,
    run_prediction_scanner_live_complement,
    run_prediction_scanner_live_complement_polymarket,
    run_prediction_scanner_live_complement_polymarket_loop,
    run_prediction_scanner_synthetic,
    safe_row_count,
    utc_now_iso,
)

__all__ = [
    "ComplementRunEvent",
    "ScannerRunEvent",
    "ScannerStatus",
    "append_jsonl",
    "get_scanner_status",
    "load_config",
    "maybe_fail_kalshi_once",
    "run_one_cycle",
    "run_one_polymarket_complement_cycle",
    "run_prediction_scanner",
    "run_prediction_scanner_live",
    "run_prediction_scanner_live_complement",
    "run_prediction_scanner_live_complement_polymarket",
    "run_prediction_scanner_live_complement_polymarket_loop",
    "run_prediction_scanner_synthetic",
    "safe_row_count",
    "utc_now_iso",
]


def main() -> None:
    parser = argparse.ArgumentParser()
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
        help="Scanner mode",
    )
    args = parser.parse_args()

    run_prediction_scanner(mode=args.mode)


if __name__ == "__main__":
    main()

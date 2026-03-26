from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from src.detect.scanner_core import (
    flag_to_dict,
    scan_complement_market,
    scan_cross_venue_market,
)
from src.config.scanner_fee_config import get_default_fee_config

LOG_PATH = Path("logs/prediction_scanner_flags.jsonl")

FEE_CONFIG = get_default_fee_config()


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def build_synthetic_flags() -> list[dict]:
    flags: list[dict] = []

    cross_flag = scan_cross_venue_market(
        market_id="btc-above-100k",
        buy_venue="polymarket",
        sell_venue="kalshi",
        buy_asks=[
            {"price": 0.60, "size": 60},
            {"price": 0.61, "size": 40},
        ],
        sell_bids=[
            {"price": 0.64, "size": 50},
            {"price": 0.63, "size": 50},
        ],
        target_size=100,
        fee_config=FEE_CONFIG,
        threshold_bps=100,
    )
    if cross_flag is not None:
        flags.append(flag_to_dict(cross_flag))

    complement_flag = scan_complement_market(
        market_id="election-yes-no",
        venue="polymarket",
        yes_asks=[{"price": 0.47, "size": 100}],
        no_asks=[{"price": 0.46, "size": 100}],
        target_size=100,
        fee_config=FEE_CONFIG,
        threshold_bps=100,
    )
    if complement_flag is not None:
        flags.append(flag_to_dict(complement_flag))

    return flags


def write_flags_jsonl(
    flags: list[dict],
    log_path: Path = LOG_PATH,
    source: str = "synthetic_demo",
) -> None:
    log_path.parent.mkdir(parents=True, exist_ok=True)

    with log_path.open("a", encoding="utf-8") as f:
        for flag in flags:
            detected_ts = _now_iso()

            record = {
                "timestamp": detected_ts,
                "detected_ts_utc": detected_ts,
                "source": source,
                "snapshot_source": source,
                "snapshot_cycle_index": 0,
                "snapshot_output_path": None,
                "replay_lookup_key": flag.get("market_id"),
                **flag,
            }
            f.write(json.dumps(record) + "\n")


def main() -> None:
    flags = build_synthetic_flags()
    write_flags_jsonl(flags, source="synthetic_demo")
    print(f"[OK] Wrote {len(flags)} flags to {LOG_PATH}")


if __name__ == "__main__":
    main()
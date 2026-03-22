from __future__ import annotations

import json
import time
from dataclasses import dataclass, asdict
from datetime import datetime, UTC
from pathlib import Path
from typing import Any

import pandas as pd
import yaml

from src.detect.polymarket_live_complement import scan_polymarket_complements
from src.ingest.polymarket_current import run_polymarket_current_ingestion
from src.ingest.kalshi_current import run_kalshi_current_ingestion
from src.utils.retry import retry_call
from src.detect.logging_runner import build_synthetic_flags, write_flags_jsonl
from src.detect.kalshi_live_complement import scan_kalshi_complements


CONFIG_PATH = Path("configs/prediction_scanner.yaml")
_SIMULATED_KALSHI_FAILURE_ALREADY_USED = False


@dataclass
class ScannerStatus:
    module: str
    status: str
    phase: str
    implemented_now: list[str]
    next_steps: list[str]

def run_prediction_scanner_live_complement_polymarket() -> None:
    print("[INFO] Starting prediction scanner in live_complement_polymarket mode")

    flags, stats = scan_polymarket_complements(
        target_size=10.0,
        threshold_bps=10.0,
    )

    print(f"[INFO] Live Polymarket complement stats: {stats}")

    if flags:
        write_flags_jsonl(flags)
        print(f"[OK] Live Polymarket complement mode produced {len(flags)} flags")
        for flag in flags[:10]:
            print(flag)
    else:
        print("[INFO] No live Polymarket complement flags emitted")

def run_prediction_scanner_synthetic() -> None:
    print("[INFO] Starting prediction scanner in synthetic mode")

    flags = build_synthetic_flags()
    write_flags_jsonl(flags)

    print(f"[OK] Synthetic mode produced {len(flags)} flags")
    for flag in flags:
        print(flag)

def run_prediction_scanner_live_complement() -> None:
    print("[INFO] Starting prediction scanner in live_complement mode")

    flags, stats = scan_kalshi_complements(target_size=1.0, threshold_bps=10.0)

    print(f"[INFO] Live complement stats: {stats}")

    if flags:
        write_flags_jsonl(flags)
        print(f"[OK] Live complement mode produced {len(flags)} flags")
        for flag in flags[:10]:
            print(flag)
    else:
        print("[INFO] No live complement flags emitted")

def get_scanner_status() -> ScannerStatus:
    return ScannerStatus(
        module="src.detect.prediction_scanner",
        status="week1_scaffold_in_progress",
        phase="Phase 1",
        implemented_now=[
            "config-driven scanner loop",
            "Polymarket current ingestion",
            "Kalshi current ingestion",
            "retry wrapper",
            "JSONL run logging",
        ],
        next_steps=[
            "cross-venue contract matching",
            "executable quote logic",
            "fee and slippage model",
            "structured opportunity logging",
            "replay/backtest",
        ],
    )


@dataclass
class ScannerRunEvent:
    ts_utc: str
    cycle_index: int
    cycle_start_utc: str
    cycle_end_utc: str
    duration_seconds: float
    polymarket_ok: bool
    kalshi_ok: bool
    polymarket_rows: int | None
    kalshi_rows: int | None
    polymarket_output: str | None
    kalshi_output: str | None
    error: str | None


def utc_now_iso() -> str:
    return datetime.now(UTC).isoformat()


def load_config(path: Path = CONFIG_PATH) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def safe_row_count(path_str: str | None) -> int | None:
    if not path_str:
        return None
    path = Path(path_str)
    if not path.exists():
        return None
    if path.suffix == ".parquet":
        try:
            df = pd.read_parquet(path)
            return int(len(df))
        except Exception:
            return None
    return None


def append_jsonl(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(payload) + "\n")

def maybe_fail_kalshi_once(config: dict[str, Any]) -> None:
    global _SIMULATED_KALSHI_FAILURE_ALREADY_USED

    should_fail = bool(config.get("simulate_kalshi_fail_once", False))
    if should_fail and not _SIMULATED_KALSHI_FAILURE_ALREADY_USED:
        _SIMULATED_KALSHI_FAILURE_ALREADY_USED = True
        raise RuntimeError("simulated transient Kalshi failure for retry test")
    
def run_one_cycle(config: dict[str, Any], cycle_index: int) -> ScannerRunEvent:
    retries = int(config.get("retry_attempts", 3))
    backoff_seconds = float(config.get("retry_backoff_seconds", 2))
    backoff_multiplier = float(config.get("retry_backoff_multiplier", 2))

    kalshi_limit = int(config.get("kalshi_limit", 1000))
    kalshi_max_pages = int(config.get("kalshi_max_pages", 5))
    kalshi_max_markets = int(config.get("kalshi_max_markets", 5000))

    polymarket_ok = False
    kalshi_ok = False
    polymarket_output = "data/processed/polymarket_markets_current.parquet"
    kalshi_output = "data/processed/kalshi_markets_current.parquet"
    error_msg = None

    cycle_start = utc_now_iso()
    t0 = time.perf_counter()

    try:
        retry_call(
            lambda: run_polymarket_current_ingestion(),
            retries=retries,
            backoff_seconds=backoff_seconds,
            backoff_multiplier=backoff_multiplier,
        )
        polymarket_ok = True
    except Exception as exc:
        error_msg = f"polymarket_ingest_failed: {exc}"

    try:
        retry_call(
            lambda: (
                maybe_fail_kalshi_once(config),
                run_kalshi_current_ingestion(
                    limit=kalshi_limit,
                    max_pages=kalshi_max_pages,
                    max_markets=kalshi_max_markets,
                ),
            )[-1],
            retries=retries,
            backoff_seconds=backoff_seconds,
            backoff_multiplier=backoff_multiplier,
        )
        kalshi_ok = True
    except Exception as exc:
        if error_msg is None:
            error_msg = f"kalshi_ingest_failed: {exc}"
        else:
            error_msg = f"{error_msg} | kalshi_ingest_failed: {exc}"

    duration_seconds = time.perf_counter() - t0
    cycle_end = utc_now_iso()

    event = ScannerRunEvent(
        ts_utc=cycle_end,
        cycle_index=cycle_index,
        cycle_start_utc=cycle_start,
        cycle_end_utc=cycle_end,
        duration_seconds=round(duration_seconds, 3),
        polymarket_ok=polymarket_ok,
        kalshi_ok=kalshi_ok,
        polymarket_rows=safe_row_count(polymarket_output) if polymarket_ok else None,
        kalshi_rows=safe_row_count(kalshi_output) if kalshi_ok else None,
        polymarket_output=polymarket_output if polymarket_ok else None,
        kalshi_output=kalshi_output if kalshi_ok else None,
        error=error_msg,
    )
    return event


def run_prediction_scanner_live() -> None:
    config = load_config()
    loop_interval_seconds = int(config.get("loop_interval_seconds", 300))
    max_cycles = int(config.get("max_cycles", 6))
    log_path = Path(config.get("log_path", "logs/prediction_scanner_runs.jsonl"))

    print("[INFO] Starting prediction scanner")
    print(f"[INFO] loop_interval_seconds={loop_interval_seconds}")
    print(f"[INFO] max_cycles={max_cycles}")
    print(f"[INFO] log_path={log_path}")

    for cycle_index in range(1, max_cycles + 1):
        print(f"\n[INFO] Cycle {cycle_index}/{max_cycles} started at {utc_now_iso()}")

        event = run_one_cycle(config, cycle_index)
        append_jsonl(log_path, asdict(event))

        print(
            f"[INFO] Cycle {cycle_index} result | "
            f"duration_seconds={event.duration_seconds} | "
            f"polymarket_ok={event.polymarket_ok} rows={event.polymarket_rows} | "
            f"kalshi_ok={event.kalshi_ok} rows={event.kalshi_rows}"
        )
        if event.error:
            print(f"[WARN] {event.error}")

        if cycle_index < max_cycles:
            time.sleep(loop_interval_seconds)

    print("\n[OK] Prediction scanner finished")


def run_prediction_scanner(mode: str = "live") -> None:
    if mode == "synthetic":
        run_prediction_scanner_synthetic()
    elif mode == "live":
        run_prediction_scanner_live()
    elif mode == "live_complement":
        run_prediction_scanner_live_complement()
    elif mode == "live_complement_polymarket":
        run_prediction_scanner_live_complement_polymarket()
    else:
        raise ValueError(f"Unknown scanner mode: {mode}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument(
    "--mode",
    choices=["live", "synthetic", "live_complement", "live_complement_polymarket"],
    default="live",
    help="Scanner mode: live ingestion loop, deterministic synthetic demo, or live Kalshi complement scan",
)
    args = parser.parse_args()

    run_prediction_scanner(mode=args.mode)
from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd
import yaml

from src.config.scanner_fee_config import get_default_fee_config
from src.detect.kalshi_live_complement import scan_kalshi_complements
from src.detect.opportunity_ranking import display_ranked_opportunities
from src.detect.logging_runner import build_synthetic_flags, write_flags_jsonl
from src.detect.polymarket_live_complement import scan_polymarket_complements
from src.ingest.kalshi_current import run_kalshi_current_ingestion
from src.ingest.polymarket_current import run_polymarket_current_ingestion
from src.utils.retry import retry_call
from src.ingest.polymarket_orderbook import run_polymarket_orderbook_ingestion
from src.ingest.polymarket_orderbook import PROCESSED_PATH as POLYMARKET_ORDERBOOKS_PATH

CONFIG_PATH = Path("configs/prediction_scanner.yaml")
DEFAULT_RUN_LOG_PATH = Path("logs/prediction_scanner_runs.jsonl")
DEFAULT_POLYMARKET_COMPLEMENT_LOG_PATH = Path("logs/polymarket_complement_runs.jsonl")
DEFAULT_POLYMARKET_COMPLEMENT_FLAG_LOG_PATH = Path("logs/polymarket_complement_flags.jsonl")

FEE_CONFIG = get_default_fee_config()

_SIMULATED_KALSHI_FAILURE_ALREADY_USED = False


@dataclass
class ScannerStatus:
    module: str
    status: str
    phase: str
    implemented_now: list[str]
    next_steps: list[str]


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


@dataclass
class ComplementRunEvent:
    ts_utc: str
    cycle_index: int
    cycle_start_utc: str
    cycle_end_utc: str
    duration_seconds: float
    orderbook_ingestion_ok: bool
    rows_total: int
    paired_markets: int
    markets_with_both_asks: int
    sufficient_size: int
    flags_emitted: int
    output_path: str | None
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
    if not path.exists() or path.suffix != ".parquet":
        return None

    try:
        df = pd.read_parquet(path)
        return int(len(df))
    except Exception:
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


def get_scanner_status() -> ScannerStatus:
    return ScannerStatus(
        module="src.detect.prediction_scanner",
        status="runtime_scaffold_connected",
        phase="Phase 1",
        implemented_now=[
            "config-driven scanner loops",
            "Polymarket and Kalshi current ingestion",
            "Kalshi live complement detection",
            "Polymarket live complement detection",
            "structured run and flag logging",
        ],
        next_steps=[
            "cross-venue contract matching",
            "richer live executable-book ingestion",
            "persistence and half-life analysis",
            "latency-aware replay validation",
            "alerting and packaging",
        ],
    )


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

    cycle_end = utc_now_iso()

    return ScannerRunEvent(
        ts_utc=cycle_end,
        cycle_index=cycle_index,
        cycle_start_utc=cycle_start,
        cycle_end_utc=cycle_end,
        duration_seconds=round(time.perf_counter() - t0, 3),
        polymarket_ok=polymarket_ok,
        kalshi_ok=kalshi_ok,
        polymarket_rows=safe_row_count(polymarket_output) if polymarket_ok else None,
        kalshi_rows=safe_row_count(kalshi_output) if kalshi_ok else None,
        polymarket_output=polymarket_output if polymarket_ok else None,
        kalshi_output=kalshi_output if kalshi_ok else None,
        error=error_msg,
    )


def run_one_polymarket_complement_cycle(
    cycle_index: int,
    limit_markets: int = 20,
    target_size: float = 10.0,
    threshold_bps: float = 10.0,
    scanner_config: dict[str, Any] | None = None,
) -> ComplementRunEvent:
    from src.ingest.polymarket_orderbook import run_polymarket_orderbook_ingestion

    cfg = scanner_config if scanner_config is not None else load_config()
    cycle_start = utc_now_iso()
    t0 = time.perf_counter()

    error_msg = None
    orderbook_ingestion_ok = False
    stats = {
        "rows_total": 0,
        "paired_markets": 0,
        "markets_with_both_asks": 0,
        "sufficient_size": 0,
        "flags_emitted": 0,
    }
    snapshot_output_path = None
    flags: list[dict[str, Any]] = []

    try:
        ingestion_result = run_polymarket_orderbook_ingestion(
            limit_markets=limit_markets,
            snapshot_ts_utc=cycle_start,
            persist_snapshot_copy=True,
        )
        orderbook_ingestion_ok = True
        snapshot_output_path = ingestion_result.get("snapshot_output_path")

        flags, stats = scan_polymarket_complements(
            path=Path(snapshot_output_path) if snapshot_output_path else POLYMARKET_ORDERBOOKS_PATH,
            target_size=target_size,
            threshold_bps=threshold_bps,
            fee_config=FEE_CONFIG,
        )

        if flags:
            append_live_flags_jsonl(
                flags=flags,
                log_path=DEFAULT_POLYMARKET_COMPLEMENT_FLAG_LOG_PATH,
                source="polymarket_live_complement",
                cycle_index=cycle_index,
                snapshot_output_path=snapshot_output_path,
                threshold_bps=threshold_bps,
            )
            display_ranked_opportunities(
                flags,
                config=cfg,
                title="Polymarket complement (single cycle)",
                cycle_index=cycle_index,
            )
    except Exception as exc:
        error_msg = str(exc)

    cycle_end = utc_now_iso()

    return ComplementRunEvent(
        ts_utc=cycle_end,
        cycle_index=cycle_index,
        cycle_start_utc=cycle_start,
        cycle_end_utc=cycle_end,
        duration_seconds=round(time.perf_counter() - t0, 3),
        orderbook_ingestion_ok=orderbook_ingestion_ok,
        rows_total=int(stats.get("rows_total", 0)),
        paired_markets=int(stats.get("paired_markets", 0)),
        markets_with_both_asks=int(stats.get("markets_with_both_asks", 0)),
        sufficient_size=int(stats.get("sufficient_size", 0)),
        flags_emitted=int(stats.get("flags_emitted", 0)),
        output_path=snapshot_output_path if orderbook_ingestion_ok else None,
        error=error_msg,
    )


def run_prediction_scanner_synthetic() -> None:
    print("[INFO] Starting prediction scanner in synthetic mode")

    flags = build_synthetic_flags()
    write_flags_jsonl(flags, source="synthetic_demo")

    print(f"[OK] Synthetic mode produced {len(flags)} flags")
    display_ranked_opportunities(flags, config=load_config(), title="Synthetic demo flags")


def run_prediction_scanner_live() -> None:
    config = load_config()
    loop_interval_seconds = int(config.get("loop_interval_seconds", 300))
    max_cycles = int(config.get("max_cycles", 6))
    log_path = Path(config.get("log_path", DEFAULT_RUN_LOG_PATH))

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


def run_prediction_scanner_live_complement() -> None:
    print("[INFO] Starting prediction scanner in live_complement mode")

    flags, stats = scan_kalshi_complements(
        target_size=1.0,
        threshold_bps=10.0,
        fee_config=FEE_CONFIG,
    )

    print(f"[INFO] Live complement stats: {stats}")

    if flags:
        write_flags_jsonl(flags, source="kalshi_live_complement")
        print(f"[OK] Live complement mode produced {len(flags)} flags")
        display_ranked_opportunities(
            flags,
            config=load_config(),
            title="Kalshi live complement",
        )
    else:
        print("[INFO] No live complement flags emitted")


def run_prediction_scanner_live_complement_polymarket() -> None:
    print("[INFO] Starting prediction scanner in live_complement_polymarket mode")

    config = load_config()
    event = run_one_polymarket_complement_cycle(
        cycle_index=1,
        limit_markets=int(config.get("polymarket_orderbook_limit_markets", 20)),
        target_size=float(config.get("polymarket_complement_target_size", 10.0)),
        threshold_bps=float(config.get("polymarket_complement_threshold_bps", 10.0)),
        scanner_config=config,
    )

    print(
        f"[INFO] Live Polymarket complement stats: "
        f"rows_total={event.rows_total}, "
        f"paired_markets={event.paired_markets}, "
        f"markets_with_both_asks={event.markets_with_both_asks}, "
        f"sufficient_size={event.sufficient_size}, "
        f"flags_emitted={event.flags_emitted}"
    )
    if event.error:
        print(f"[WARN] {event.error}")
    elif event.flags_emitted == 0:
        print("[INFO] No live Polymarket complement flags emitted")

def append_live_flags_jsonl(
    flags: list[dict],
    log_path: Path,
    source: str,
    cycle_index: int,
    snapshot_output_path: str | None,
    threshold_bps: float,
) -> None:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.touch(exist_ok=True)

    if not flags:
        return

    with log_path.open("a", encoding="utf-8") as f:
        for flag in flags:
            detected_ts = utc_now_iso()
            record = {
                "timestamp": detected_ts,
                "detected_ts_utc": detected_ts,
                "source": source,
                "snapshot_source": source,
                "snapshot_cycle_index": cycle_index,
                "snapshot_output_path": snapshot_output_path,
                "replay_lookup_key": flag.get("market_id"),
                "threshold_bps": threshold_bps,
                **flag,
            }
            f.write(json.dumps(record) + "\n")


def run_prediction_scanner_live_complement_polymarket_loop() -> None:
    print("[INFO] Starting prediction scanner in live_complement_polymarket_loop mode")

    config = load_config()
    loop_interval_seconds = int(config.get("loop_interval_seconds", 300))
    max_cycles = int(config.get("max_cycles", 6))
    log_path = Path(
        config.get("log_path_complement_polymarket", DEFAULT_POLYMARKET_COMPLEMENT_LOG_PATH)
    )
    flag_log_path = Path(
        config.get(
            "flag_log_path_complement_polymarket",
            DEFAULT_POLYMARKET_COMPLEMENT_FLAG_LOG_PATH,
        )
    )

    # Use YAML keys to avoid config drift across modes.
    limit_markets = int(config.get("polymarket_orderbook_limit_markets", 20))
    target_size = float(config.get("polymarket_complement_target_size", 10.0))
    threshold_bps = float(config.get("polymarket_complement_threshold_bps", 10.0))

    print(f"[INFO] loop_interval_seconds={loop_interval_seconds}")
    print(f"[INFO] max_cycles={max_cycles}")
    print(f"[INFO] limit_markets={limit_markets}")
    print(f"[INFO] target_size={target_size}")
    print(f"[INFO] threshold_bps={threshold_bps}")
    print(f"[INFO] log_path={log_path}")
    print(f"[INFO] flag_log_path={flag_log_path}")

    for cycle_index in range(1, max_cycles + 1):
        print(f"\n[INFO] Cycle {cycle_index}/{max_cycles} started at {utc_now_iso()}")

        cycle_start = utc_now_iso()
        t0 = time.perf_counter()
        error_msg = None
        flags: list[dict] = []
        stats = {
            "rows_total": 0,
            "paired_markets": 0,
            "markets_with_both_asks": 0,
            "sufficient_size": 0,
            "flags_emitted": 0,
        }
        orderbook_ingestion_ok = False
        snapshot_output_path = None

        try:
            ingestion_result = run_polymarket_orderbook_ingestion(
                limit_markets=limit_markets,
                snapshot_ts_utc=cycle_start,
                persist_snapshot_copy=True,
            )
            orderbook_ingestion_ok = True
            snapshot_output_path = ingestion_result.get("snapshot_output_path")

            flags, stats = scan_polymarket_complements(
                path=Path(snapshot_output_path) if snapshot_output_path else POLYMARKET_ORDERBOOKS_PATH,
                target_size=target_size,
                threshold_bps=threshold_bps,
                fee_config=FEE_CONFIG,
            )

            append_live_flags_jsonl(
                flags=flags,
                log_path=flag_log_path,
                source="live_complement_polymarket_loop",
                cycle_index=cycle_index,
                snapshot_output_path=snapshot_output_path,
                threshold_bps=threshold_bps,
            )
            display_ranked_opportunities(
                flags,
                config=config,
                title=f"Polymarket complement loop — cycle {cycle_index}/{max_cycles}",
                cycle_index=cycle_index,
            )
        except Exception as exc:
            error_msg = str(exc)

        cycle_end = utc_now_iso()
        event = ComplementRunEvent(
            ts_utc=cycle_end,
            cycle_index=cycle_index,
            cycle_start_utc=cycle_start,
            cycle_end_utc=cycle_end,
            duration_seconds=round(time.perf_counter() - t0, 3),
            orderbook_ingestion_ok=orderbook_ingestion_ok,
            rows_total=int(stats.get("rows_total", 0)),
            paired_markets=int(stats.get("paired_markets", 0)),
            markets_with_both_asks=int(stats.get("markets_with_both_asks", 0)),
            sufficient_size=int(stats.get("sufficient_size", 0)),
            flags_emitted=int(stats.get("flags_emitted", 0)),
            output_path=snapshot_output_path if orderbook_ingestion_ok else None,
            error=error_msg,
        )

        append_jsonl(log_path, asdict(event))

        print(
            f"[INFO] Cycle {cycle_index} result | "
            f"duration_seconds={event.duration_seconds} | "
            f"orderbook_ingestion_ok={event.orderbook_ingestion_ok} | "
            f"rows_total={event.rows_total} | "
            f"paired_markets={event.paired_markets} | "
            f"markets_with_both_asks={event.markets_with_both_asks} | "
            f"sufficient_size={event.sufficient_size} | "
            f"flags_emitted={event.flags_emitted}"
        )

        if event.error:
            print(f"[WARN] {event.error}")

        if cycle_index < max_cycles:
            time.sleep(loop_interval_seconds)

    print("\n[OK] Polymarket live complement loop finished")


def run_prediction_scanner(mode: str = "live") -> None:
    if mode == "synthetic":
        run_prediction_scanner_synthetic()
    elif mode == "live":
        run_prediction_scanner_live()
    elif mode == "live_complement":
        run_prediction_scanner_live_complement()
    elif mode == "live_complement_polymarket":
        run_prediction_scanner_live_complement_polymarket()
    elif mode == "live_complement_polymarket_loop":
        run_prediction_scanner_live_complement_polymarket_loop()
    else:
        raise ValueError(f"Unknown scanner mode: {mode}")

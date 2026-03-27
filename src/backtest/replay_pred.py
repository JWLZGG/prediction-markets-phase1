from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta
from functools import lru_cache
from pathlib import Path
from statistics import median
from typing import Any

from src.config.scanner_fee_config import get_default_fee_config
from src.detect.edge import compute_complement_edge
from src.detect.executable_pricing import get_executable_buy_price
from src.detect.fees import compute_fee_breakdown, compute_notional
from src.detect.polymarket_live_complement import (
    load_polymarket_orderbooks,
    pair_market_books,
)
from src.ingest.polymarket_orderbook import SNAPSHOT_DIR as POLYMARKET_SNAPSHOT_DIR


INPUT_FLAGS_PATHS = [
    Path("logs/polymarket_complement_flags.jsonl"),
    Path("logs/prediction_scanner_flags.jsonl"),
]
OUTPUT_ROWS_CSV = Path("artifacts/outputs/replay_pred_rows.csv")
OUTPUT_SUMMARY_JSON = Path("artifacts/outputs/replay_pred_summary.json")
OUTPUT_SUMMARY_MD = Path("reports/replay_pred_summary.md")

LATENCY_SECONDS = [1, 5, 10]
SNAPSHOT_NAME_RE = re.compile(
    r"polymarket_orderbooks_(\d{8})T(\d{6})(\d{0,6})(?:Z|\+0000)?\.parquet$"
)
SUPPORTED_COMPLEMENT_SOURCES = {
    "live_complement_polymarket_loop",
    "polymarket_live_complement",
    "polymarket_live_complement_backfill",
}
FEE_CONFIG = get_default_fee_config()


@dataclass
class ReplayRow:
    source_flag_type: str
    market_id: str
    pair_id: str | None
    target_size: float
    size_bucket: str
    latency_seconds: int
    source: str | None
    original_buy_price: float | None
    original_sell_price: float | None
    original_net_edge: float | None
    original_total_cost: float | None
    replay_mode: str
    replay_status: str
    snapshot_output_path: str | None
    later_snapshot_path: str | None
    later_snapshot_ts_utc: str | None
    observed_state_found: bool
    replayable: bool
    later_state_executable: bool
    replayed_buy_price: float | None
    replayed_sell_price: float | None
    replayed_gross_edge: float | None
    replayed_total_cost: float | None
    replayed_net_edge: float | None
    replayed_net_edge_bps: float | None
    still_positive: bool
    false_positive: bool


@dataclass
class ReplaySummary:
    flags_input: int
    replay_rows: int
    latency_scenarios: list[int]
    avg_original_net_edge: float | None
    half_life_seconds: int | None
    observed_state_rows: int
    replayable_rows: int
    status_counts: dict[str, int]
    by_latency: list[dict[str, Any]]
    by_size_and_latency: list[dict[str, Any]]


@dataclass
class ReplayStatus:
    module: str
    status: str
    phase: str
    implemented_now: list[str]
    next_steps: list[str]


def _r(x: float | None, ndigits: int = 6) -> float | None:
    if x is None:
        return None
    return round(float(x), ndigits)


def _size_bucket(target_size: float) -> str:
    size = float(target_size)
    if size <= 10:
        return "small"
    if size <= 100:
        return "medium"
    return "large"


def _extract_market_id(flag: dict[str, Any]) -> str:
    if flag.get("market_id") is not None:
        return str(flag["market_id"])
    if flag.get("pair_id") is not None:
        return str(flag["pair_id"])
    return "unknown"


def _extract_pair_id(flag: dict[str, Any]) -> str | None:
    value = flag.get("pair_id")
    if value is None:
        return None
    return str(value)


def _extract_buy_sell_prices(flag: dict[str, Any]) -> tuple[float | None, float | None]:
    details = flag.get("details", {})

    if "buy_avg_price" in details and "sell_avg_price" in details:
        return float(details["buy_avg_price"]), float(details["sell_avg_price"])

    if "yes_buy_avg_price" in details and "no_buy_avg_price" in details:
        yes_price = float(details["yes_buy_avg_price"])
        no_price = float(details["no_buy_avg_price"])
        return yes_price + no_price, 1.0

    return None, None


def _extract_total_cost(flag: dict[str, Any]) -> float | None:
    details = flag.get("details", {})
    value = details.get("total_cost")
    if value is None:
        return None
    return float(value)


def _extract_original_net_edge(flag: dict[str, Any]) -> float | None:
    details = flag.get("details", {})
    value = details.get("net_edge")
    if value is None:
        return None
    return float(value)


def _extract_detection_ts(flag: dict[str, Any]) -> datetime | None:
    for key in ("detected_ts_utc", "timestamp", "ts_utc"):
        value = flag.get(key)
        if not value:
            continue
        try:
            return datetime.fromisoformat(str(value))
        except ValueError:
            continue
    return None


def _parse_snapshot_timestamp(path: Path) -> datetime | None:
    match = SNAPSHOT_NAME_RE.match(path.name)
    if not match:
        return None

    date_part, time_part, micros = match.groups()
    micros = (micros or "").ljust(6, "0")
    try:
        dt = datetime.strptime(date_part + time_part + micros, "%Y%m%d%H%M%S%f")
    except ValueError:
        return None
    return dt.replace(tzinfo=UTC)


def _snapshot_dir_candidates(flag: dict[str, Any]) -> list[Path]:
    candidates: list[Path] = []
    snapshot_output_path = flag.get("snapshot_output_path")
    if snapshot_output_path:
        snapshot_path = Path(str(snapshot_output_path))
        if snapshot_path.parent not in candidates:
            candidates.append(snapshot_path.parent)

    if POLYMARKET_SNAPSHOT_DIR not in candidates:
        candidates.append(POLYMARKET_SNAPSHOT_DIR)

    return candidates


@lru_cache(maxsize=16)
def _snapshot_index(snapshot_dir_str: str) -> tuple[tuple[str, str], ...]:
    snapshot_dir = Path(snapshot_dir_str)
    if not snapshot_dir.exists():
        return tuple()

    items: list[tuple[str, str]] = []
    for path in snapshot_dir.glob("polymarket_orderbooks_*.parquet"):
        ts = _parse_snapshot_timestamp(path)
        if ts is None:
            continue
        items.append((ts.isoformat(), str(path)))

    items.sort()
    return tuple(items)


def _find_later_snapshot_for_flag(
    flag: dict[str, Any],
    latency_seconds: int,
) -> tuple[Path | None, datetime | None]:
    detected_ts = _extract_detection_ts(flag)
    if detected_ts is None:
        return None, None

    target_ts = detected_ts + timedelta(seconds=int(latency_seconds))
    for snapshot_dir in _snapshot_dir_candidates(flag):
        for ts_iso, path_str in _snapshot_index(str(snapshot_dir)):
            ts = datetime.fromisoformat(ts_iso)
            if ts >= target_ts:
                return Path(path_str), ts
    return None, None


@lru_cache(maxsize=64)
def _load_paired_books(snapshot_path_str: str) -> dict[str, dict[str, Any]]:
    snapshot_path = Path(snapshot_path_str)
    df = load_polymarket_orderbooks(snapshot_path)
    pairs = pair_market_books(df)
    return {str(pair["market_id"]): pair for pair in pairs}


def _recompute_complement_with_observed_state(
    flag: dict[str, Any],
    later_snapshot_path: Path,
) -> dict[str, Any]:
    pairs = _load_paired_books(str(later_snapshot_path))
    market = pairs.get(_extract_market_id(flag))
    if market is None:
        return {
            "replay_status": "market_missing_in_later_snapshot",
            "observed_state_found": False,
            "replayable": False,
            "later_state_executable": False,
            "replayed_buy_price": None,
            "replayed_sell_price": None,
            "replayed_gross_edge": None,
            "replayed_total_cost": None,
            "replayed_net_edge": None,
            "replayed_net_edge_bps": None,
            "still_positive": False,
            "false_positive": False,
        }

    target_size = float(flag.get("target_size", 0.0))
    yes_result = get_executable_buy_price(market["yes_asks"], target_size=target_size)
    no_result = get_executable_buy_price(market["no_asks"], target_size=target_size)

    if (
        not yes_result.executable
        or not no_result.executable
        or yes_result.avg_price is None
        or no_result.avg_price is None
    ):
        return {
            "replay_status": "insufficient_later_liquidity",
            "observed_state_found": True,
            "replayable": False,
            "later_state_executable": False,
            "replayed_buy_price": None,
            "replayed_sell_price": None,
            "replayed_gross_edge": None,
            "replayed_total_cost": None,
            "replayed_net_edge": None,
            "replayed_net_edge_bps": None,
            "still_positive": False,
            "false_positive": False,
        }

    yes_notional = compute_notional(yes_result.avg_price, target_size)
    no_notional = compute_notional(no_result.avg_price, target_size)
    yes_fee = compute_fee_breakdown("polymarket", yes_notional, FEE_CONFIG)
    no_fee = compute_fee_breakdown("polymarket", no_notional, FEE_CONFIG)
    total_cost_per_unit = (yes_fee.total_cost + no_fee.total_cost) / float(target_size)
    edge_result = compute_complement_edge(
        yes_buy_price=yes_result.avg_price,
        no_buy_price=no_result.avg_price,
        total_cost=total_cost_per_unit,
        threshold_bps=0.0,
    )

    original_net_edge = _extract_original_net_edge(flag) or 0.0
    still_positive = edge_result.net_edge > 0.0
    false_positive = original_net_edge > 0.0 and edge_result.net_edge <= 0.0
    replay_status = "still_positive" if still_positive else "false_positive"

    return {
        "replay_status": replay_status,
        "observed_state_found": True,
        "replayable": True,
        "later_state_executable": True,
        "replayed_buy_price": yes_result.avg_price + no_result.avg_price,
        "replayed_sell_price": 1.0,
        "replayed_gross_edge": edge_result.gross_edge,
        "replayed_total_cost": edge_result.total_cost,
        "replayed_net_edge": edge_result.net_edge,
        "replayed_net_edge_bps": edge_result.net_edge_bps,
        "still_positive": still_positive,
        "false_positive": false_positive,
    }


def _supports_observed_state_replay(flag: dict[str, Any]) -> bool:
    if str(flag.get("flag_type", "")) != "complement_sanity":
        return False

    if not flag.get("snapshot_output_path"):
        return False

    if _extract_detection_ts(flag) is None:
        return False

    source = str(flag.get("source", "") or "")
    if not source:
        return True

    return source in SUPPORTED_COMPLEMENT_SOURCES or "polymarket" in source


def load_flag_logs(paths: list[Path] = INPUT_FLAGS_PATHS) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path in paths:
        if not path.exists():
            continue
        with path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                rows.append(json.loads(line))
    return rows


def replay_flag(
    flag: dict[str, Any],
    latency_seconds: int,
) -> ReplayRow:
    original_buy_price, original_sell_price = _extract_buy_sell_prices(flag)
    original_total_cost = _extract_total_cost(flag)
    original_net_edge = _extract_original_net_edge(flag)
    source = flag.get("source")
    snapshot_output_path = flag.get("snapshot_output_path")

    base = {
        "source_flag_type": str(flag.get("flag_type", "unknown")),
        "market_id": _extract_market_id(flag),
        "pair_id": _extract_pair_id(flag),
        "target_size": float(flag.get("target_size", 0.0)),
        "size_bucket": _size_bucket(float(flag.get("target_size", 0.0))),
        "latency_seconds": int(latency_seconds),
        "source": str(source) if source is not None else None,
        "original_buy_price": original_buy_price,
        "original_sell_price": original_sell_price,
        "original_net_edge": original_net_edge,
        "original_total_cost": original_total_cost,
        "snapshot_output_path": str(snapshot_output_path) if snapshot_output_path else None,
    }

    if not _supports_observed_state_replay(flag):
        return ReplayRow(
            replay_mode="unsupported",
            replay_status="unsupported_no_observed_state_path",
            later_snapshot_path=None,
            later_snapshot_ts_utc=None,
            observed_state_found=False,
            replayable=False,
            later_state_executable=False,
            replayed_buy_price=None,
            replayed_sell_price=None,
            replayed_gross_edge=None,
            replayed_total_cost=None,
            replayed_net_edge=None,
            replayed_net_edge_bps=None,
            still_positive=False,
            false_positive=False,
            **base,
        )

    later_snapshot_path, later_snapshot_ts = _find_later_snapshot_for_flag(
        flag,
        latency_seconds=latency_seconds,
    )
    if later_snapshot_path is None or later_snapshot_ts is None:
        return ReplayRow(
            replay_mode="observed_latency_replay",
            replay_status="missing_later_snapshot",
            later_snapshot_path=None,
            later_snapshot_ts_utc=None,
            observed_state_found=False,
            replayable=False,
            later_state_executable=False,
            replayed_buy_price=None,
            replayed_sell_price=None,
            replayed_gross_edge=None,
            replayed_total_cost=None,
            replayed_net_edge=None,
            replayed_net_edge_bps=None,
            still_positive=False,
            false_positive=False,
            **base,
        )

    replay = _recompute_complement_with_observed_state(flag, later_snapshot_path)
    return ReplayRow(
        replay_mode="observed_latency_replay",
        later_snapshot_path=str(later_snapshot_path),
        later_snapshot_ts_utc=later_snapshot_ts.isoformat(),
        **replay,
        **base,
    )


def estimate_half_life_seconds(replay_rows: list[ReplayRow]) -> int | None:
    replayable_rows = [row for row in replay_rows if row.replayable]
    if not replayable_rows:
        return None

    latencies = sorted({row.latency_seconds for row in replayable_rows})
    for latency in latencies:
        subset = [row for row in replayable_rows if row.latency_seconds == latency]
        if not subset:
            continue
        share_lost = sum(1 for row in subset if not row.still_positive) / len(subset)
        if share_lost >= 0.5:
            return latency
    return None


def _build_group_metrics(
    replay_rows: list[ReplayRow],
    *,
    latency_seconds: int,
    size_bucket: str | None = None,
) -> dict[str, Any]:
    subset = [row for row in replay_rows if row.latency_seconds == latency_seconds]
    if size_bucket is not None:
        subset = [row for row in subset if row.size_bucket == size_bucket]

    replayable_subset = [row for row in subset if row.replayable]
    false_positive_rate = None
    still_positive_rate = None
    avg_replayed_net_edge = None
    median_replayed_net_edge = None

    if replayable_subset:
        false_positive_rate = sum(1 for row in replayable_subset if row.false_positive) / len(
            replayable_subset
        )
        still_positive_rate = sum(1 for row in replayable_subset if row.still_positive) / len(
            replayable_subset
        )
        avg_replayed_net_edge = sum(
            row.replayed_net_edge or 0.0 for row in replayable_subset
        ) / len(replayable_subset)
        median_replayed_net_edge = median(
            row.replayed_net_edge for row in replayable_subset if row.replayed_net_edge is not None
        )

    metrics = {
        "latency_seconds": latency_seconds,
        "rows": len(subset),
        "observed_state_rows": sum(1 for row in subset if row.observed_state_found),
        "replayable_rows": len(replayable_subset),
        "missing_later_snapshot_rows": sum(
            1 for row in subset if row.replay_status == "missing_later_snapshot"
        ),
        "insufficient_later_liquidity_rows": sum(
            1 for row in subset if row.replay_status == "insufficient_later_liquidity"
        ),
        "unsupported_rows": sum(
            1 for row in subset if row.replay_status == "unsupported_no_observed_state_path"
        ),
        "avg_replayed_net_edge": _r(avg_replayed_net_edge, 6),
        "median_replayed_net_edge": _r(median_replayed_net_edge, 6),
        "false_positive_rate": _r(false_positive_rate, 6),
        "still_positive_rate": _r(still_positive_rate, 6),
    }
    if size_bucket is not None:
        metrics["size_bucket"] = size_bucket

    return metrics


def build_summary(
    flags: list[dict[str, Any]],
    replay_rows: list[ReplayRow],
) -> ReplaySummary:
    original_edges = [
        row.original_net_edge
        for row in replay_rows
        if row.original_net_edge is not None
    ]
    avg_original_net_edge = None
    if original_edges:
        avg_original_net_edge = sum(original_edges) / len(original_edges)

    latencies = sorted({row.latency_seconds for row in replay_rows})
    size_buckets = sorted({row.size_bucket for row in replay_rows})
    status_counts: dict[str, int] = {}
    for row in replay_rows:
        status_counts[row.replay_status] = status_counts.get(row.replay_status, 0) + 1

    by_latency = [
        _build_group_metrics(replay_rows, latency_seconds=latency)
        for latency in latencies
    ]

    by_size_and_latency: list[dict[str, Any]] = []
    for size_bucket in size_buckets:
        for latency in latencies:
            by_size_and_latency.append(
                _build_group_metrics(
                    replay_rows,
                    latency_seconds=latency,
                    size_bucket=size_bucket,
                )
            )

    return ReplaySummary(
        flags_input=len(flags),
        replay_rows=len(replay_rows),
        latency_scenarios=latencies,
        avg_original_net_edge=_r(avg_original_net_edge, 6),
        half_life_seconds=estimate_half_life_seconds(replay_rows),
        observed_state_rows=sum(1 for row in replay_rows if row.observed_state_found),
        replayable_rows=sum(1 for row in replay_rows if row.replayable),
        status_counts=status_counts,
        by_latency=by_latency,
        by_size_and_latency=by_size_and_latency,
    )


def write_replay_outputs(
    replay_rows: list[ReplayRow],
    summary: ReplaySummary,
) -> None:
    OUTPUT_ROWS_CSV.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_SUMMARY_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_SUMMARY_MD.parent.mkdir(parents=True, exist_ok=True)

    if replay_rows:
        headers = list(asdict(replay_rows[0]).keys())
        lines = [",".join(headers)]
        for row in replay_rows:
            row_dict = asdict(row)
            values: list[str] = []
            for header in headers:
                value = row_dict[header]
                if value is None:
                    values.append("")
                else:
                    values.append(str(value).replace(",", ";"))
            lines.append(",".join(values))
        OUTPUT_ROWS_CSV.write_text("\n".join(lines) + "\n", encoding="utf-8")
    else:
        OUTPUT_ROWS_CSV.write_text("", encoding="utf-8")

    OUTPUT_SUMMARY_JSON.write_text(
        json.dumps(asdict(summary), indent=2),
        encoding="utf-8",
    )

    lines = [
        "# Replay Summary",
        "",
        f"- Flags input: {summary.flags_input}",
        f"- Replay rows: {summary.replay_rows}",
        f"- Observed-state rows: {summary.observed_state_rows}",
        f"- Replayable rows: {summary.replayable_rows}",
        f"- Latency scenarios: {summary.latency_scenarios}",
        f"- Average original net edge: {summary.avg_original_net_edge}",
        f"- Estimated half-life (seconds): {summary.half_life_seconds}",
        "",
        "## Status counts",
        "",
        "| Replay status | Rows |",
        "|---|---:|",
    ]

    for status, count in sorted(summary.status_counts.items()):
        lines.append(f"| {status} | {count} |")

    lines.extend(
        [
            "",
            "## By latency",
            "",
            "| Latency (s) | Rows | Observed-state rows | Replayable rows | Missing later snapshot | Insufficient later liquidity | Unsupported rows | Avg replayed net edge | Median replayed net edge | False positive rate | Still positive rate |",
            "|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
        ]
    )

    for item in summary.by_latency:
        lines.append(
            f"| {item['latency_seconds']} | {item['rows']} | {item['observed_state_rows']} | "
            f"{item['replayable_rows']} | {item['missing_later_snapshot_rows']} | "
            f"{item['insufficient_later_liquidity_rows']} | {item['unsupported_rows']} | "
            f"{item['avg_replayed_net_edge']} | {item['median_replayed_net_edge']} | "
            f"{item['false_positive_rate']} | {item['still_positive_rate']} |"
        )

    lines.extend(
        [
            "",
            "## By size and latency",
            "",
            "| Size bucket | Latency (s) | Rows | Replayable rows | False positive rate | Still positive rate |",
            "|---|---:|---:|---:|---:|---:|",
        ]
    )
    for item in summary.by_size_and_latency:
        lines.append(
            f"| {item['size_bucket']} | {item['latency_seconds']} | {item['rows']} | "
            f"{item['replayable_rows']} | {item['false_positive_rate']} | {item['still_positive_rate']} |"
        )

    lines.extend(
        [
            "",
            "## Conclusion",
            "",
            "Replay now prefers observed later-state snapshots for supported Polymarket complement flags.",
            "Rows without a later snapshot or without replayable live metadata are kept in the output with explicit statuses instead of being silently penalized by a proxy model.",
            "",
        ]
    )

    OUTPUT_SUMMARY_MD.write_text("\n".join(lines), encoding="utf-8")


def replay_flags(
    flags: list[dict[str, Any]],
    latency_grid: list[int] | None = None,
) -> tuple[list[ReplayRow], ReplaySummary]:
    if latency_grid is None:
        latency_grid = LATENCY_SECONDS

    replay_rows: list[ReplayRow] = []
    for flag in flags:
        for latency_seconds in latency_grid:
            replay_rows.append(replay_flag(flag, latency_seconds=latency_seconds))

    summary = build_summary(flags, replay_rows)
    return replay_rows, summary


def get_replay_status() -> ReplayStatus:
    return ReplayStatus(
        module="src.backtest.replay_pred",
        status="observed_state_replay_connected",
        phase="Phase 1",
        implemented_now=[
            "JSONL flag replay from live and sample logs",
            "observed-state latency replay for supported Polymarket complement flags",
            "explicit unsupported/missing-data replay statuses",
            "false positive and still-positive estimation",
            "size-by-latency summary metrics",
            "CSV/JSON/Markdown replay outputs",
        ],
        next_steps=[
            "extend observed-state replay to cross-venue matched flags",
            "retain richer historical Kalshi quote snapshots for true cross-venue replay",
            "increase real flag volume so replay metrics are driven by live opportunities, not only support scaffolding",
        ],
    )


def run_replay_pred() -> None:
    main()


def main() -> None:
    flags = load_flag_logs()
    replay_rows, summary = replay_flags(flags)
    write_replay_outputs(replay_rows, summary)

    print("[INFO] Replay finished")
    print(f"[INFO] Flags input: {summary.flags_input}")
    print(f"[INFO] Replay rows: {summary.replay_rows}")
    print(f"[INFO] Observed-state rows: {summary.observed_state_rows}")
    print(f"[INFO] Replayable rows: {summary.replayable_rows}")
    print(f"[INFO] Half-life (seconds): {summary.half_life_seconds}")
    print(f"[INFO] Wrote CSV: {OUTPUT_ROWS_CSV}")
    print(f"[INFO] Wrote JSON summary: {OUTPUT_SUMMARY_JSON}")
    print(f"[INFO] Wrote markdown summary: {OUTPUT_SUMMARY_MD}")


if __name__ == "__main__":
    main()

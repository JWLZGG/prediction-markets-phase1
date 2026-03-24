from __future__ import annotations

import json
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any

from src.detect.edge import compute_complement_edge, compute_cross_venue_edge

FLAG_LOG_PATH = Path("logs/prediction_scanner_flags.jsonl")
OUTPUT_PATH = Path("reports/replay_pred_summary.md")

LATENCY_SCENARIOS = [
    ("250ms", 0.25),
    ("1s", 1.0),
    ("3s", 3.0),
]


@dataclass
class ReplayResult:
    latency_label: str
    latency_seconds: float
    replay_mode: str
    flag_type: str
    market_id: str
    original_net_edge: float | None
    recomputed_net_edge: float | None
    edge_diff: float | None
    still_positive: bool | None
    false_positive: bool | None
    consistent: bool
    note: str


def load_flag_events(path: Path = FLAG_LOG_PATH) -> list[dict[str, Any]]:
    if not path.exists():
        return []

    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        rows.append(json.loads(line))
    return rows


def reconstruct_detection_inputs(flag: dict[str, Any]) -> dict[str, Any]:
    return {
        "timestamp": flag.get("timestamp"),
        "flag_type": flag.get("flag_type"),
        "market_id": flag.get("market_id"),
        "venue_a": flag.get("venue_a"),
        "venue_b": flag.get("venue_b"),
        "target_size": flag.get("target_size"),
        "threshold_bps": flag.get("threshold_bps"),
        "details": flag.get("details", {}),
        "inputs": flag.get("inputs", {}),
    }


def recompute_flag_from_logged_inputs(flag_inputs: dict[str, Any]) -> tuple[float | None, str]:
    flag_type = flag_inputs["flag_type"]
    details = flag_inputs.get("details", {})

    if flag_type == "cross_venue_divergence":
        buy_avg_price = details.get("buy_avg_price")
        sell_avg_price = details.get("sell_avg_price")
        total_cost = details.get("total_cost")

        if any(v is None for v in [buy_avg_price, sell_avg_price, total_cost]):
            return None, "missing required cross-venue fields in logged details"

        edge = compute_cross_venue_edge(
            buy_price=float(buy_avg_price),
            sell_price=float(sell_avg_price),
            total_cost=float(total_cost),
            threshold_bps=0.0,
        )
        return float(edge.net_edge), "ok"

    if flag_type == "complement_sanity":
        yes_buy_avg_price = details.get("yes_buy_avg_price")
        no_buy_avg_price = details.get("no_buy_avg_price")
        total_cost = details.get("total_cost")

        if any(v is None for v in [yes_buy_avg_price, no_buy_avg_price, total_cost]):
            return None, "missing required complement fields in logged details"

        edge = compute_complement_edge(
            yes_buy_price=float(yes_buy_avg_price),
            no_buy_price=float(no_buy_avg_price),
            total_cost=float(total_cost),
            threshold_bps=0.0,
        )
        return float(edge.net_edge), "ok"

    return None, "unsupported flag type"


def recompute_flag_at_latency(
    flag_inputs: dict[str, Any],
    latency_label: str,
    latency_seconds: float,
) -> ReplayResult:
    market_id = str(flag_inputs["market_id"])
    flag_type = str(flag_inputs["flag_type"])
    details = flag_inputs.get("details", {})
    original_net_edge = details.get("net_edge")

    recomputed_net_edge, note = recompute_flag_from_logged_inputs(flag_inputs)

    if original_net_edge is None:
        return ReplayResult(
            latency_label=latency_label,
            latency_seconds=latency_seconds,
            replay_mode="deterministic_proxy",
            flag_type=flag_type,
            market_id=market_id,
            original_net_edge=None,
            recomputed_net_edge=recomputed_net_edge,
            edge_diff=None,
            still_positive=None,
            false_positive=None,
            consistent=False,
            note="original net edge missing",
        )

    if recomputed_net_edge is None:
        return ReplayResult(
            latency_label=latency_label,
            latency_seconds=latency_seconds,
            replay_mode="deterministic_proxy",
            flag_type=flag_type,
            market_id=market_id,
            original_net_edge=float(original_net_edge),
            recomputed_net_edge=None,
            edge_diff=None,
            still_positive=None,
            false_positive=None,
            consistent=False,
            note=note,
        )

    edge_diff = recomputed_net_edge - float(original_net_edge)
    consistent = abs(edge_diff) < 1e-5
    still_positive = recomputed_net_edge > 0
    false_positive = recomputed_net_edge <= 0

    return ReplayResult(
        latency_label=latency_label,
        latency_seconds=latency_seconds,
        replay_mode="deterministic_proxy",
        flag_type=flag_type,
        market_id=market_id,
        original_net_edge=float(original_net_edge),
        recomputed_net_edge=recomputed_net_edge,
        edge_diff=edge_diff,
        still_positive=still_positive,
        false_positive=false_positive,
        consistent=consistent,
        note="ok" if consistent else "recomputed edge differs from logged edge",
    )


def summarize_results(results: list[ReplayResult]) -> dict[str, Any]:
    total = len(results)
    consistent = sum(1 for r in results if r.consistent)
    still_positive = sum(1 for r in results if r.still_positive is True)
    false_positive = sum(1 for r in results if r.false_positive is True)

    by_latency: dict[str, dict[str, int]] = {}
    for r in results:
        bucket = by_latency.setdefault(
            r.latency_label,
            {
                "total": 0,
                "consistent": 0,
                "still_positive": 0,
                "false_positive": 0,
            },
        )
        bucket["total"] += 1
        if r.consistent:
            bucket["consistent"] += 1
        if r.still_positive is True:
            bucket["still_positive"] += 1
        if r.false_positive is True:
            bucket["false_positive"] += 1

    return {
        "total_replay_rows": total,
        "consistent_recomputations": consistent,
        "still_positive_count": still_positive,
        "false_positive_count": false_positive,
        "by_latency": by_latency,
    }


def write_summary(results: list[ReplayResult], summary: dict[str, Any]) -> None:
    lines = [
        "# Replay Summary",
        "",
        "Phase B scaffold: latency-labelled replay using deterministic logged-state recomputation.",
        "",
        "Current replay mode is `deterministic_proxy`, which means recomputation uses the logged detector inputs rather than a later observed market state.",
        "This is the correct intermediate step before wiring true `t + latency` snapshot lookups.",
        "",
        f"- Total replay rows: {summary['total_replay_rows']}",
        f"- Consistent recomputations: {summary['consistent_recomputations']}",
        f"- Still-positive count: {summary['still_positive_count']}",
        f"- False-positive count: {summary['false_positive_count']}",
        "",
        "## By latency",
        "",
    ]

    for latency_label, stats in summary["by_latency"].items():
        lines.extend([
            f"### {latency_label}",
            f"- Total: {stats['total']}",
            f"- Consistent: {stats['consistent']}",
            f"- Still positive: {stats['still_positive']}",
            f"- False positive: {stats['false_positive']}",
            "",
        ])

    lines.extend([
        "## Detailed results",
        "",
        "| latency | replay_mode | flag_type | market_id | original_net_edge | recomputed_net_edge | edge_diff | still_positive | false_positive | consistent | note |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ])

    for r in results:
        lines.append(
            f"| {r.latency_label} | {r.replay_mode} | {r.flag_type} | {r.market_id} | "
            f"{'' if r.original_net_edge is None else f'{r.original_net_edge:.6f}'} | "
            f"{'' if r.recomputed_net_edge is None else f'{r.recomputed_net_edge:.6f}'} | "
            f"{'' if r.edge_diff is None else f'{r.edge_diff:.6f}'} | "
            f"{r.still_positive} | {r.false_positive} | {r.consistent} | {r.note} |"
        )

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text("\n".join(lines), encoding="utf-8")


def run_replay_pred() -> None:
    flags = load_flag_events()
    if not flags:
        print("[WARN] No flag events found for replay.")
        return

    results: list[ReplayResult] = []

    for flag in flags:
        inputs = reconstruct_detection_inputs(flag)
        for latency_label, latency_seconds in LATENCY_SCENARIOS:
            results.append(
                recompute_flag_at_latency(
                    flag_inputs=inputs,
                    latency_label=latency_label,
                    latency_seconds=latency_seconds,
                )
            )

    summary = summarize_results(results)
    write_summary(results, summary)

    print("[OK] Wrote replay summary to reports/replay_pred_summary.md")
    print("[INFO] Replay summary:")
    print(summary)
    for r in results[:10]:
        print(asdict(r))


if __name__ == "__main__":
    run_replay_pred()
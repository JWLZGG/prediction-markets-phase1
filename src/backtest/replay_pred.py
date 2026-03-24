from __future__ import annotations

import json
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any

from src.detect.edge import compute_complement_edge, compute_cross_venue_edge


FLAG_LOG_PATH = Path("logs/prediction_scanner_flags.jsonl")
OUTPUT_PATH = Path("reports/replay_pred_summary.md")


@dataclass
class ReplayResult:
    flag_type: str
    market_id: str
    original_net_edge: float | None
    recomputed_net_edge: float | None
    edge_diff: float | None
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
    details = flag.get("details", {})
    return {
        "flag_type": flag.get("flag_type"),
        "market_id": flag.get("market_id"),
        "venue_a": flag.get("venue_a"),
        "venue_b": flag.get("venue_b"),
        "target_size": flag.get("target_size"),
        "details": details,
    }


def recompute_flag_deterministic(flag_inputs: dict[str, Any]) -> ReplayResult:
    flag_type = flag_inputs["flag_type"]
    market_id = str(flag_inputs["market_id"])
    details = flag_inputs.get("details", {})

    original_net_edge = details.get("net_edge")

    if flag_type == "cross_venue_divergence":
        buy_avg_price = details.get("buy_avg_price")
        sell_avg_price = details.get("sell_avg_price")
        total_cost = details.get("total_cost")

        if any(v is None for v in [buy_avg_price, sell_avg_price, total_cost]):
            return ReplayResult(
                flag_type=flag_type,
                market_id=market_id,
                original_net_edge=original_net_edge,
                recomputed_net_edge=None,
                edge_diff=None,
                consistent=False,
                note="missing required cross-venue fields in logged details",
            )

        edge = compute_cross_venue_edge(
        buy_price=float(buy_avg_price),
        sell_price=float(sell_avg_price),
        total_cost=float(total_cost),
        threshold_bps=0.0,
        )

        recomputed_net_edge = float(edge.net_edge)

    elif flag_type == "complement_sanity":
        yes_buy_avg_price = details.get("yes_buy_avg_price")
        no_buy_avg_price = details.get("no_buy_avg_price")
        total_cost = details.get("total_cost")

        if any(v is None for v in [yes_buy_avg_price, no_buy_avg_price, total_cost]):
            return ReplayResult(
                flag_type=flag_type,
                market_id=market_id,
                original_net_edge=original_net_edge,
                recomputed_net_edge=None,
                edge_diff=None,
                consistent=False,
                note="missing required complement fields in logged details",
            )

        edge = compute_complement_edge(
        yes_buy_price=float(yes_buy_avg_price),
        no_buy_price=float(no_buy_avg_price),
        total_cost=float(total_cost),
        threshold_bps=0.0,
        )

        recomputed_net_edge = float(edge.net_edge)

    else:
        return ReplayResult(
            flag_type=flag_type,
            market_id=market_id,
            original_net_edge=original_net_edge,
            recomputed_net_edge=None,
            edge_diff=None,
            consistent=False,
            note="unsupported flag type",
        )

    if original_net_edge is None:
        return ReplayResult(
            flag_type=flag_type,
            market_id=market_id,
            original_net_edge=None,
            recomputed_net_edge=recomputed_net_edge,
            edge_diff=None,
            consistent=False,
            note="original net edge missing",
        )

    edge_diff = recomputed_net_edge - float(original_net_edge)
    consistent = abs(edge_diff) < 1e-4

    return ReplayResult(
        flag_type=flag_type,
        market_id=market_id,
        original_net_edge=float(original_net_edge),
        recomputed_net_edge=recomputed_net_edge,
        edge_diff=edge_diff,
        consistent=consistent,
        note="ok" if consistent else "recomputed edge differs from logged edge",
    )


def summarize_false_positives(results: list[ReplayResult]) -> dict[str, Any]:
    total = len(results)
    consistent = sum(1 for r in results if r.consistent)
    inconsistent = total - consistent

    return {
        "total_flags": total,
        "consistent_recomputations": consistent,
        "inconsistent_recomputations": inconsistent,
    }


def write_summary(results: list[ReplayResult], summary: dict[str, Any]) -> None:
    lines = [
        "# Replay Summary",
        "",
        "Phase A deterministic replay from logged inputs only.",
        "",
        f"- Total flags: {summary['total_flags']}",
        f"- Consistent recomputations: {summary['consistent_recomputations']}",
        f"- Inconsistent recomputations: {summary['inconsistent_recomputations']}",
        "",
        "## Detailed results",
        "",
        "| flag_type | market_id | original_net_edge | recomputed_net_edge | edge_diff | consistent | note |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]

    for r in results:
        lines.append(
            f"| {r.flag_type} | {r.market_id} | "
            f"{'' if r.original_net_edge is None else f'{r.original_net_edge:.6f}'} | "
            f"{'' if r.recomputed_net_edge is None else f'{r.recomputed_net_edge:.6f}'} | "
            f"{'' if r.edge_diff is None else f'{r.edge_diff:.6f}'} | "
            f"{r.consistent} | {r.note} |"
        )

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text("\n".join(lines), encoding="utf-8")


def run_replay_pred() -> None:
    flags = load_flag_events()
    if not flags:
        print("[WARN] No flag events found for replay.")
        return

    results = []
    for flag in flags:
        inputs = reconstruct_detection_inputs(flag)
        results.append(recompute_flag_deterministic(inputs))

    summary = summarize_false_positives(results)
    write_summary(results, summary)

    print("[OK] Wrote replay summary to reports/replay_pred_summary.md")
    print("[INFO] Replay summary:")
    print(summary)
    for r in results[:10]:
        print(asdict(r))


if __name__ == "__main__":
    run_replay_pred()
from __future__ import annotations

import json
from dataclasses import dataclass, asdict
from pathlib import Path
from statistics import median
from typing import Any


INPUT_FLAGS_PATH = Path("logs/prediction_scanner_flags.jsonl")
OUTPUT_ROWS_CSV = Path("artifacts/outputs/replay_pred_rows.csv")
OUTPUT_SUMMARY_JSON = Path("artifacts/outputs/replay_pred_summary.json")
OUTPUT_SUMMARY_MD = Path("reports/replay_pred_summary.md")

LATENCY_TO_PENALTY_BPS = {
    1: 5.0,
    5: 15.0,
    10: 30.0,
}


@dataclass
class ReplayRow:
    source_flag_type: str
    market_id: str
    pair_id: str | None
    target_size: float
    latency_seconds: int
    penalty_bps: float
    original_buy_price: float
    original_sell_price: float
    original_net_edge: float
    original_total_cost: float
    replayed_buy_price: float
    replayed_sell_price: float
    replayed_gross_edge: float
    replayed_net_edge: float
    still_positive: bool
    false_positive: bool


@dataclass
class ReplaySummary:
    flags_input: int
    replay_rows: int
    latency_scenarios: list[int]
    avg_original_net_edge: float | None
    half_life_seconds: int | None
    by_latency: list[dict[str, Any]]


def _r(x: float | None, ndigits: int = 6) -> float | None:
    if x is None:
        return None
    return round(float(x), ndigits)


def load_flag_log(path: Path = INPUT_FLAGS_PATH) -> list[dict[str, Any]]:
    if not path.exists():
        return []

    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return rows


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


def _extract_buy_sell_prices(flag: dict[str, Any]) -> tuple[float, float]:
    details = flag.get("details", {})

    if "buy_avg_price" in details and "sell_avg_price" in details:
        return float(details["buy_avg_price"]), float(details["sell_avg_price"])

    if "yes_buy_avg_price" in details and "no_buy_avg_price" in details:
        yes_price = float(details["yes_buy_avg_price"])
        no_price = float(details["no_buy_avg_price"])
        # complement bundle: total buy cost is yes + no
        # represent it as "buy price" = total basket cost, "sell price" = 1.0 payout
        return yes_price + no_price, 1.0

    raise ValueError(f"Unsupported flag detail schema: {details.keys()}")


def _extract_total_cost(flag: dict[str, Any]) -> float:
    details = flag.get("details", {})
    return float(details.get("total_cost", 0.0))


def _extract_original_net_edge(flag: dict[str, Any]) -> float:
    details = flag.get("details", {})
    return float(details.get("net_edge", 0.0))


def latency_penalty_bps(latency_seconds: int) -> float:
    if latency_seconds in LATENCY_TO_PENALTY_BPS:
        return LATENCY_TO_PENALTY_BPS[latency_seconds]
    raise ValueError(f"No penalty configured for latency {latency_seconds}s")


def replay_flag(
    flag: dict[str, Any],
    latency_seconds: int,
) -> ReplayRow:
    penalty_bps = latency_penalty_bps(latency_seconds)

    original_buy_price, original_sell_price = _extract_buy_sell_prices(flag)
    original_total_cost = _extract_total_cost(flag)
    original_net_edge = _extract_original_net_edge(flag)

    replayed_buy_price = original_buy_price * (1.0 + penalty_bps / 10000.0)
    replayed_sell_price = original_sell_price * (1.0 - penalty_bps / 10000.0)
    replayed_gross_edge = replayed_sell_price - replayed_buy_price
    replayed_net_edge = replayed_gross_edge - original_total_cost

    still_positive = replayed_net_edge > 0.0
    false_positive = original_net_edge > 0.0 and replayed_net_edge <= 0.0

    return ReplayRow(
        source_flag_type=str(flag.get("flag_type", "unknown")),
        market_id=_extract_market_id(flag),
        pair_id=_extract_pair_id(flag),
        target_size=float(flag.get("target_size", 0.0)),
        latency_seconds=int(latency_seconds),
        penalty_bps=float(penalty_bps),
        original_buy_price=float(original_buy_price),
        original_sell_price=float(original_sell_price),
        original_net_edge=float(original_net_edge),
        original_total_cost=float(original_total_cost),
        replayed_buy_price=float(replayed_buy_price),
        replayed_sell_price=float(replayed_sell_price),
        replayed_gross_edge=float(replayed_gross_edge),
        replayed_net_edge=float(replayed_net_edge),
        still_positive=still_positive,
        false_positive=false_positive,
    )


def estimate_half_life_seconds(replay_rows: list[ReplayRow]) -> int | None:
    if not replay_rows:
        return None

    latencies = sorted({row.latency_seconds for row in replay_rows})
    for latency in latencies:
        subset = [row for row in replay_rows if row.latency_seconds == latency]
        if not subset:
            continue
        share_lost = sum(1 for row in subset if not row.still_positive) / len(subset)
        if share_lost >= 0.5:
            return latency
    return None


def build_summary(
    flags: list[dict[str, Any]],
    replay_rows: list[ReplayRow],
) -> ReplaySummary:
    avg_original_net_edge = None
    if replay_rows:
        avg_original_net_edge = sum(row.original_net_edge for row in replay_rows) / len(replay_rows)

    latencies = sorted({row.latency_seconds for row in replay_rows})
    by_latency: list[dict[str, Any]] = []

    for latency in latencies:
        subset = [row for row in replay_rows if row.latency_seconds == latency]
        if not subset:
            continue

        avg_replayed_net_edge = sum(row.replayed_net_edge for row in subset) / len(subset)
        med_replayed_net_edge = median(row.replayed_net_edge for row in subset)
        false_positive_rate = sum(1 for row in subset if row.false_positive) / len(subset)
        still_positive_rate = sum(1 for row in subset if row.still_positive) / len(subset)

        by_latency.append(
            {
                "latency_seconds": latency,
                "rows": len(subset),
                "penalty_bps": latency_penalty_bps(latency),
                "avg_replayed_net_edge": _r(avg_replayed_net_edge, 6),
                "median_replayed_net_edge": _r(med_replayed_net_edge, 6),
                "false_positive_rate": _r(false_positive_rate, 6),
                "still_positive_rate": _r(still_positive_rate, 6),
            }
        )

    return ReplaySummary(
        flags_input=len(flags),
        replay_rows=len(replay_rows),
        latency_scenarios=latencies,
        avg_original_net_edge=_r(avg_original_net_edge, 6),
        half_life_seconds=estimate_half_life_seconds(replay_rows),
        by_latency=by_latency,
    )


def write_replay_outputs(
    replay_rows: list[ReplayRow],
    summary: ReplaySummary,
) -> None:
    OUTPUT_ROWS_CSV.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_SUMMARY_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_SUMMARY_MD.parent.mkdir(parents=True, exist_ok=True)

    # CSV
    if replay_rows:
        headers = list(asdict(replay_rows[0]).keys())
        lines = [",".join(headers)]
        for row in replay_rows:
            row_dict = asdict(row)
            values = []
            for header in headers:
                value = row_dict[header]
                if value is None:
                    values.append("")
                else:
                    text = str(value).replace(",", ";")
                    values.append(text)
            lines.append(",".join(values))
        OUTPUT_ROWS_CSV.write_text("\n".join(lines) + "\n", encoding="utf-8")
    else:
        OUTPUT_ROWS_CSV.write_text("", encoding="utf-8")

    # JSON summary
    OUTPUT_SUMMARY_JSON.write_text(
        json.dumps(asdict(summary), indent=2),
        encoding="utf-8",
    )

    # Markdown summary
    lines = [
        "# Replay Summary",
        "",
        f"- Flags input: {summary.flags_input}",
        f"- Replay rows: {summary.replay_rows}",
        f"- Latency scenarios: {summary.latency_scenarios}",
        f"- Average original net edge: {summary.avg_original_net_edge}",
        f"- Estimated half-life (seconds): {summary.half_life_seconds}",
        "",
        "## By latency",
        "",
        "| Latency (s) | Rows | Penalty (bps) | Avg replayed net edge | Median replayed net edge | False positive rate | Still positive rate |",
        "|---:|---:|---:|---:|---:|---:|---:|",
    ]

    for item in summary.by_latency:
        lines.append(
            f"| {item['latency_seconds']} | {item['rows']} | {item['penalty_bps']} | "
            f"{item['avg_replayed_net_edge']} | {item['median_replayed_net_edge']} | "
            f"{item['false_positive_rate']} | {item['still_positive_rate']} |"
        )

    lines.extend(
        [
            "",
            "## Conclusion",
            "",
            "Replay v1 applies latency penalties to logged opportunities and estimates whether edge remains positive under delayed execution.",
            "This is a first-pass feasibility framework and can later be upgraded with richer historical orderbook or quote evolution data.",
            "",
        ]
    )

    OUTPUT_SUMMARY_MD.write_text("\n".join(lines), encoding="utf-8")


def replay_flags(
    flags: list[dict[str, Any]],
    latency_grid: list[int] | None = None,
) -> tuple[list[ReplayRow], ReplaySummary]:
    if latency_grid is None:
        latency_grid = sorted(LATENCY_TO_PENALTY_BPS.keys())

    replay_rows: list[ReplayRow] = []
    for flag in flags:
        for latency_seconds in latency_grid:
            replay_rows.append(replay_flag(flag, latency_seconds=latency_seconds))

    summary = build_summary(flags, replay_rows)
    return replay_rows, summary


def main() -> None:
    flags = load_flag_log()
    replay_rows, summary = replay_flags(flags)
    write_replay_outputs(replay_rows, summary)

    print("[INFO] Replay finished")
    print(f"[INFO] Flags input: {summary.flags_input}")
    print(f"[INFO] Replay rows: {summary.replay_rows}")
    print(f"[INFO] Half-life (seconds): {summary.half_life_seconds}")
    print(f"[INFO] Wrote CSV: {OUTPUT_ROWS_CSV}")
    print(f"[INFO] Wrote JSON summary: {OUTPUT_SUMMARY_JSON}")
    print(f"[INFO] Wrote markdown summary: {OUTPUT_SUMMARY_MD}")


if __name__ == "__main__":
    main()
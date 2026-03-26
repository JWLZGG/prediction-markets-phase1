from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def _scanner_section(config: dict[str, Any] | None) -> dict[str, Any]:
    if not config:
        return {}
    block = config.get("scanner")
    return block if isinstance(block, dict) else {}


def ranked_console_top_n(config: dict[str, Any] | None) -> int:
    n = _scanner_section(config).get("ranked_console_top_n", 25)
    try:
        return max(0, int(n))
    except (TypeError, ValueError):
        return 25


def ranked_snapshot_path(config: dict[str, Any] | None) -> Path | None:
    raw = _scanner_section(config).get("ranked_snapshot_path")
    if not raw:
        return None
    return Path(str(raw))


def net_edge_bps(flag: dict[str, Any]) -> float:
    details = flag.get("details") or {}
    if not isinstance(details, dict):
        return float("-inf")
    v = details.get("net_edge_bps")
    if v is None:
        return float("-inf")
    try:
        return float(v)
    except (TypeError, ValueError):
        return float("-inf")


def net_edge(flag: dict[str, Any]) -> float:
    details = flag.get("details") or {}
    if not isinstance(details, dict):
        return float("-inf")
    v = details.get("net_edge")
    if v is None:
        return float("-inf")
    try:
        return float(v)
    except (TypeError, ValueError):
        return float("-inf")


def rank_flags(flags: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(flags, key=lambda f: (net_edge_bps(f), net_edge(f)), reverse=True)


def _compact_row(flag: dict[str, Any], rank: int) -> dict[str, Any]:
    details = flag.get("details") if isinstance(flag.get("details"), dict) else {}
    return {
        "rank": rank,
        "flag_type": flag.get("flag_type"),
        "market_id": flag.get("market_id"),
        "venue_a": flag.get("venue_a"),
        "venue_b": flag.get("venue_b"),
        "question": flag.get("question"),
        "target_size": flag.get("target_size"),
        "threshold_bps": flag.get("threshold_bps"),
        "net_edge_bps": details.get("net_edge_bps"),
        "net_edge": details.get("net_edge"),
        "gross_edge": details.get("gross_edge"),
        "total_cost": details.get("total_cost"),
    }


def write_ranked_snapshot(
    ranked: list[dict[str, Any]],
    path: Path,
    *,
    extra: dict[str, Any] | None = None,
) -> None:
    payload: dict[str, Any] = {
        "ranked": [_compact_row(f, i + 1) for i, f in enumerate(ranked)],
    }
    if extra:
        payload["meta"] = extra
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def display_ranked_opportunities(
    flags: list[dict[str, Any]],
    *,
    config: dict[str, Any] | None = None,
    title: str = "Ranked opportunities",
    cycle_index: int | None = None,
) -> None:
    top_n = ranked_console_top_n(config)
    snap_path = ranked_snapshot_path(config)

    if not flags:
        print(f"[INFO] {title}: no flags this cycle.")
        return

    ranked = rank_flags(flags)

    if snap_path is not None:
        meta: dict[str, Any] = {"title": title, "flag_count": len(flags)}
        if cycle_index is not None:
            meta["cycle_index"] = cycle_index
        write_ranked_snapshot(ranked, snap_path, extra=meta)

    print(f"\n[INFO] {title} (sorted by net_edge_bps, showing up to {top_n})")
    show = ranked[:top_n] if top_n > 0 else []
    if not show:
        return

    for i, flag in enumerate(show, start=1):
        details = flag.get("details") if isinstance(flag.get("details"), dict) else {}
        q = flag.get("question") or ""
        q_short = (q[:72] + "…") if len(str(q)) > 73 else q
        line = (
            f"  {i:2d}. {flag.get('flag_type')} | {flag.get('market_id')} | "
            f"net_edge_bps={details.get('net_edge_bps')} net_edge={details.get('net_edge')}"
        )
        if q_short:
            line += f" | {q_short}"
        print(line)

from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any

from src.detect.edge import compute_complement_edge, compute_cross_venue_edge
from src.detect.executable_pricing import (
    ExecutionResult,
    get_executable_buy_price,
    get_executable_sell_price,
)
from src.detect.fees import compute_fee_breakdown, compute_notional


def _r(x: float, ndigits: int = 6) -> float:
    return round(float(x), ndigits)


@dataclass(frozen=True)
class ScannerFlag:
    flag_type: str
    market_id: str
    venue_a: str
    venue_b: str | None
    target_size: float
    threshold_bps: float
    details: dict[str, Any]
    inputs: dict[str, Any]


def _build_cross_venue_details(
    market_id: str,
    buy_venue: str,
    sell_venue: str,
    target_size: float,
    buy_result: ExecutionResult,
    sell_result: ExecutionResult,
    total_cost_per_unit: float,
    threshold_bps: float,
    buy_asks: list[dict],
    sell_bids: list[dict],
) -> ScannerFlag | None:
    if not buy_result.executable:
        return None
    if not sell_result.executable:
        return None
    if buy_result.avg_price is None or sell_result.avg_price is None:
        return None

    edge_result = compute_cross_venue_edge(
        buy_price=buy_result.avg_price,
        sell_price=sell_result.avg_price,
        total_cost=total_cost_per_unit,
        threshold_bps=threshold_bps,
    )

    if not edge_result.should_flag:
        return None

    return ScannerFlag(
        flag_type="cross_venue_divergence",
        market_id=market_id,
        venue_a=buy_venue,
        venue_b=sell_venue,
        target_size=target_size,
        threshold_bps=threshold_bps,
        details={
            "buy_avg_price": _r(buy_result.avg_price, 6),
            "sell_avg_price": _r(sell_result.avg_price, 6),
            "buy_notional": _r(buy_result.total_cost, 6),
            "sell_notional": _r(sell_result.total_cost, 6),
            "levels_used_buy": buy_result.levels_used,
            "levels_used_sell": sell_result.levels_used,
            "gross_edge": _r(edge_result.gross_edge, 6),
            "total_cost": _r(edge_result.total_cost, 6),
            "net_edge": _r(edge_result.net_edge, 6),
            "net_edge_bps": _r(edge_result.net_edge_bps, 2),
            "should_flag": edge_result.should_flag,
        },
        inputs={
            "buy_asks": buy_asks,
            "sell_bids": sell_bids,
        },
    )


def scan_cross_venue_market(
    market_id: str,
    buy_venue: str,
    sell_venue: str,
    buy_asks: list[dict],
    sell_bids: list[dict],
    target_size: float,
    fee_config: dict,
    threshold_bps: float,
) -> ScannerFlag | None:
    buy_result = get_executable_buy_price(buy_asks, target_size=target_size)
    sell_result = get_executable_sell_price(sell_bids, target_size=target_size)

    if not buy_result.executable or not sell_result.executable:
        return None
    if buy_result.avg_price is None or sell_result.avg_price is None:
        return None

    buy_notional = compute_notional(buy_result.avg_price, target_size)
    sell_notional = compute_notional(sell_result.avg_price, target_size)

    buy_fee = compute_fee_breakdown(
        venue=buy_venue,
        notional=buy_notional,
        config=fee_config,
    )
    sell_fee = compute_fee_breakdown(
        venue=sell_venue,
        notional=sell_notional,
        config=fee_config,
    )

    total_cost_per_unit = (buy_fee.total_cost + sell_fee.total_cost) / float(target_size)

    return _build_cross_venue_details(
        market_id=market_id,
        buy_venue=buy_venue,
        sell_venue=sell_venue,
        target_size=target_size,
        buy_result=buy_result,
        sell_result=sell_result,
        total_cost_per_unit=total_cost_per_unit,
        threshold_bps=threshold_bps,
        buy_asks=buy_asks,
        sell_bids=sell_bids,
    )


def scan_complement_market(
    market_id: str,
    venue: str,
    yes_asks: list[dict],
    no_asks: list[dict],
    target_size: float,
    fee_config: dict,
    threshold_bps: float,
) -> ScannerFlag | None:
    yes_result = get_executable_buy_price(yes_asks, target_size=target_size)
    no_result = get_executable_buy_price(no_asks, target_size=target_size)

    if not yes_result.executable or not no_result.executable:
        return None
    if yes_result.avg_price is None or no_result.avg_price is None:
        return None

    yes_notional = compute_notional(yes_result.avg_price, target_size)
    no_notional = compute_notional(no_result.avg_price, target_size)

    yes_fee = compute_fee_breakdown(
        venue=venue,
        notional=yes_notional,
        config=fee_config,
    )
    no_fee = compute_fee_breakdown(
        venue=venue,
        notional=no_notional,
        config=fee_config,
    )

    total_cost_per_unit = (yes_fee.total_cost + no_fee.total_cost) / float(target_size)

    edge_result = compute_complement_edge(
        yes_buy_price=yes_result.avg_price,
        no_buy_price=no_result.avg_price,
        total_cost=total_cost_per_unit,
        threshold_bps=threshold_bps,
    )

    if not edge_result.should_flag:
        return None

    return ScannerFlag(
        flag_type="complement_sanity",
        market_id=market_id,
        venue_a=venue,
        venue_b=None,
        target_size=target_size,
        threshold_bps=threshold_bps,
        details={
            "yes_buy_avg_price": _r(yes_result.avg_price, 6),
            "no_buy_avg_price": _r(no_result.avg_price, 6),
            "yes_levels_used": yes_result.levels_used,
            "no_levels_used": no_result.levels_used,
            "gross_edge": _r(edge_result.gross_edge, 6),
            "total_cost": _r(edge_result.total_cost, 6),
            "net_edge": _r(edge_result.net_edge, 6),
            "net_edge_bps": _r(edge_result.net_edge_bps, 2),
            "should_flag": edge_result.should_flag,
        },
        inputs={
            "yes_asks": yes_asks,
            "no_asks": no_asks,
        },
    )


def flag_to_dict(flag: ScannerFlag) -> dict[str, Any]:
    return asdict(flag)
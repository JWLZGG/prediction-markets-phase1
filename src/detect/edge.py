from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class EdgeResult:
    gross_edge: float
    total_cost: float
    net_edge: float
    net_edge_bps: float
    should_flag: bool


def probability_to_bps(x: float) -> float:
    return float(x) * 10_000.0


def compute_cross_venue_edge(
    buy_price: float,
    sell_price: float,
    total_cost: float,
    threshold_bps: float,
) -> EdgeResult:
    """
    Cross-venue divergence edge in probability space.

    Example:
        buy at 0.60 on venue A
        sell at 0.63 on venue B
        gross edge = 0.03
    """
    gross_edge = float(sell_price) - float(buy_price)
    net_edge = gross_edge - float(total_cost)
    net_edge_bps = probability_to_bps(net_edge)
    should_flag = net_edge_bps >= float(threshold_bps)

    return EdgeResult(
        gross_edge=gross_edge,
        total_cost=float(total_cost),
        net_edge=net_edge,
        net_edge_bps=net_edge_bps,
        should_flag=should_flag,
    )


def compute_complement_edge(
    yes_buy_price: float,
    no_buy_price: float,
    total_cost: float,
    threshold_bps: float,
) -> EdgeResult:
    """
    Complement sanity edge for binary markets.

    If YES + NO < 1 after costs, there may be a synthetic edge.
    """
    gross_edge = 1.0 - (float(yes_buy_price) + float(no_buy_price))
    net_edge = gross_edge - float(total_cost)
    net_edge_bps = probability_to_bps(net_edge)
    should_flag = net_edge_bps >= float(threshold_bps)

    return EdgeResult(
        gross_edge=gross_edge,
        total_cost=float(total_cost),
        net_edge=net_edge,
        net_edge_bps=net_edge_bps,
        should_flag=should_flag,
    )
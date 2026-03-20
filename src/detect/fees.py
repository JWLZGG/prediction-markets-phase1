from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class FeeBreakdown:
    trading_fee: float
    slippage_buffer: float
    fixed_buffer: float
    total_cost: float


def bps_to_decimal(bps: float) -> float:
    return float(bps) / 10_000.0


def compute_notional(avg_price: float, size: float) -> float:
    if avg_price < 0:
        raise ValueError(f"avg_price must be non-negative, got {avg_price}")
    if size < 0:
        raise ValueError(f"size must be non-negative, got {size}")
    return float(avg_price) * float(size)


def compute_fee_breakdown(
    venue: str,
    notional: float,
    config: dict,
) -> FeeBreakdown:
    if notional < 0:
        raise ValueError(f"notional must be non-negative, got {notional}")

    venues = config.get("venues", {})
    venue_cfg = venues.get(venue)

    if venue_cfg is None:
        raise ValueError(f"Missing fee config for venue: {venue}")

    taker_fee_bps = float(venue_cfg.get("taker_fee_bps", 0.0))
    slippage_buffer_bps = float(venue_cfg.get("slippage_buffer_bps", 0.0))
    fixed_buffer = float(venue_cfg.get("fixed_buffer", 0.0))

    trading_fee = notional * bps_to_decimal(taker_fee_bps)
    slippage_buffer = notional * bps_to_decimal(slippage_buffer_bps)
    total_cost = trading_fee + slippage_buffer + fixed_buffer

    return FeeBreakdown(
        trading_fee=trading_fee,
        slippage_buffer=slippage_buffer,
        fixed_buffer=fixed_buffer,
        total_cost=total_cost,
    )
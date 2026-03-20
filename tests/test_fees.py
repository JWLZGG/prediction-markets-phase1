import math

from src.detect.fees import bps_to_decimal, compute_fee_breakdown, compute_notional


TEST_CONFIG = {
    "venues": {
        "polymarket": {
            "taker_fee_bps": 0,
            "slippage_buffer_bps": 50,
            "fixed_buffer": 0.0,
        },
        "kalshi": {
            "taker_fee_bps": 25,
            "slippage_buffer_bps": 50,
            "fixed_buffer": 0.0,
        },
        "test_fixed": {
            "taker_fee_bps": 10,
            "slippage_buffer_bps": 20,
            "fixed_buffer": 1.5,
        },
    }
}


def test_bps_to_decimal():
    assert math.isclose(bps_to_decimal(100), 0.01, rel_tol=1e-9)
    assert math.isclose(bps_to_decimal(25), 0.0025, rel_tol=1e-9)
    assert math.isclose(bps_to_decimal(0), 0.0, rel_tol=1e-9)


def test_compute_notional():
    result = compute_notional(avg_price=0.63, size=100)
    assert math.isclose(result, 63.0, rel_tol=1e-9)


def test_polymarket_zero_fee_with_slippage():
    breakdown = compute_fee_breakdown(
        venue="polymarket",
        notional=100.0,
        config=TEST_CONFIG,
    )

    assert math.isclose(breakdown.trading_fee, 0.0, rel_tol=1e-9)
    assert math.isclose(breakdown.slippage_buffer, 0.5, rel_tol=1e-9)
    assert math.isclose(breakdown.fixed_buffer, 0.0, rel_tol=1e-9)
    assert math.isclose(breakdown.total_cost, 0.5, rel_tol=1e-9)


def test_kalshi_fee_plus_slippage():
    breakdown = compute_fee_breakdown(
        venue="kalshi",
        notional=100.0,
        config=TEST_CONFIG,
    )

    assert math.isclose(breakdown.trading_fee, 0.25, rel_tol=1e-9)
    assert math.isclose(breakdown.slippage_buffer, 0.5, rel_tol=1e-9)
    assert math.isclose(breakdown.fixed_buffer, 0.0, rel_tol=1e-9)
    assert math.isclose(breakdown.total_cost, 0.75, rel_tol=1e-9)


def test_fixed_buffer_is_added():
    breakdown = compute_fee_breakdown(
        venue="test_fixed",
        notional=200.0,
        config=TEST_CONFIG,
    )

    # 10 bps of 200 = 0.2
    # 20 bps of 200 = 0.4
    # fixed buffer = 1.5
    assert math.isclose(breakdown.trading_fee, 0.2, rel_tol=1e-9)
    assert math.isclose(breakdown.slippage_buffer, 0.4, rel_tol=1e-9)
    assert math.isclose(breakdown.fixed_buffer, 1.5, rel_tol=1e-9)
    assert math.isclose(breakdown.total_cost, 2.1, rel_tol=1e-9)


def test_missing_venue_raises():
    try:
        compute_fee_breakdown(
            venue="unknown",
            notional=100.0,
            config=TEST_CONFIG,
        )
        assert False, "Expected ValueError for missing venue config"
    except ValueError:
        pass
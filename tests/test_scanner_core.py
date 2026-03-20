import math

from src.detect.scanner_core import (
    flag_to_dict,
    scan_complement_market,
    scan_cross_venue_market,
)


TEST_CONFIG = {
    "venues": {
        "polymarket": {
            "taker_fee_bps": 0,
            "slippage_buffer_bps": 10,
            "fixed_buffer": 0.0,
        },
        "kalshi": {
            "taker_fee_bps": 0,
            "slippage_buffer_bps": 10,
            "fixed_buffer": 0.0,
        },
    }
}


def test_scan_cross_venue_market_flags():
    flag = scan_cross_venue_market(
        market_id="btc-above-100k",
        buy_venue="polymarket",
        sell_venue="kalshi",
        buy_asks=[
            {"price": 0.60, "size": 60},
            {"price": 0.61, "size": 40},
        ],
        sell_bids=[
            {"price": 0.64, "size": 50},
            {"price": 0.63, "size": 50},
        ],
        target_size=100,
        fee_config=TEST_CONFIG,
        threshold_bps=100,
    )

    assert flag is not None
    assert flag.flag_type == "cross_venue_divergence"
    assert flag.market_id == "btc-above-100k"
    assert flag.venue_a == "polymarket"
    assert flag.venue_b == "kalshi"
    assert math.isclose(flag.target_size, 100.0, rel_tol=1e-9)
    assert flag.details["should_flag"] is True
    assert flag.details["net_edge_bps"] >= 100


def test_scan_cross_venue_market_returns_none_when_not_executable():
    flag = scan_cross_venue_market(
        market_id="thin-market",
        buy_venue="polymarket",
        sell_venue="kalshi",
        buy_asks=[{"price": 0.60, "size": 20}],
        sell_bids=[{"price": 0.65, "size": 100}],
        target_size=100,
        fee_config=TEST_CONFIG,
        threshold_bps=100,
    )

    assert flag is None


def test_scan_complement_market_flags():
    flag = scan_complement_market(
        market_id="election-yes-no",
        venue="polymarket",
        yes_asks=[
            {"price": 0.47, "size": 100},
        ],
        no_asks=[
            {"price": 0.46, "size": 100},
        ],
        target_size=100,
        fee_config=TEST_CONFIG,
        threshold_bps=100,
    )

    assert flag is not None
    assert flag.flag_type == "complement_sanity"
    assert flag.market_id == "election-yes-no"
    assert flag.venue_a == "polymarket"
    assert flag.venue_b is None
    assert flag.details["should_flag"] is True
    assert flag.details["net_edge_bps"] >= 100


def test_flag_to_dict():
    flag = scan_complement_market(
        market_id="test-market",
        venue="polymarket",
        yes_asks=[{"price": 0.47, "size": 100}],
        no_asks=[{"price": 0.46, "size": 100}],
        target_size=100,
        fee_config=TEST_CONFIG,
        threshold_bps=100,
    )

    assert flag is not None
    as_dict = flag_to_dict(flag)
    assert as_dict["flag_type"] == "complement_sanity"
    assert as_dict["market_id"] == "test-market"
    assert "details" in as_dict
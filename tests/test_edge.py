import math

from src.detect.edge import (
    compute_complement_edge,
    compute_cross_venue_edge,
    probability_to_bps,
)


def test_probability_to_bps():
    assert math.isclose(probability_to_bps(0.01), 100.0, rel_tol=1e-9)
    assert math.isclose(probability_to_bps(0.025), 250.0, rel_tol=1e-9)
    assert math.isclose(probability_to_bps(0.0), 0.0, rel_tol=1e-9)


def test_cross_venue_edge_positive_flag():
    result = compute_cross_venue_edge(
        buy_price=0.60,
        sell_price=0.63,
        total_cost=0.01,
        threshold_bps=100,
    )

    assert math.isclose(result.gross_edge, 0.03, rel_tol=1e-9)
    assert math.isclose(result.total_cost, 0.01, rel_tol=1e-9)
    assert math.isclose(result.net_edge, 0.02, rel_tol=1e-9)
    assert math.isclose(result.net_edge_bps, 200.0, rel_tol=1e-9)
    assert result.should_flag is True


def test_cross_venue_edge_below_threshold():
    result = compute_cross_venue_edge(
        buy_price=0.60,
        sell_price=0.61,
        total_cost=0.005,
        threshold_bps=100,
    )

    assert math.isclose(result.gross_edge, 0.01, rel_tol=1e-9)
    assert math.isclose(result.net_edge, 0.005, rel_tol=1e-9)
    assert math.isclose(result.net_edge_bps, 50.0, rel_tol=1e-9)
    assert result.should_flag is False


def test_cross_venue_edge_negative():
    result = compute_cross_venue_edge(
        buy_price=0.62,
        sell_price=0.60,
        total_cost=0.005,
        threshold_bps=100,
    )

    assert math.isclose(result.gross_edge, -0.02, rel_tol=1e-9)
    assert math.isclose(result.net_edge, -0.025, rel_tol=1e-9)
    assert math.isclose(result.net_edge_bps, -250.0, rel_tol=1e-9)
    assert result.should_flag is False


def test_complement_edge_positive_flag():
    result = compute_complement_edge(
        yes_buy_price=0.48,
        no_buy_price=0.47,
        total_cost=0.01,
        threshold_bps=100,
    )

    assert math.isclose(result.gross_edge, 0.05, rel_tol=1e-9)
    assert math.isclose(result.net_edge, 0.04, rel_tol=1e-9)
    assert math.isclose(result.net_edge_bps, 400.0, rel_tol=1e-9)
    assert result.should_flag is True


def test_complement_edge_below_threshold():
    result = compute_complement_edge(
        yes_buy_price=0.50,
        no_buy_price=0.495,
        total_cost=0.003,
        threshold_bps=100,
    )

    assert math.isclose(result.gross_edge, 0.005, rel_tol=1e-9)
    assert math.isclose(result.net_edge, 0.002, rel_tol=1e-9)
    assert math.isclose(result.net_edge_bps, 20.0, rel_tol=1e-9)
    assert result.should_flag is False
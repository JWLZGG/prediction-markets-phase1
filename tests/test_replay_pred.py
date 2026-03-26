import pytest

from src.backtest.replay_pred import (
    estimate_half_life_seconds,
    replay_flag,
    replay_flags,
)


def make_cross_venue_flag(net_edge: float = 0.02) -> dict:
    return {
        "flag_type": "cross_venue_divergence",
        "market_id": "btc-above-100k",
        "target_size": 100,
        "details": {
            "buy_avg_price": 0.60,
            "sell_avg_price": 0.63,
            "total_cost": 0.01,
            "net_edge": net_edge,
        },
    }


def make_marginal_cross_venue_flag() -> dict:
    return {
        "flag_type": "cross_venue_divergence",
        "market_id": "btc-above-100k-marginal",
        "target_size": 100,
        "details": {
            "buy_avg_price": 0.60,
            "sell_avg_price": 0.611,
            "total_cost": 0.01,
            "net_edge": 0.001,
        },
    }


def make_complement_flag(net_edge: float = 0.03) -> dict:
    return {
        "flag_type": "complement_sanity",
        "market_id": "election-yes-no",
        "target_size": 100,
        "details": {
            "yes_buy_avg_price": 0.47,
            "no_buy_avg_price": 0.46,
            "total_cost": 0.01,
            "net_edge": net_edge,
        },
    }


def test_replay_cross_venue_flag_runs():
    flag = make_cross_venue_flag(net_edge=0.02)
    row = replay_flag(flag, latency_seconds=1)

    assert row.market_id == "btc-above-100k"
    assert row.latency_seconds == 1
    assert row.original_net_edge == 0.02
    assert row.replayed_buy_price > row.original_buy_price
    assert row.replayed_sell_price < row.original_sell_price


def test_replay_complement_flag_runs():
    flag = make_complement_flag(net_edge=0.03)
    row = replay_flag(flag, latency_seconds=5)

    assert row.market_id == "election-yes-no"
    assert row.latency_seconds == 5
    assert row.original_buy_price == pytest.approx(0.93)
    assert row.original_sell_price == pytest.approx(1.0)


def test_false_positive_under_large_latency():
    flag = make_marginal_cross_venue_flag()
    row = replay_flag(flag, latency_seconds=10)

    assert row.false_positive is True
    assert row.still_positive is False


def test_replay_flags_and_summary():
    flags = [make_cross_venue_flag(), make_complement_flag()]
    rows, summary = replay_flags(flags, latency_grid=[1, 5, 10])

    assert len(rows) == 6
    assert summary.flags_input == 2
    assert summary.replay_rows == 6
    assert summary.latency_scenarios == [1, 5, 10]
    assert len(summary.by_latency) == 3


def test_estimate_half_life_seconds():
    flags = [make_marginal_cross_venue_flag() for _ in range(4)]
    rows, _ = replay_flags(flags, latency_grid=[1, 5, 10])

    half_life = estimate_half_life_seconds(rows)
    assert half_life in {1, 5, 10}
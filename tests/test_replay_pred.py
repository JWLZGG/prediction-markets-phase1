from datetime import datetime
from pathlib import Path

import pytest

import src.backtest.replay_pred as replay_pred_module
from src.backtest.replay_pred import (
    ReplayRow,
    estimate_half_life_seconds,
    replay_flag,
    replay_flags,
)


def make_live_complement_flag(snapshot_output_path: Path, net_edge: float = 0.02, target_size: float = 10.0) -> dict:
    return {
        "source": "live_complement_polymarket_loop",
        "flag_type": "complement_sanity",
        "market_id": "test-market",
        "target_size": target_size,
        "detected_ts_utc": "2026-03-25T00:00:30+00:00",
        "snapshot_output_path": str(snapshot_output_path),
        "details": {
            "yes_buy_avg_price": 0.47,
            "no_buy_avg_price": 0.46,
            "total_cost": 0.005,
            "net_edge": net_edge,
        },
    }


def make_cross_venue_flag() -> dict:
    return {
        "source": "synthetic_demo",
        "flag_type": "cross_venue_divergence",
        "market_id": "btc-above-100k",
        "target_size": 100,
        "details": {
            "buy_avg_price": 0.60,
            "sell_avg_price": 0.63,
            "total_cost": 0.01,
            "net_edge": 0.02,
        },
    }


def test_observed_state_replay_uses_later_snapshot(monkeypatch: pytest.MonkeyPatch):
    snapshot_1 = Path("orig_snapshot.parquet")
    snapshot_2 = Path("later_snapshot.parquet")

    monkeypatch.setattr(
        replay_pred_module,
        "_find_later_snapshot_for_flag",
        lambda flag, latency_seconds: (
            snapshot_2,
            datetime.fromisoformat("2026-03-25T00:02:00+00:00"),
        ),
    )
    monkeypatch.setattr(
        replay_pred_module,
        "_load_paired_books",
        lambda snapshot_path_str: {
            "test-market": {
                "market_id": "test-market",
                "yes_asks": [{"price": 0.49, "size": 10}],
                "no_asks": [{"price": 0.49, "size": 10}],
            }
        },
    )

    flag = make_live_complement_flag(snapshot_1)
    row = replay_flag(flag, latency_seconds=1)

    assert row.replay_mode == "observed_latency_replay"
    assert row.replay_status == "still_positive"
    assert row.replayable is True
    assert row.later_snapshot_path == str(snapshot_2)
    assert row.replayed_buy_price == pytest.approx(0.98)
    assert row.replayed_net_edge is not None
    assert row.replayed_net_edge > 0


def test_observed_state_replay_can_false_positive(monkeypatch: pytest.MonkeyPatch):
    snapshot_1 = Path("orig_snapshot.parquet")
    snapshot_2 = Path("later_snapshot.parquet")

    monkeypatch.setattr(
        replay_pred_module,
        "_find_later_snapshot_for_flag",
        lambda flag, latency_seconds: (
            snapshot_2,
            datetime.fromisoformat("2026-03-25T00:02:00+00:00"),
        ),
    )
    monkeypatch.setattr(
        replay_pred_module,
        "_load_paired_books",
        lambda snapshot_path_str: {
            "test-market": {
                "market_id": "test-market",
                "yes_asks": [{"price": 0.56, "size": 10}],
                "no_asks": [{"price": 0.45, "size": 10}],
            }
        },
    )

    flag = make_live_complement_flag(snapshot_1, net_edge=0.02)
    row = replay_flag(flag, latency_seconds=1)

    assert row.replay_mode == "observed_latency_replay"
    assert row.replay_status == "false_positive"
    assert row.replayable is True
    assert row.false_positive is True
    assert row.still_positive is False


def test_unsupported_flag_is_marked_explicitly():
    row = replay_flag(make_cross_venue_flag(), latency_seconds=1)

    assert row.replay_mode == "unsupported"
    assert row.replay_status == "unsupported_no_observed_state_path"
    assert row.replayable is False


def test_replay_flags_summary_includes_size_latency_breakdown(monkeypatch: pytest.MonkeyPatch):
    snapshot_1 = Path("orig_snapshot.parquet")
    snapshot_2 = Path("later_snapshot.parquet")

    monkeypatch.setattr(
        replay_pred_module,
        "_find_later_snapshot_for_flag",
        lambda flag, latency_seconds: (
            snapshot_2,
            datetime.fromisoformat("2026-03-25T00:02:00+00:00"),
        ),
    )
    monkeypatch.setattr(
        replay_pred_module,
        "_load_paired_books",
        lambda snapshot_path_str: {
            "test-market": {
                "market_id": "test-market",
                "yes_asks": [{"price": 0.49, "size": 100}],
                "no_asks": [{"price": 0.49, "size": 100}],
            }
        },
    )

    flags = [
        make_live_complement_flag(snapshot_1, target_size=5.0),
        make_live_complement_flag(snapshot_1, target_size=50.0),
    ]
    rows, summary = replay_flags(flags, latency_grid=[1])

    assert len(rows) == 2
    assert summary.flags_input == 2
    assert summary.replay_rows == 2
    assert summary.replayable_rows == 2
    assert len(summary.by_latency) == 1
    size_buckets = {item["size_bucket"] for item in summary.by_size_and_latency}
    assert size_buckets == {"medium", "small"}


def test_estimate_half_life_seconds_uses_replayable_rows():
    rows = [
        ReplayRow(
            source_flag_type="complement_sanity",
            market_id="m1",
            pair_id=None,
            target_size=10.0,
            size_bucket="small",
            latency_seconds=1,
            source="live_complement_polymarket_loop",
            original_buy_price=0.93,
            original_sell_price=1.0,
            original_net_edge=0.02,
            original_total_cost=0.005,
            replay_mode="observed_latency_replay",
            replay_status="still_positive",
            snapshot_output_path="snap1",
            later_snapshot_path="snap2",
            later_snapshot_ts_utc="2026-03-25T00:02:00+00:00",
            observed_state_found=True,
            replayable=True,
            later_state_executable=True,
            replayed_buy_price=0.98,
            replayed_sell_price=1.0,
            replayed_gross_edge=0.02,
            replayed_total_cost=0.005,
            replayed_net_edge=0.015,
            replayed_net_edge_bps=150.0,
            still_positive=True,
            false_positive=False,
        ),
        ReplayRow(
            source_flag_type="complement_sanity",
            market_id="m2",
            pair_id=None,
            target_size=10.0,
            size_bucket="small",
            latency_seconds=5,
            source="live_complement_polymarket_loop",
            original_buy_price=0.93,
            original_sell_price=1.0,
            original_net_edge=0.02,
            original_total_cost=0.005,
            replay_mode="observed_latency_replay",
            replay_status="false_positive",
            snapshot_output_path="snap1",
            later_snapshot_path="snap3",
            later_snapshot_ts_utc="2026-03-25T00:06:00+00:00",
            observed_state_found=True,
            replayable=True,
            later_state_executable=True,
            replayed_buy_price=1.01,
            replayed_sell_price=1.0,
            replayed_gross_edge=-0.01,
            replayed_total_cost=0.005,
            replayed_net_edge=-0.015,
            replayed_net_edge_bps=-150.0,
            still_positive=False,
            false_positive=True,
        ),
    ]

    assert estimate_half_life_seconds(rows) == 5

import pandas as pd

from src.features.open_snapshot_selection import (
    attach_open_snapshot_timestamp,
    select_open_snapshot_timestamp,
)


def test_select_first_valid_price_within_60_minutes():
    created_at = pd.Timestamp("2026-01-01T00:00:00Z")
    history = pd.DataFrame(
        {
            "timestamp": [
                pd.Timestamp("2026-01-01T00:10:00Z"),
                pd.Timestamp("2026-01-01T00:20:00Z"),
            ]
        }
    )

    result = select_open_snapshot_timestamp(created_at, history)
    assert result == pd.Timestamp("2026-01-01T00:10:00Z")


def test_reject_when_only_later_price_exists():
    created_at = pd.Timestamp("2026-01-01T00:00:00Z")
    history = pd.DataFrame(
        {
            "timestamp": [
                pd.Timestamp("2026-01-01T01:30:00Z"),
            ]
        }
    )

    result = select_open_snapshot_timestamp(created_at, history)
    assert result is None


def test_accept_exactly_60_minute_boundary():
    created_at = pd.Timestamp("2026-01-01T00:00:00Z")
    history = pd.DataFrame(
        {
            "timestamp": [
                pd.Timestamp("2026-01-01T01:00:00Z"),
            ]
        }
    )

    result = select_open_snapshot_timestamp(created_at, history)
    assert result == pd.Timestamp("2026-01-01T01:00:00Z")


def test_ignore_pre_creation_timestamp_and_take_first_valid_after():
    created_at = pd.Timestamp("2026-01-01T00:00:00Z")
    history = pd.DataFrame(
        {
            "timestamp": [
                pd.Timestamp("2025-12-31T23:55:00Z"),
                pd.Timestamp("2026-01-01T00:15:00Z"),
                pd.Timestamp("2026-01-01T00:30:00Z"),
            ]
        }
    )

    result = select_open_snapshot_timestamp(created_at, history)
    assert result == pd.Timestamp("2026-01-01T00:15:00Z")


def test_attach_open_snapshot_timestamp():
    markets = pd.DataFrame(
        {
            "market_id": ["M1", "M2"],
            "created_at": [
                pd.Timestamp("2026-01-01T00:00:00Z"),
                pd.Timestamp("2026-01-01T02:00:00Z"),
            ],
        }
    )

    history = pd.DataFrame(
        {
            "market_id": ["M1", "M1", "M2"],
            "timestamp": [
                pd.Timestamp("2026-01-01T00:10:00Z"),
                pd.Timestamp("2026-01-01T00:20:00Z"),
                pd.Timestamp("2026-01-01T03:30:00Z"),
            ],
        }
    )

    result = attach_open_snapshot_timestamp(markets, history)

    assert "open_snapshot_ts" in result.columns
    assert result.loc[result["market_id"] == "M1", "open_snapshot_ts"].iloc[0] == pd.Timestamp(
        "2026-01-01T00:10:00Z"
    )
    assert pd.isna(
        result.loc[result["market_id"] == "M2", "open_snapshot_ts"].iloc[0]
    )
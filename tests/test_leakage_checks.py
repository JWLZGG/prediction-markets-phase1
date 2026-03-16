import pandas as pd
import pytest

from src.features.leakage_checks import (
    assert_snapshot_before_close,
    assert_open_before_close,
    assert_snapshot_not_before_open,
    assert_no_duplicate_market_snapshot_rows,
    assert_no_post_resolution_feature_columns,
)


def test_snapshot_after_close_raises():
    df = pd.DataFrame(
        {
            "snapshot_ts": [pd.Timestamp("2026-01-03T00:00:00Z")],
            "close_ts": [pd.Timestamp("2026-01-02T00:00:00Z")],
        }
    )

    with pytest.raises(ValueError):
        assert_snapshot_before_close(df)


def test_open_not_before_close_raises():
    df = pd.DataFrame(
        {
            "open_ts": [pd.Timestamp("2026-01-02T00:00:00Z")],
            "close_ts": [pd.Timestamp("2026-01-02T00:00:00Z")],
        }
    )

    with pytest.raises(ValueError):
        assert_open_before_close(df)


def test_snapshot_before_open_raises():
    df = pd.DataFrame(
        {
            "open_ts": [pd.Timestamp("2026-01-02T00:00:00Z")],
            "snapshot_ts": [pd.Timestamp("2026-01-01T23:00:00Z")],
        }
    )

    with pytest.raises(ValueError):
        assert_snapshot_not_before_open(df)


def test_duplicate_market_snapshot_rows_raise():
    df = pd.DataFrame(
        {
            "market_id": [1, 1],
            "snapshot_type": ["mid", "mid"],
            "snapshot_ts": [
                pd.Timestamp("2026-01-02T00:00:00Z"),
                pd.Timestamp("2026-01-02T00:00:00Z"),
            ],
        }
    )

    with pytest.raises(ValueError):
        assert_no_duplicate_market_snapshot_rows(df)


def test_post_resolution_columns_raise():
    df = pd.DataFrame(
        {
            "market_id": [1],
            "resolved_outcome_price": [1.0],
        }
    )

    with pytest.raises(ValueError):
        assert_no_post_resolution_feature_columns(df, ["resolved_outcome_price", "final_price"])
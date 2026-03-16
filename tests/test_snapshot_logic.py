import pandas as pd

from src.features.leakage_checks import (
    assert_midpoint_between_open_and_close,
    assert_t_minus_24h_is_exact,
)


def test_midpoint_between_open_and_close():
    df = pd.DataFrame(
        {
            "snapshot_type": ["mid"],
            "open_ts": [pd.Timestamp("2026-01-01T00:00:00Z")],
            "close_ts": [pd.Timestamp("2026-01-03T00:00:00Z")],
            "snapshot_ts": [pd.Timestamp("2026-01-02T00:00:00Z")],
        }
    )

    assert_midpoint_between_open_and_close(df)


def test_t_minus_24h_exact():
    df = pd.DataFrame(
        {
            "snapshot_type": ["t_minus_24h"],
            "close_ts": [pd.Timestamp("2026-01-03T00:00:00Z")],
            "snapshot_ts": [pd.Timestamp("2026-01-02T00:00:00Z")],
        }
    )

    assert_t_minus_24h_is_exact(df)
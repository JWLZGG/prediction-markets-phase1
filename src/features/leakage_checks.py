from __future__ import annotations

import pandas as pd


def assert_required_columns(df: pd.DataFrame, required: list[str]) -> None:
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")


def assert_open_before_close(df: pd.DataFrame) -> None:
    if (pd.to_datetime(df["open_ts"], utc=True) >= pd.to_datetime(df["close_ts"], utc=True)).any():
        raise ValueError("Integrity error: open_ts must be strictly before close_ts")


def assert_snapshot_before_close(df: pd.DataFrame) -> None:
    if (pd.to_datetime(df["snapshot_ts"], utc=True) > pd.to_datetime(df["close_ts"], utc=True)).any():
        raise ValueError("Leakage detected: snapshot_ts after close_ts")


def assert_snapshot_not_before_open(df: pd.DataFrame) -> None:
    if (pd.to_datetime(df["snapshot_ts"], utc=True) < pd.to_datetime(df["open_ts"], utc=True)).any():
        raise ValueError("Integrity error: snapshot_ts before open_ts")


def assert_no_duplicate_market_snapshot_rows(df: pd.DataFrame) -> None:
    required = ["market_id", "snapshot_type", "snapshot_ts"]
    assert_required_columns(df, required)

    dupes = df.duplicated(subset=required)
    if dupes.any():
        raise ValueError("Integrity error: duplicate market/snapshot rows detected")


def assert_midpoint_between_open_and_close(df: pd.DataFrame) -> None:
    required = ["snapshot_type", "snapshot_ts", "open_ts", "close_ts"]
    assert_required_columns(df, required)

    mid_df = df[df["snapshot_type"] == "mid"].copy()
    if mid_df.empty:
        return

    open_ts = pd.to_datetime(mid_df["open_ts"], utc=True)
    close_ts = pd.to_datetime(mid_df["close_ts"], utc=True)
    snapshot_ts = pd.to_datetime(mid_df["snapshot_ts"], utc=True)

    expected_mid = open_ts + (close_ts - open_ts) / 2

    if not (snapshot_ts == expected_mid).all():
        raise ValueError("Integrity error: midpoint snapshot_ts does not equal lifecycle midpoint")


def assert_t_minus_24h_is_exact(df: pd.DataFrame) -> None:
    required = ["snapshot_type", "snapshot_ts", "close_ts"]
    assert_required_columns(df, required)

    t24_df = df[df["snapshot_type"] == "t_minus_24h"].copy()
    if t24_df.empty:
        return

    close_ts = pd.to_datetime(t24_df["close_ts"], utc=True)
    snapshot_ts = pd.to_datetime(t24_df["snapshot_ts"], utc=True)
    expected = close_ts - pd.Timedelta(hours=24)

    if not (snapshot_ts == expected).all():
        raise ValueError("Integrity error: t_minus_24h snapshot_ts is not exactly close_ts - 24h")


def assert_no_post_resolution_feature_columns(df: pd.DataFrame, forbidden_columns: list[str]) -> None:
    present = [c for c in forbidden_columns if c in df.columns]
    if present:
        raise ValueError(f"Leakage risk: forbidden post-resolution columns present: {present}")
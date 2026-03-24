from __future__ import annotations

from datetime import timedelta

import pandas as pd


def select_open_snapshot_timestamp(
    created_at: pd.Timestamp,
    history_df: pd.DataFrame,
    timestamp_col: str = "timestamp",
    window_minutes: int = 60,
) -> pd.Timestamp | None:
    """
    Select the earliest valid history timestamp that falls within the
    open-selection window:

        created_at <= timestamp <= created_at + window_minutes

    Returns None if no valid timestamp exists.
    """
    if created_at is None or pd.isna(created_at):
        return None

    if history_df is None or history_df.empty:
        return None

    if timestamp_col not in history_df.columns:
        raise ValueError(f"Missing timestamp column: {timestamp_col}")

    df = history_df.copy()
    df[timestamp_col] = pd.to_datetime(df[timestamp_col], utc=True, errors="coerce")
    df = df[df[timestamp_col].notna()].copy()

    if df.empty:
        return None

    created_at = pd.to_datetime(created_at, utc=True, errors="coerce")
    if pd.isna(created_at):
        return None

    window_end = created_at + timedelta(minutes=window_minutes)

    df = df[
        (df[timestamp_col] >= created_at) &
        (df[timestamp_col] <= window_end)
    ].copy()

    if df.empty:
        return None

    return df[timestamp_col].min()

def select_first_available_snapshot_timestamp(
    created_at: pd.Timestamp,
    history_df: pd.DataFrame,
    timestamp_col: str = "ts",
    max_window_minutes: int | None = None,
) -> pd.Timestamp | None:
    """
    Select the earliest available history timestamp at or after created_at.

    If max_window_minutes is provided, require:
        created_at <= timestamp <= created_at + max_window_minutes

    Returns None if no valid timestamp exists.
    """
    if created_at is None or pd.isna(created_at):
        return None

    if history_df is None or history_df.empty:
        return None

    if timestamp_col not in history_df.columns:
        raise ValueError(f"Missing timestamp column: {timestamp_col}")

    df = history_df.copy()
    df[timestamp_col] = pd.to_datetime(df[timestamp_col], utc=True, errors="coerce")
    df = df[df[timestamp_col].notna()].copy()

    if df.empty:
        return None

    created_at = pd.to_datetime(created_at, utc=True, errors="coerce")
    if pd.isna(created_at):
        return None

    df = df[df[timestamp_col] >= created_at].copy()

    if max_window_minutes is not None:
        window_end = created_at + pd.Timedelta(minutes=max_window_minutes)
        df = df[df[timestamp_col] <= window_end].copy()

    if df.empty:
        return None

    return df[timestamp_col].min()

def select_first_available_snapshot_timestamp(
    created_at: pd.Timestamp,
    history_df: pd.DataFrame,
    timestamp_col: str = "ts",
    max_window_minutes: int | None = None,
) -> pd.Timestamp | None:
    if created_at is None or pd.isna(created_at):
        return None

    if history_df is None or history_df.empty:
        return None

    if timestamp_col not in history_df.columns:
        raise ValueError(f"Missing timestamp column: {timestamp_col}")

    df = history_df.copy()
    df[timestamp_col] = pd.to_datetime(df[timestamp_col], utc=True, errors="coerce")
    df = df[df[timestamp_col].notna()].copy()

    if df.empty:
        return None

    created_at = pd.to_datetime(created_at, utc=True, errors="coerce")
    if pd.isna(created_at):
        return None

    df = df[df[timestamp_col] >= created_at].copy()

    if max_window_minutes is not None:
        window_end = created_at + pd.Timedelta(minutes=max_window_minutes)
        df = df[df[timestamp_col] <= window_end].copy()

    if df.empty:
        return None

    return df[timestamp_col].min()

def attach_open_snapshot_timestamp(
    markets_df: pd.DataFrame,
    history_df: pd.DataFrame,
    market_id_col: str = "market_id",
    created_at_col: str = "created_at",
    history_timestamp_col: str = "timestamp",
    window_minutes: int = 60,
) -> pd.DataFrame:
    """
    For each market in markets_df, attach an `open_snapshot_ts` chosen from
    the corresponding rows in history_df using the strict open-window rule.

    Markets with no valid open snapshot receive None in `open_snapshot_ts`.
    """
    required_market_cols = {market_id_col, created_at_col}
    missing_market_cols = required_market_cols - set(markets_df.columns)
    if missing_market_cols:
        raise ValueError(f"Missing market columns: {sorted(missing_market_cols)}")

    if market_id_col not in history_df.columns:
        raise ValueError(f"Missing history market id column: {market_id_col}")
    if history_timestamp_col not in history_df.columns:
        raise ValueError(f"Missing history timestamp column: {history_timestamp_col}")

    out = markets_df.copy()
    out[created_at_col] = pd.to_datetime(out[created_at_col], utc=True, errors="coerce")

    history = history_df.copy()
    history[history_timestamp_col] = pd.to_datetime(
        history[history_timestamp_col], utc=True, errors="coerce"
    )

    open_timestamps: list[pd.Timestamp | None] = []

    for _, row in out.iterrows():
        market_id = row[market_id_col]
        created_at = row[created_at_col]

        market_history = history[history[market_id_col] == market_id].copy()

        open_ts = select_open_snapshot_timestamp(
            created_at=created_at,
            history_df=market_history,
            timestamp_col=history_timestamp_col,
            window_minutes=window_minutes,
        )
        open_timestamps.append(open_ts)

    out["open_snapshot_ts"] = open_timestamps
    return out
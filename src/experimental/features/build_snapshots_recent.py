from __future__ import annotations

import ast
import json
from pathlib import Path
from typing import Any

import pandas as pd

from src.features.open_snapshot_selection import (
    select_first_available_snapshot_timestamp,
    select_open_snapshot_timestamp,
)
from src.ingest.price_history import fetch_price_history, history_to_df
from src.utils.io import read_parquet, write_parquet

INPUT_PATH = Path("data/processed/markets_recent.parquet")
OPEN_OUT = Path("data/processed/features_open_recent.parquet")
MID_OUT = Path("data/processed/features_mid_recent.parquet")
T24_OUT = Path("data/processed/features_24h_recent.parquet")


def _parse_token_ids(value: Any) -> list[str]:
    if value is None:
        return []

    if hasattr(value, "tolist"):
        try:
            value = value.tolist()
        except Exception:
            pass

    if isinstance(value, tuple):
        value = list(value)

    if isinstance(value, list):
        return [str(x) for x in value if x is not None]

    if isinstance(value, str):
        text = value.strip()
        if not text:
            return []

        try:
            parsed = json.loads(text)
            if isinstance(parsed, list):
                return [str(x) for x in parsed if x is not None]
        except json.JSONDecodeError:
            pass

        try:
            parsed = ast.literal_eval(text)
            if isinstance(parsed, list):
                return [str(x) for x in parsed if x is not None]
        except (ValueError, SyntaxError):
            pass

    return []


def _get_primary_token_id(row: pd.Series) -> str | None:
    token_ids = _parse_token_ids(row.get("parsed_token_ids"))
    if not token_ids:
        return None
    return token_ids[0]


def _fetch_history_df(token_id: str) -> pd.DataFrame:
    raw_history = fetch_price_history(token_id)
    history_df = history_to_df(raw_history)
    if history_df.empty:
        return history_df
    history_df["ts"] = pd.to_datetime(history_df["ts"], utc=True, errors="coerce")
    history_df = history_df[history_df["ts"].notna()].copy()
    return history_df.sort_values("ts").reset_index(drop=True)


def build_snapshots_recent() -> None:
    df = read_parquet(INPUT_PATH).copy()
    print(f"[INFO] recent markets loaded: {len(df)}")

    df = df[df["resolved_outcome"].notna()].copy()
    print(f"[INFO] after resolved_outcome filter: {len(df)}")

    open_rows = []
    mid_rows = []
    t24_rows = []

    skipped_t24_short_markets = 0
    skipped_open_missing_token = 0
    skipped_open_no_valid_price_24h = 0
    strict_open_60m_rows = 0

    for _, row in df.iterrows():
        open_ts = pd.Timestamp(row["open_ts"])
        close_ts = pd.Timestamp(row["close_ts"])
        duration_hours = float(row["duration_hours"])

        mid_ts = open_ts + (close_ts - open_ts) / 2
        t24_ts = close_ts - pd.Timedelta(hours=24)

        base = {
            "market_id": row["market_id"],
            "platform": row["platform"],
            "question": row["question"],
            "category": row["category"],
            "category_fallback": row["category_fallback"],
            "open_ts": row["open_ts"],
            "close_ts": row["close_ts"],
            "resolved_outcome": row["resolved_outcome"],
            "label_status": row["label_status"],
            "duration_hours": row["duration_hours"],
            "parsed_token_ids": row["parsed_token_ids"],
            "parsed_outcomes": row["parsed_outcomes"],
            "volume": row["volume"],
            "liquidity": row["liquidity"],
            "volume_num": row["volume_num"],
            "liquidity_num": row["liquidity_num"],
        }

        # OPEN
        primary_token_id = _get_primary_token_id(row)
        if primary_token_id is None:
            skipped_open_missing_token += 1
        else:
            try:
                history_df = _fetch_history_df(primary_token_id)
            except Exception:
                history_df = pd.DataFrame(columns=["ts", "price"])

            strict_open_ts = select_open_snapshot_timestamp(
                created_at=open_ts,
                history_df=history_df,
                timestamp_col="ts",
                window_minutes=60,
            )

            if strict_open_ts is not None:
                strict_open_60m_rows += 1

            practical_open_ts = select_first_available_snapshot_timestamp(
                created_at=open_ts,
                history_df=history_df,
                timestamp_col="ts",
                max_window_minutes=24 * 60,
            )

            if practical_open_ts is None:
                skipped_open_no_valid_price_24h += 1
            else:
                minutes_from_open = (practical_open_ts - open_ts).total_seconds() / 60.0

                open_rows.append({
                    **base,
                    "snapshot_type": "open",
                    "target_ts": open_ts,
                    "snapshot_ts": practical_open_ts,
                    "strict_open_snapshot_ts_60m": strict_open_ts,
                    "strict_open_available_60m": strict_open_ts is not None,
                    "minutes_from_open_to_snapshot": minutes_from_open,
                    "time_to_resolution_hours": (close_ts - practical_open_ts).total_seconds() / 3600.0,
                })

        # MID
        mid_rows.append({
            **base,
            "snapshot_type": "mid",
            "target_ts": mid_ts,
            "snapshot_ts": mid_ts,
            "time_to_resolution_hours": (close_ts - mid_ts).total_seconds() / 3600.0,
        })

        # 24H
        if duration_hours >= 24:
            t24_rows.append({
                **base,
                "snapshot_type": "t_minus_24h",
                "target_ts": t24_ts,
                "snapshot_ts": t24_ts,
                "time_to_resolution_hours": 24.0,
            })
        else:
            skipped_t24_short_markets += 1

    open_df = pd.DataFrame(open_rows)
    mid_df = pd.DataFrame(mid_rows)
    t24_df = pd.DataFrame(t24_rows)

    print(f"[INFO] open snapshot rows (practical <=24h): {len(open_df)}")
    print(f"[INFO] strict open rows (<=60m): {strict_open_60m_rows}")
    print(f"[INFO] mid snapshot rows: {len(mid_df)}")
    print(f"[INFO] 24h snapshot rows: {len(t24_df)}")
    print(f"[INFO] skipped open missing token: {skipped_open_missing_token}")
    print(f"[INFO] skipped open no valid price in 24h window: {skipped_open_no_valid_price_24h}")
    print(f"[INFO] short-duration markets skipped for 24h snapshot: {skipped_t24_short_markets}")

    write_parquet(open_df, OPEN_OUT)
    write_parquet(mid_df, MID_OUT)
    write_parquet(t24_df, T24_OUT)

    print(f"[OK] Wrote {len(open_df)} open snapshot rows to {OPEN_OUT}")
    print(f"[OK] Wrote {len(mid_df)} mid snapshot rows to {MID_OUT}")
    print(f"[OK] Wrote {len(t24_df)} 24h snapshot rows to {T24_OUT}")


if __name__ == "__main__":
    build_snapshots_recent()
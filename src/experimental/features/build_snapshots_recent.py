from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.utils.io import read_parquet, write_parquet

INPUT_PATH = Path("data/processed/markets_recent.parquet")
OPEN_OUT = Path("data/processed/features_open_recent.parquet")
MID_OUT = Path("data/processed/features_mid_recent.parquet")
T24_OUT = Path("data/processed/features_24h_recent.parquet")


def build_snapshots_recent() -> None:
    df = read_parquet(INPUT_PATH).copy()
    df = df[df["resolved_outcome"].notna()].copy()

    open_rows = []
    mid_rows = []
    t24_rows = []

    skipped_t24_short_markets = 0

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

        open_rows.append({
            **base,
            "snapshot_type": "open",
            "target_ts": open_ts,
            "snapshot_ts": open_ts,
            "time_to_resolution_hours": duration_hours,
        })

        mid_rows.append({
            **base,
            "snapshot_type": "mid",
            "target_ts": mid_ts,
            "snapshot_ts": mid_ts,
            "time_to_resolution_hours": (close_ts - mid_ts).total_seconds() / 3600.0,
        })

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

    write_parquet(open_df, OPEN_OUT)
    write_parquet(mid_df, MID_OUT)
    write_parquet(t24_df, T24_OUT)

    print(f"[OK] Wrote {len(open_df)} open snapshot rows to {OPEN_OUT}")
    print(f"[OK] Wrote {len(mid_df)} mid snapshot rows to {MID_OUT}")
    print(f"[OK] Wrote {len(t24_df)} 24h snapshot rows to {T24_OUT}")
    print(f"[INFO] Short-duration markets skipped for 24h snapshot: {skipped_t24_short_markets}")


if __name__ == "__main__":
    build_snapshots_recent()
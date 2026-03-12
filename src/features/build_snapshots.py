from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.utils.io import read_parquet, write_parquet

MARKETS_PATH = Path("data/processed/markets.parquet")
OUT_OPEN = Path("data/processed/features_open.parquet")
OUT_MID = Path("data/processed/features_mid.parquet")
OUT_24H = Path("data/processed/features_24h.parquet")


def build_snapshots() -> None:
    markets = read_parquet(MARKETS_PATH).copy()

    # Keep only rows with confident labels for modelling
    markets = markets[markets["resolved_outcome"].notna()].copy()

    open_rows = []
    mid_rows = []
    t24_rows = []

    for _, row in markets.iterrows():
        open_ts = row["open_ts"]
        close_ts = row["close_ts"]

        if pd.isna(open_ts) or pd.isna(close_ts):
            continue

        mid_ts = open_ts + (close_ts - open_ts) / 2
        t24_ts = close_ts - pd.Timedelta(hours=24)

        base = {
            "market_id": row["market_id"],
            "platform": row["platform"],
            "question": row["question"],
            "category": row["category"],
            "open_ts": row["open_ts"],
            "close_ts": row["close_ts"],
            "resolved_outcome": row["resolved_outcome"],
            "label_status": row["label_status"],
            "duration_hours": row["duration_hours"],
            "parsed_token_ids": row["parsed_token_ids"],
            "parsed_outcomes": row["parsed_outcomes"],
        }

        open_rows.append(
            {
                **base,
                "snapshot_type": "open",
                "target_ts": open_ts,
                "snapshot_ts": open_ts,
                "time_to_resolution_hours": (close_ts - open_ts).total_seconds() / 3600.0,
            }
        )

        mid_rows.append(
            {
                **base,
                "snapshot_type": "mid",
                "target_ts": mid_ts,
                "snapshot_ts": mid_ts,
                "time_to_resolution_hours": (close_ts - mid_ts).total_seconds() / 3600.0,
            }
        )

        t24_rows.append(
            {
                **base,
                "snapshot_type": "t_minus_24h",
                "target_ts": t24_ts,
                "snapshot_ts": t24_ts,
                "time_to_resolution_hours": (close_ts - t24_ts).total_seconds() / 3600.0,
            }
        )

    write_parquet(pd.DataFrame(open_rows), OUT_OPEN)
    write_parquet(pd.DataFrame(mid_rows), OUT_MID)
    write_parquet(pd.DataFrame(t24_rows), OUT_24H)

    print(f"[OK] Wrote {len(open_rows)} open snapshot rows to {OUT_OPEN}")
    print(f"[OK] Wrote {len(mid_rows)} mid snapshot rows to {OUT_MID}")
    print(f"[OK] Wrote {len(t24_rows)} 24h snapshot rows to {OUT_24H}")


if __name__ == "__main__":
    build_snapshots()
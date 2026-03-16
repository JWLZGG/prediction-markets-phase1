from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.features.leakage_checks import (
    assert_required_columns,
    assert_open_before_close,
    assert_snapshot_before_close,
    assert_snapshot_not_before_open,
    assert_no_duplicate_market_snapshot_rows,
    assert_midpoint_between_open_and_close,
    assert_t_minus_24h_is_exact,
)

OPEN_PATH = Path("data/processed/features_open_recent.parquet")
MID_PATH = Path("data/processed/features_mid_recent.parquet")
T24_PATH = Path("data/processed/features_24h_recent.parquet")


def run_checks_for_file(path: Path) -> None:
    print(f"\n[INFO] Checking {path}")
    df = pd.read_parquet(path)

    assert_required_columns(
        df,
        ["market_id", "snapshot_type", "snapshot_ts", "open_ts", "close_ts"],
    )
    assert_open_before_close(df)
    assert_snapshot_before_close(df)
    assert_snapshot_not_before_open(df)
    assert_no_duplicate_market_snapshot_rows(df)

    snapshot_types = set(df["snapshot_type"].astype(str).unique())

    if "mid" in snapshot_types:
        assert_midpoint_between_open_and_close(df)

    if "t_minus_24h" in snapshot_types:
        assert_t_minus_24h_is_exact(df)

    print(f"[OK] Passed integrity checks for {path}")
    print(f"[INFO] Rows checked: {len(df)}")


def run_integrity_checks_recent() -> None:
    for path in [OPEN_PATH, MID_PATH, T24_PATH]:
        run_checks_for_file(path)

    print("\n[OK] All recent snapshot integrity checks passed")


if __name__ == "__main__":
    run_integrity_checks_recent()
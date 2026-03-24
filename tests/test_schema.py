import pandas as pd
from src.features.leakage_checks import assert_required_columns


def test_required_columns_exist():
    df = pd.DataFrame(
        {
            "market_id": [1],
            "snapshot_ts": ["2026-01-01"],
            "close_ts": ["2026-01-02"],
        }
    )
    assert_required_columns(df, ["market_id", "snapshot_ts", "close_ts"])
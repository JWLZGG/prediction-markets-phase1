from pathlib import Path
import pandas as pd
import shutil
import uuid

from src.detect.polymarket_live_complement import scan_polymarket_complements
from src.ingest.polymarket_orderbook import _normalize_side, _parse_token_ids


def test_parse_token_ids_from_json_string():
    value = '["123", "456"]'
    result = _parse_token_ids(value)
    assert result == ["123", "456"]


def test_parse_token_ids_invalid_returns_empty():
    value = "not-json"
    result = _parse_token_ids(value)
    assert result == []


def test_normalize_levels_filters_bad_rows():
    levels = [
        {"price": "0.42", "size": "10"},
        {"price": "0.43", "size": "0"},
        {"price": None, "size": "5"},
    ]
    result = _normalize_side(levels, side="asks")
    assert result == [{"price": 0.42, "size": 10.0}]


def test_scan_polymarket_complements_uses_multi_level_depth():
    scratch_dir = Path("artifacts/test_tmp") / f"poly_depth_{uuid.uuid4().hex}"
    scratch_dir.mkdir(parents=True, exist_ok=True)
    path = scratch_dir / "orderbooks.parquet"
    df = pd.DataFrame(
        [
            {
                "market_id": "M1",
                "question": "Will X happen?",
                "token_id": "YES1",
                "token_side": "yes",
                "bids": [],
                "asks": [{"price": 0.47, "size": 40}, {"price": 0.49, "size": 60}],
                "raw_book": {"book": "yes"},
            },
            {
                "market_id": "M1",
                "question": "Will X happen?",
                "token_id": "NO1",
                "token_side": "no",
                "bids": [],
                "asks": [{"price": 0.46, "size": 100}],
                "raw_book": {"book": "no"},
            },
        ]
    )

    try:
        df.to_parquet(path, index=False)

        flags, stats = scan_polymarket_complements(
            path=path,
            target_size=100.0,
            threshold_bps=100.0,
        )

        assert stats["paired_markets"] == 1
        assert stats["sufficient_size"] == 1
        assert len(flags) == 1
    finally:
        shutil.rmtree(scratch_dir, ignore_errors=True)

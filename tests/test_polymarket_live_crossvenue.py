from __future__ import annotations

import shutil
import uuid
from pathlib import Path

import pandas as pd

from src.detect.polymarket_live_crossvenue import scan_matched_crossvenue_pairs


def test_scan_matched_crossvenue_pairs_emits_flag_for_usable_direction() -> None:
    scratch_dir = Path("artifacts/test_tmp") / f"crossv_{uuid.uuid4().hex}"
    scratch_dir.mkdir(parents=True, exist_ok=True)

    poly_path = scratch_dir / "poly_orderbooks.parquet"
    kalshi_path = scratch_dir / "kalshi_current.parquet"
    matched_path = scratch_dir / "matched.yaml"

    try:
        df_poly = pd.DataFrame(
            [
                {
                    "market_id": "PM1",
                    "question": "Q1",
                    "token_id": "PM1-Y",
                    "token_side": "yes",
                    "bids": [{"price": 0.49, "size": 100.0}],
                    "asks": [{"price": 0.50, "size": 100.0}],
                    "raw_book": {"book": "yes"},
                },
                {
                    "market_id": "PM1",
                    "question": "Q1",
                    "token_id": "PM1-N",
                    "token_side": "no",
                    "bids": [{"price": 0.51, "size": 100.0}],
                    "asks": [{"price": 0.52, "size": 100.0}],
                    "raw_book": {"book": "no"},
                },
            ]
        )
        df_poly.to_parquet(poly_path, index=False)

        df_kalshi = pd.DataFrame(
            [
                {
                    "ticker": "KAL1",
                    "question": "Q1",
                    "yes_ask": 0.53,
                    "yes_bid": 0.55,
                    "no_ask": None,
                    "no_bid": None,
                    "raw_market": {"market_type": "binary"},
                }
            ]
        )
        df_kalshi.to_parquet(kalshi_path, index=False)

        matched_path.write_text(
            "\n".join(
                [
                    "pairs:",
                    "  - pair_id: pair1",
                    "    label: test pair",
                    "    polymarket:",
                    "      market_id: PM1",
                        "      side: \"yes\"",
                    "    kalshi:",
                    "      ticker: KAL1",
                        "      side: \"yes\"",
                ]
            ),
            encoding="utf-8",
        )

        fee_config = {
            "venues": {
                "polymarket": {"taker_fee_bps": 0, "slippage_buffer_bps": 0, "fixed_buffer": 0.0},
                "kalshi": {"taker_fee_bps": 0, "slippage_buffer_bps": 0, "fixed_buffer": 0.0},
            }
        }

        flags, stats = scan_matched_crossvenue_pairs(
            matched_config_path=matched_path,
            polymarket_orderbooks_path=poly_path,
            kalshi_current_path=kalshi_path,
            target_size=100.0,
            threshold_bps=10.0,
            fee_config=fee_config,
        )

        assert stats["pairs_total"] == 1
        assert stats["pairs_found_on_both_venues"] == 1
        assert stats["pairs_with_usable_buy_sell_paths"] >= 1
        assert stats["flags_emitted"] == len(flags)
        assert len(flags) == 1

        f0 = flags[0]
        assert f0["flag_type"] == "cross_venue_divergence"
        assert f0["market_id"] == "pair1"
        assert f0["venue_a"] == "polymarket"
        assert f0["venue_b"] == "kalshi"

        assert "details" in f0
        assert f0["details"]["should_flag"] is True
        assert float(f0["details"]["net_edge_bps"]) >= 10.0
        assert "inputs" in f0
        assert "buy_asks" in f0["inputs"]
        assert "sell_bids" in f0["inputs"]
    finally:
        shutil.rmtree(scratch_dir, ignore_errors=True)


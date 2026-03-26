from pathlib import Path

from src.utils.matched_markets import load_matched_prediction_pairs


def test_load_matched_prediction_pairs():
    pairs = load_matched_prediction_pairs(Path("configs/matched_prediction_markets.yaml"))
    assert isinstance(pairs, list)
    assert len(pairs) >= 1
    assert "pair_id" in pairs[0]
    assert "polymarket" in pairs[0]
    assert "kalshi" in pairs[0]
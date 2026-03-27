from pathlib import Path

import yaml

from src.utils.matched_markets import load_matched_prediction_pairs


def test_load_matched_prediction_pairs():
    config_path = Path("configs/matched_prediction_markets.yaml")
    pairs = load_matched_prediction_pairs(config_path)
    assert isinstance(pairs, list)

    with config_path.open("r", encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}

    assert isinstance(raw.get("pairs", []), list)
    assert isinstance(raw.get("candidate_pairs_manual_review", []), list)

    for pair in pairs:
        assert "pair_id" in pair
        assert "polymarket" in pair
        assert "kalshi" in pair

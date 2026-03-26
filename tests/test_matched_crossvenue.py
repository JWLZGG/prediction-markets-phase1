from src.detect.matched_crossvenue import scan_matched_crossvenue_pairs


def test_scan_matched_crossvenue_pairs_runs():
    flags, stats = scan_matched_crossvenue_pairs(target_size=10.0, threshold_bps=10.0)
    assert isinstance(flags, list)
    assert "pairs_total" in stats
    assert "pairs_found_on_both_venues" in stats
    assert "pairs_with_usable_buy_sell_paths" in stats
    assert "flags_emitted" in stats
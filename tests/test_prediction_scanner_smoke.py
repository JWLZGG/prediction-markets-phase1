from src.detect.logging_runner import build_synthetic_flags


def test_synthetic_scanner_has_flags():
    flags = build_synthetic_flags()
    assert isinstance(flags, list)
    assert len(flags) >= 1
    assert "flag_type" in flags[0]
    assert "market_id" in flags[0]
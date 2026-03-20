from src.detect.kalshi_live_complement import extract_kalshi_top_book, scan_kalshi_complements


def test_extract_kalshi_top_book_valid_row():
    row = {
        "market_id": "TEST1",
        "ticker": "TEST1-TICKER",
        "question": "Will X happen?",
        "status": "active",
        "yes_ask": 0.47,
        "no_ask": 0.46,
        "raw_market": {
            "market_type": "binary",
            "yes_ask_size_fp": "150.00",
            "no_ask_size_fp": "120.00",
        },
    }

    result = extract_kalshi_top_book(row)
    assert result is not None
    assert result["market_id"] == "TEST1"
    assert result["yes_asks"][0]["price"] == 0.47
    assert result["no_asks"][0]["price"] == 0.46
    assert result["yes_asks"][0]["size"] == 150.0
    assert result["no_asks"][0]["size"] == 120.0


def test_extract_kalshi_top_book_rejects_non_binary():
    row = {
        "market_id": "TEST2",
        "ticker": "TEST2-TICKER",
        "question": "Bad market",
        "status": "active",
        "yes_ask": 0.47,
        "no_ask": 0.46,
        "raw_market": {
            "market_type": "scalar",
            "yes_ask_size_fp": "150.00",
            "no_ask_size_fp": "120.00",
        },
    }

    result = extract_kalshi_top_book(row)
    assert result is None


def test_extract_kalshi_top_book_rejects_missing_sizes():
    row = {
        "market_id": "TEST3",
        "ticker": "TEST3-TICKER",
        "question": "No size market",
        "status": "active",
        "yes_ask": 0.47,
        "no_ask": 0.46,
        "raw_market": {
            "market_type": "binary",
            "yes_ask_size_fp": "0.00",
            "no_ask_size_fp": "120.00",
        },
    }

    result = extract_kalshi_top_book(row)
    assert result is None

def test_extract_kalshi_top_book_can_derive_no_ask_from_yes_bid():
    row = {
        "market_id": "TEST4",
        "ticker": "TEST4-TICKER",
        "question": "Derived no ask market",
        "status": "active",
        "yes_ask": None,
        "no_ask": None,
        "yes_bid": None,
        "no_bid": None,
        "raw_market": {
            "market_type": "binary",
            "yes_ask_dollars": "0.55",
            "yes_ask_size_fp": "3600.00",
            "yes_bid_dollars": "0.45",
            "yes_bid_size_fp": "2400.00",
            "no_ask_dollars": "1.0000",
            "no_ask_size_fp": None,
        },
    }

    result = extract_kalshi_top_book(row)
    assert result is not None
    assert result["yes_asks"][0]["price"] == 0.55
    assert result["yes_asks"][0]["size"] == 3600.0
    assert result["no_asks"][0]["price"] == 0.55  # 1 - 0.45
    assert result["no_asks"][0]["size"] == 2400.0

def test_scan_kalshi_complements_on_live_file_runs():
    flags, stats = scan_kalshi_complements(target_size=10.0, threshold_bps=100.0)

    assert "rows_total" in stats
    assert "eligible_top_book" in stats
    assert "sufficient_size" in stats
    assert "flags_emitted" in stats
    assert isinstance(flags, list)
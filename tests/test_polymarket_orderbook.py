from src.ingest.polymarket_orderbook import _normalize_side, _parse_token_ids


def test_parse_token_ids_from_json_string():
    value = '["123", "456"]'
    result = _parse_token_ids(value)
    assert result == ["123", "456"]


def test_parse_token_ids_invalid_returns_empty():
    value = "not-json"
    result = _parse_token_ids(value)
    assert result == []


def test_normalize_side_filters_bad_rows():
    levels = [
        {"price": "0.42", "size": "10"},
        {"price": "0.43", "size": "0"},
        {"price": None, "size": "5"},
    ]
    result = _normalize_side(levels, side="asks")
    assert result == [{"price": 0.42, "size": 10.0}]
import math

from src.detect.executable_pricing import (
    BookLevel,
    get_executable_buy_price,
    get_executable_sell_price,
    walk_book,
)


def test_buy_single_level_full_fill():
    asks = [BookLevel(price=0.62, size=100)]
    result = get_executable_buy_price(asks, target_size=50)

    assert result.executable is True
    assert math.isclose(result.avg_price, 0.62, rel_tol=1e-9)
    assert math.isclose(result.total_size, 50.0, rel_tol=1e-9)
    assert math.isclose(result.total_cost, 31.0, rel_tol=1e-9)
    assert result.levels_used == 1
    assert math.isclose(result.unfilled_size, 0.0, rel_tol=1e-9)


def test_buy_multi_level_vwap():
    asks = [
        BookLevel(price=0.62, size=40),
        BookLevel(price=0.64, size=60),
    ]
    result = get_executable_buy_price(asks, target_size=100)

    assert result.executable is True
    assert math.isclose(result.avg_price, 0.632, rel_tol=1e-9)
    assert math.isclose(result.total_size, 100.0, rel_tol=1e-9)
    assert math.isclose(result.total_cost, 63.2, rel_tol=1e-9)
    assert result.levels_used == 2
    assert math.isclose(result.unfilled_size, 0.0, rel_tol=1e-9)


def test_buy_insufficient_liquidity():
    asks = [
        BookLevel(price=0.62, size=40),
        BookLevel(price=0.64, size=20),
    ]
    result = get_executable_buy_price(asks, target_size=100)

    assert result.executable is False
    assert math.isclose(result.avg_price, (40 * 0.62 + 20 * 0.64) / 60, rel_tol=1e-9)
    assert math.isclose(result.total_size, 60.0, rel_tol=1e-9)
    assert math.isclose(result.unfilled_size, 40.0, rel_tol=1e-9)
    assert result.levels_used == 2


def test_sell_uses_descending_bids():
    bids = [
        BookLevel(price=0.59, size=50),
        BookLevel(price=0.61, size=30),
        BookLevel(price=0.58, size=100),
    ]
    result = get_executable_sell_price(bids, target_size=60)

    expected_cost = (30 * 0.61) + (30 * 0.59)
    expected_avg = expected_cost / 60

    assert result.executable is True
    assert math.isclose(result.avg_price, expected_avg, rel_tol=1e-9)
    assert math.isclose(result.total_size, 60.0, rel_tol=1e-9)
    assert result.levels_used == 2
    assert math.isclose(result.unfilled_size, 0.0, rel_tol=1e-9)


def test_unordered_input_is_sorted_correctly():
    asks = [
        {"price": 0.65, "size": 50},
        {"price": 0.62, "size": 20},
        {"price": 0.64, "size": 30},
    ]
    result = walk_book(asks, target_size=50, side="asks")

    expected_cost = (20 * 0.62) + (30 * 0.64)
    expected_avg = expected_cost / 50

    assert result.executable is True
    assert math.isclose(result.avg_price, expected_avg, rel_tol=1e-9)
    assert result.levels_used == 2


def test_zero_or_negative_target_size_raises():
    asks = [BookLevel(price=0.62, size=100)]

    try:
        get_executable_buy_price(asks, target_size=0)
        assert False, "Expected ValueError for target_size=0"
    except ValueError:
        pass

    try:
        get_executable_buy_price(asks, target_size=-10)
        assert False, "Expected ValueError for target_size<0"
    except ValueError:
        pass
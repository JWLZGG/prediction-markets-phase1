from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Literal

BookSide = Literal["asks", "bids"]


@dataclass(frozen=True)
class BookLevel:
    price: float
    size: float


@dataclass(frozen=True)
class ExecutionResult:
    executable: bool
    avg_price: float | None
    total_size: float
    total_cost: float
    levels_used: int
    unfilled_size: float


def _normalize_levels(levels: Iterable[BookLevel | dict]) -> list[BookLevel]:
    normalized: list[BookLevel] = []

    for level in levels:
        if isinstance(level, BookLevel):
            price = float(level.price)
            size = float(level.size)
        else:
            price = float(level["price"])
            size = float(level["size"])

        if price < 0:
            raise ValueError(f"Price must be non-negative, got {price}")
        if size < 0:
            raise ValueError(f"Size must be non-negative, got {size}")

        if size == 0:
            continue

        normalized.append(BookLevel(price=price, size=size))

    return normalized


def walk_book(
    levels: Iterable[BookLevel | dict],
    target_size: float,
    side: BookSide,
) -> ExecutionResult:
    """
    Walk an order book side and compute the executable VWAP for the requested size.

    For asks:
        - sorted ascending by price
        - used for buy execution

    For bids:
        - sorted descending by price
        - used for sell execution
    """
    if target_size <= 0:
        raise ValueError(f"target_size must be > 0, got {target_size}")

    normalized = _normalize_levels(levels)

    if side == "asks":
        ordered = sorted(normalized, key=lambda x: x.price)
    elif side == "bids":
        ordered = sorted(normalized, key=lambda x: x.price, reverse=True)
    else:
        raise ValueError(f"Unknown side: {side}")

    remaining = float(target_size)
    total_cost = 0.0
    total_filled = 0.0
    levels_used = 0

    for level in ordered:
        if remaining <= 0:
            break

        fill_size = min(level.size, remaining)
        total_cost += fill_size * level.price
        total_filled += fill_size
        remaining -= fill_size
        levels_used += 1

    if total_filled == 0:
        return ExecutionResult(
            executable=False,
            avg_price=None,
            total_size=0.0,
            total_cost=0.0,
            levels_used=0,
            unfilled_size=float(target_size),
        )

    avg_price = total_cost / total_filled

    return ExecutionResult(
        executable=(remaining == 0),
        avg_price=avg_price,
        total_size=total_filled,
        total_cost=total_cost,
        levels_used=levels_used,
        unfilled_size=max(0.0, remaining),
    )


def get_executable_buy_price(
    asks: Iterable[BookLevel | dict],
    target_size: float,
) -> ExecutionResult:
    return walk_book(levels=asks, target_size=target_size, side="asks")


def get_executable_sell_price(
    bids: Iterable[BookLevel | dict],
    target_size: float,
) -> ExecutionResult:
    return walk_book(levels=bids, target_size=target_size, side="bids")

if __name__ == "__main__":
    asks = [
        BookLevel(price=0.62, size=40),
        BookLevel(price=0.64, size=60),
    ]
    bids = [
        BookLevel(price=0.61, size=30),
        BookLevel(price=0.59, size=50),
    ]

    buy_result = get_executable_buy_price(asks, target_size=100)
    sell_result = get_executable_sell_price(bids, target_size=60)

    print("[INFO] Buy execution result:")
    print(buy_result)

    print("\n[INFO] Sell execution result:")
    print(sell_result)
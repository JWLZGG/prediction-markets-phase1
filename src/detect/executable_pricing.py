from dataclasses import dataclass
from typing import List, Literal

Side = Literal["buy", "sell"]

@dataclass
class BookLevel:
    price: float
    size: float

@dataclass
class ExecutionResult:
    executable: bool
    avg_price: float | None
    total_size: float
    total_cost: float | None
    levels_used: int
    unfilled_size: float
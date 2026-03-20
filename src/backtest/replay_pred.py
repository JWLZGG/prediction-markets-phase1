from __future__ import annotations

"""
Prediction-market replay/backtest placeholder.

Phase 1 status:
- monitor outputs and reports are produced
- replay of logged executable opportunities is not yet implemented
"""

from dataclasses import dataclass
from typing import Any


@dataclass
class ReplayStatus:
    module: str
    status: str
    phase: str
    implemented_now: list[str]
    next_steps: list[str]


def get_replay_status() -> ReplayStatus:
    return ReplayStatus(
        module="src.backtest.replay_pred",
        status="placeholder",
        phase="Phase 1",
        implemented_now=[
            "offline model evaluation",
            "current scored market outputs",
            "monitor report generation",
        ],
        next_steps=[
            "replay logged prediction opportunities",
            "latency-aware feasibility checks",
            "false-positive estimation",
            "weekly replay summary metrics",
        ],
    )


def run_replay_pred(*args: Any, **kwargs: Any) -> None:
    raise NotImplementedError(
        "Prediction replay/backtest is not implemented in Phase 1. "
        "This is a Phase 2 extension after scanner event logging exists."
    )


if __name__ == "__main__":
    status = get_replay_status()
    print(status)
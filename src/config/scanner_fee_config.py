from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


def _repo_root() -> Path:
    # src/config/scanner_fee_config.py -> src/config -> src -> repo root
    return Path(__file__).resolve().parents[2]


def _default_fee_config_fallback() -> dict[str, Any]:
    # These match the hardcoded values that existed before this module.
    return {
        "venues": {
            "polymarket": {
                "taker_fee_bps": 0,
                "slippage_buffer_bps": 10,
                "fixed_buffer": 0.0,
            },
            "kalshi": {
                "taker_fee_bps": 25,
                "slippage_buffer_bps": 10,
                "fixed_buffer": 0.0,
            },
        }
    }


def load_scanner_config(config_path: Path | None = None) -> dict[str, Any]:
    if config_path is None:
        config_path = _repo_root() / "configs" / "prediction_scanner.yaml"

    try:
        with config_path.open("r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
    except FileNotFoundError:
        return _default_fee_config_fallback()

    if not isinstance(data, dict):
        return _default_fee_config_fallback()

    return data


def get_default_fee_config() -> dict[str, Any]:
    """
    Returns the fee config block expected by `src.detect.fees.compute_fee_breakdown`.

    Prefer `configs/prediction_scanner.yaml` if present; otherwise fall back to legacy
    hardcoded values.
    """

    cfg = load_scanner_config()
    venues = cfg.get("venues")
    if isinstance(venues, dict) and venues:
        return {"venues": venues}

    return _default_fee_config_fallback()


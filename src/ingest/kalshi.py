from __future__ import annotations

"""
Kalshi ingestion module.

Phase 1 status:
- current/open Kalshi ingestion is implemented in `src.ingest.kalshi_current`
- historical/resolved Kalshi ingestion is not yet implemented here

This module exists so the repo structure is explicit and future work has a
clear place to live.
"""

from pathlib import Path
import json


def phase1_status() -> dict:
    return {
        "module": "src.ingest.kalshi",
        "status": "placeholder",
        "implemented_in_phase1": [
            "current market ingestion via src.ingest.kalshi_current",
        ],
        "not_yet_implemented": [
            "historical/resolved Kalshi ingestion",
            "Kalshi snapshot/history training pipeline",
        ],
    }


def save_phase1_status_report(
    output_path: str | Path = "artifacts/outputs/kalshi_phase1_status.json",
) -> Path:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(phase1_status(), indent=2), encoding="utf-8")
    return path


def ingest_kalshi_historical(*args, **kwargs):
    raise NotImplementedError(
        "Historical/resolved Kalshi ingestion is not implemented in Phase 1. "
        "Use `src.ingest.kalshi_current` for current-market ingestion."
    )


if __name__ == "__main__":
    out = save_phase1_status_report()
    print(f"[OK] Wrote Kalshi Phase 1 status report to {out}")
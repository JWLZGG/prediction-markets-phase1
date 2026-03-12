from __future__ import annotations

import requests
from typing import Any


def fetch_price_history(url: str, params: dict[str, Any] | None = None) -> dict | list:
    response = requests.get(url, params=params, timeout=30)
    response.raise_for_status()
    return response.json()
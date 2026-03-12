from __future__ import annotations

import pandas as pd


def to_utc_timestamp(value):
    return pd.to_datetime(value, utc=True, errors="coerce")
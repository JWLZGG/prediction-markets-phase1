from __future__ import annotations

from typing import Any

import pandas as pd
import requests


PRICE_HISTORY_URL = "https://clob.polymarket.com/prices-history"


def fetch_price_history(
    token_id: str,
    interval: str = "max",
    fidelity: int = 720,
    timeout: int = 30,
) -> dict:
    resp = requests.get(
        "https://clob.polymarket.com/prices-history",
        params={
            "market": token_id,
            "interval": interval,
            "fidelity": fidelity,
        },
        timeout=timeout,
    )
    resp.raise_for_status()
    return resp.json()


def history_to_df(history_json: dict) -> pd.DataFrame:
    rows = history_json.get("history", [])
    if not rows:
        return pd.DataFrame(columns=["ts", "price"])

    df = pd.DataFrame(rows).copy()
    df["ts"] = pd.to_datetime(df["t"], unit="s", utc=True, errors="coerce")
    df["price"] = pd.to_numeric(df["p"], errors="coerce")
    df = df.dropna(subset=["ts", "price"]).sort_values("ts").reset_index(drop=True)
    return df[["ts", "price"]]


def nearest_prob_at_or_before(target_ts: pd.Timestamp, hist_df: pd.DataFrame) -> float | None:
    if hist_df.empty:
        return None

    target_ts = pd.Timestamp(target_ts)
    if target_ts.tzinfo is None:
        target_ts = target_ts.tz_localize("UTC")
    else:
        target_ts = target_ts.tz_convert("UTC")

    work = hist_df.copy()
    work["ts"] = pd.to_datetime(work["ts"], utc=True, errors="coerce")
    work = work.dropna(subset=["ts", "price"]).sort_values("ts")

    eligible = work[work["ts"] <= target_ts]
    if not eligible.empty:
        return float(eligible.iloc[-1]["price"])

    # Optional tiny tolerance fallback: if the first point is within 10 minutes after target,
    # treat it as the nearest available proxy.
    after = work[work["ts"] > target_ts]
    if not after.empty:
        delta = after.iloc[0]["ts"] - target_ts
        if delta <= pd.Timedelta(minutes=10):
            return float(after.iloc[0]["price"])

    return None


def fetch_prob_at_or_before(
    token_id: str,
    target_ts: pd.Timestamp,
    interval: str = "max",
    fidelity: int = 720,
    timeout: int = 30,
) -> float | None:
    history_json = fetch_price_history(
        token_id=token_id,
        interval=interval,
        fidelity=fidelity,
        timeout=timeout,
    )
    hist_df = history_to_df(history_json)
    return nearest_prob_at_or_before(target_ts, hist_df)

def nearest_prob_at_or_after(target_ts: pd.Timestamp, hist_df: pd.DataFrame) -> float | None:
    if hist_df.empty:
        return None

    target_ts = pd.Timestamp(target_ts)
    if target_ts.tzinfo is None:
        target_ts = target_ts.tz_localize("UTC")
    else:
        target_ts = target_ts.tz_convert("UTC")

    eligible = hist_df[hist_df["ts"] >= target_ts].copy()

    if eligible.empty:
        return None
    
def fetch_prob_at_or_after(
    token_id: str,
    target_ts: pd.Timestamp,
    interval: str = "max",
    fidelity: int = 720,
    timeout: int = 30,
) -> float | None:
    history_json = fetch_price_history(
        token_id=token_id,
        interval=interval,
        fidelity=fidelity,
        timeout=timeout,
    )
    hist_df = history_to_df(history_json)
    return nearest_prob_at_or_after(target_ts, hist_df)


    return float(eligible.iloc[0]["price"])

    return nearest_prob_at_or_before(target_ts, hist_df)

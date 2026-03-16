from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from src.ingest.price_history import fetch_prob_at_or_before
from src.utils.io import read_parquet, write_parquet

INPUT_PATH = Path("data/processed/features_24h.parquet")
OUTPUT_PATH = Path("data/processed/features_24h_enriched.parquet")


def extract_first_token_id(token_ids: Any) -> str | None:
    if isinstance(token_ids, list) and len(token_ids) >= 1:
        return str(token_ids[0])
    return None


def enrich_market_probs() -> None:
    df = read_parquet(INPUT_PATH).copy()

    df["market_token_id"] = df["parsed_token_ids"].apply(extract_first_token_id)

    probs = []
    for i, row in df.iterrows():
        token_id = row["market_token_id"]
        target_ts = row["target_ts"]

        if token_id is None or pd.isna(target_ts):
            probs.append(None)
            continue

        try:
            prob = fetch_prob_at_or_before(
                token_id=token_id,
                target_ts=pd.Timestamp(target_ts),
                interval="max",
                fidelity=720,
                timeout=30,
            )
            probs.append(prob)
        except Exception as e:
            print(f"[WARN] row={i} market_id={row.get('market_id')} failed: {repr(e)}")
            probs.append(None)

        if (i + 1) % 25 == 0:
            print(f"[INFO] processed {i + 1}/{len(df)} rows")

    df["market_implied_prob"] = probs

    write_parquet(df, OUTPUT_PATH)

    print(f"[OK] Wrote enriched features to {OUTPUT_PATH}")
    print(f"[INFO] Rows written: {len(df)}")
    print(f"[INFO] Non-null market_implied_prob: {df['market_implied_prob'].notna().sum()}")


if __name__ == "__main__":
    enrich_market_probs()
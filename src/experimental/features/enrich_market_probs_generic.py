from __future__ import annotations

from pathlib import Path
from typing import Any
import json

import pandas as pd

from src.ingest.price_history import fetch_prob_at_or_before


def extract_first_token_id(token_ids: Any) -> str | None:
    if token_ids is None:
        return None

    if isinstance(token_ids, (list, tuple)):
        return str(token_ids[0]) if len(token_ids) >= 1 else None

    try:
        if hasattr(token_ids, "__len__") and not isinstance(token_ids, str):
            return str(token_ids[0]) if len(token_ids) >= 1 else None
    except Exception:
        pass

    if isinstance(token_ids, str):
        try:
            parsed = json.loads(token_ids)
            if isinstance(parsed, list) and len(parsed) >= 1:
                return str(parsed[0])
        except Exception:
            return None

    return None


def enrich_file(input_path: Path, output_path: Path) -> None:
    df = pd.read_parquet(input_path).copy()

    df["market_token_id"] = df["parsed_token_ids"].apply(extract_first_token_id)

    print(df["market_token_id"].head(10))
    print("non-null token ids:", df["market_token_id"].notna().sum())

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
    df.to_parquet(output_path, index=False)

    print(f"[OK] Wrote enriched features to {output_path}")
    print(f"[INFO] Rows written: {len(df)}")
    print(f"[INFO] Non-null market_implied_prob: {df['market_implied_prob'].notna().sum()}")
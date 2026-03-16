from __future__ import annotations

import pandas as pd

from src.ingest.polymarket import fetch_markets, build_raw_markets_dataframe


def run_probe() -> None:
    offsets = [0, 50, 100, 200, 500, 1000, 2000, 3000, 4000, 5000, 7500, 10000, 20000]

    for offset in offsets:
        try:
            raw = fetch_markets(
                limit=50,
                closed=True,
                extra_params={"offset": offset},
            )
            df = build_raw_markets_dataframe(raw)

            print(f"\n=== offset={offset} ===")
            if df.empty:
                print("No rows returned.")
                continue

            print(df[["market_id", "question", "created_at", "end_date"]]
                  .sort_values("end_date", ascending=False)
                  .head(10))
            print("max end_date:", df["end_date"].max())
            print("min end_date:", df["end_date"].min())

        except Exception as e:
            print(f"\n=== offset={offset} FAILED ===")
            print(repr(e))


if __name__ == "__main__":
    run_probe()
from __future__ import annotations

from pathlib import Path
import numpy as np
import pandas as pd

from src.utils.io import read_parquet, write_parquet

INPUT_PATH = Path("data/processed/kalshi_markets_current.parquet")
OUTPUT_PATH = Path("data/processed/kalshi_current_features.parquet")


def categorize_question(text: str) -> str:
    t = str(text).lower()

    sports_terms = [
        "nba", "nfl", "mlb", "nhl", "fifa", "ufc", "tennis", "masters",
        "world cup", "qualify", "winner", "set ", "match", "goals",
        "totals", "spread", "coritiba", "mirassol", "hurkacz", "quinn",
        "atp", "wta", "soccer", "football", "baseball", "basketball",
        "hockey", "golf", "innings", "points", "rebounds", "threes"
    ]
    politics_terms = [
        "trump", "biden", "election", "senate", "president", "house",
        "governor", "democrat", "republican", "prime minister",
        "magyar", "orbán", "nomination", "gabbard"
    ]
    crypto_terms = [
        "btc", "bitcoin", "eth", "ethereum", "sol", "crypto", "token",
        "airdrop", "defi", "stablecoin"
    ]
    macro_terms = [
        "fed", "rates", "rate cut", "rate hike", "cpi", "inflation",
        "oil", "wti", "brent", "silver", "gold", "settle", "front-month",
        "yield", "treasury", "commodity"
    ]
    culture_terms = [
        "movie", "album", "oscar", "actor", "actress", "song", "netflix",
        "album sales", "chart", "survivor"
    ]
    business_terms = [
        "openai", "tesla", "apple", "amazon", "meta", "microsoft",
        "market cap", "earnings", "sales", "electronic arts"
    ]

    if any(k in t for k in sports_terms):
        return "Sports"
    if any(k in t for k in politics_terms):
        return "Politics"
    if any(k in t for k in crypto_terms):
        return "Crypto"
    if any(k in t for k in macro_terms):
        return "Macro/Commodities"
    if any(k in t for k in culture_terms):
        return "Culture/Entertainment"
    if any(k in t for k in business_terms):
        return "Business/Tech"
    return "Other"

    if any(k in t for k in sports_terms):
        return "Sports"
    if any(k in t for k in politics_terms):
        return "Politics"
    if any(k in t for k in crypto_terms):
        return "Crypto"
    if any(k in t for k in culture_terms):
        return "Culture/Entertainment"
    if any(k in t for k in business_terms):
        return "Business/Tech"
    return "Other"


def derive_market_prob(row: pd.Series):
    yes_bid = pd.to_numeric(row.get("yes_bid_dollars"), errors="coerce")
    yes_ask = pd.to_numeric(row.get("yes_ask_dollars"), errors="coerce")
    last_price = pd.to_numeric(row.get("last_price_dollars"), errors="coerce")

    if pd.notna(yes_bid) and pd.notna(yes_ask):
        p = float((yes_bid + yes_ask) / 2.0)
    elif pd.notna(yes_bid):
        p = float(yes_bid)
    elif pd.notna(yes_ask):
        p = float(yes_ask)
    elif pd.notna(last_price):
        p = float(last_price)
    else:
        return None

    if p > 1:
        p = p / 100.0

    if p < 0 or p > 1:
        return None

    return p


def run_build_kalshi_current_features() -> None:
    df = read_parquet(INPUT_PATH).copy()

    now_ts = pd.Timestamp.utcnow()
    if now_ts.tzinfo is None:
        now_ts = now_ts.tz_localize("UTC")
    else:
        now_ts = now_ts.tz_convert("UTC")

    df = df[df["status"].astype(str).str.lower().isin(["open", "active"])].copy()

    df = df[
        df["raw_market"].apply(
            lambda x: isinstance(x, dict) and x.get("market_type") == "binary"
        )
    ].copy()

    df = df[~df["ticker"].astype(str).str.startswith("KXMVE")].copy()

    df["open_ts"] = pd.to_datetime(df["open_time"], utc=True, errors="coerce")
    df["close_ts"] = pd.to_datetime(df["close_time"], utc=True, errors="coerce")

    df = df[df["close_ts"].notna() & (df["close_ts"] > now_ts)].copy()
    df = df.reset_index(drop=True)

    df["yes_bid_dollars"] = df["raw_market"].apply(
        lambda x: x.get("yes_bid_dollars") if isinstance(x, dict) else None
    )
    df["yes_ask_dollars"] = df["raw_market"].apply(
        lambda x: x.get("yes_ask_dollars") if isinstance(x, dict) else None
    )
    df["no_bid_dollars"] = df["raw_market"].apply(
        lambda x: x.get("no_bid_dollars") if isinstance(x, dict) else None
    )
    df["no_ask_dollars"] = df["raw_market"].apply(
        lambda x: x.get("no_ask_dollars") if isinstance(x, dict) else None
    )
    df["last_price_dollars"] = df["raw_market"].apply(
        lambda x: x.get("last_price_dollars") if isinstance(x, dict) else None
    )

    df["volume"] = df["raw_market"].apply(
        lambda x: x.get("volume_fp") if isinstance(x, dict) else None
    )
    df["open_interest"] = df["raw_market"].apply(
        lambda x: x.get("open_interest_fp") if isinstance(x, dict) else None
    )

    for col in [
        "yes_bid_dollars",
        "yes_ask_dollars",
        "no_bid_dollars",
        "no_ask_dollars",
        "last_price_dollars",
        "volume",
        "open_interest",
    ]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df["market_implied_prob"] = df.apply(derive_market_prob, axis=1)
    df["category_fallback"] = df["question"].apply(categorize_question)

    df["time_to_close_hours"] = (df["close_ts"] - now_ts).dt.total_seconds() / 3600.0
    df["duration_hours"] = (df["close_ts"] - df["open_ts"]).dt.total_seconds() / 3600.0

    df["volume_num"] = pd.to_numeric(df["volume"], errors="coerce")
    df["open_interest_num"] = pd.to_numeric(df["open_interest"], errors="coerce")
    df["log_volume"] = np.log1p(df["volume_num"])

    print("[INFO] Sample extracted quote columns:")
    print(
        df[
            [
                "ticker",
                "yes_bid_dollars",
                "yes_ask_dollars",
                "last_price_dollars",
                "market_implied_prob",
            ]
        ].head(10).to_string(index=False)
    )

    print(f"[INFO] Rows before final filter: {len(df)}")
    print(f"[INFO] Non-null market_implied_prob: {df['market_implied_prob'].notna().sum()}")
    print(f"[INFO] market_implied_prob > 0: {(df['market_implied_prob'] > 0).sum()}")
    print(f"[INFO] market_implied_prob < 1: {(df['market_implied_prob'] < 1).sum()}")
    print(
        f"[INFO] time_to_close_hours between 6 and 720: "
        f"{((df['time_to_close_hours'] >= 6) & (df['time_to_close_hours'] <= 720)).sum()}"
    )

    df = df[
        df["market_implied_prob"].notna()
        & (df["market_implied_prob"] > 0.0)
        & (df["market_implied_prob"] < 1.0)
        & (df["time_to_close_hours"] >= 6)
        & (df["time_to_close_hours"] <= 720)
    ].copy()

    keep_cols = [
        "market_id",
        "ticker",
        "question",
        "status",
        "category_fallback",
        "open_ts",
        "close_ts",
        "time_to_close_hours",
        "duration_hours",
        "volume",
        "volume_num",
        "log_volume",
        "open_interest",
        "open_interest_num",
        "yes_bid_dollars",
        "yes_ask_dollars",
        "no_bid_dollars",
        "no_ask_dollars",
        "last_price_dollars",
        "market_implied_prob",
    ]

    out_df = df[keep_cols].copy()
    write_parquet(out_df, OUTPUT_PATH)

    print(f"[OK] Wrote Kalshi current features to {OUTPUT_PATH}")
    print(f"[INFO] Rows written: {len(out_df)}")
    print(f"[INFO] Non-null market_implied_prob: {out_df['market_implied_prob'].notna().sum()}")
    print("[INFO] Category mix:")
    print(out_df["category_fallback"].value_counts(dropna=False).head(10))


if __name__ == "__main__":
    run_build_kalshi_current_features()
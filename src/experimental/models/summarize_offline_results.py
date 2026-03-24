from __future__ import annotations

from pathlib import Path
import numpy as np
import pandas as pd

from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import brier_score_loss
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

OUTPUT_CSV = Path("reports/offline_snapshot_summary.csv")
OUTPUT_MD = Path("reports/offline_snapshot_summary.md")

SNAPSHOTS = {
    "open": Path("data/processed/features_open_recent_enriched.parquet"),
    "mid": Path("data/processed/features_mid_recent_history_enriched.parquet"),
    "24h": Path("data/processed/features_24h_recent_history_enriched.parquet"),
}


def build_pipeline(numeric_features: list[str], categorical_features: list[str]) -> Pipeline:
    numeric_transformer = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
        ]
    )

    categorical_transformer = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="most_frequent")),
            ("onehot", OneHotEncoder(handle_unknown="ignore")),
        ]
    )

    preprocessor = ColumnTransformer(
        transformers=[
            ("num", numeric_transformer, numeric_features),
            ("cat", categorical_transformer, categorical_features),
        ]
    )

    model = Pipeline(
        steps=[
            ("preprocessor", preprocessor),
            ("classifier", LogisticRegression(max_iter=3000, random_state=42)),
        ]
    )
    return model


def brier_skill_score(model_brier: float, baseline_brier: float) -> float | None:
    if baseline_brier == 0:
        return None
    return 1.0 - (model_brier / baseline_brier)


def load_snapshot(path: Path) -> pd.DataFrame:
    df = pd.read_parquet(path).copy()

    if "volume" in df.columns and "log_volume" not in df.columns:
        df["log_volume"] = np.log1p(pd.to_numeric(df["volume"], errors="coerce"))

    if "liquidity" in df.columns and "log_liquidity" not in df.columns:
        df["log_liquidity"] = np.log1p(pd.to_numeric(df["liquidity"], errors="coerce"))

    if "market_implied_prob" in df.columns and "distance_from_0_5" not in df.columns:
        df["distance_from_0_5"] = (
            pd.to_numeric(df["market_implied_prob"], errors="coerce") - 0.5
        ).abs()

    if "prob_change_24h" not in df.columns:
        df["prob_change_24h"] = 0.0

    if "history_points_count" not in df.columns:
        df["history_points_count"] = 0.0

    if "minutes_from_open_to_snapshot" not in df.columns:
        df["minutes_from_open_to_snapshot"] = np.nan

    if "strict_open_available_60m" not in df.columns:
        df["strict_open_available_60m"] = False

    return df


def evaluate_snapshot(snapshot_name: str, path: Path) -> dict:
    if not path.exists():
        return {
            "snapshot": snapshot_name,
            "rows_used": 0,
            "strict_open_rows_60m": np.nan,
            "avg_minutes_from_open_to_snapshot": np.nan,
            "naive_brier": np.nan,
            "market_brier": np.nan,
            "model_brier": np.nan,
            "bss_vs_naive": np.nan,
            "bss_vs_market": np.nan,
            "takeaway": "missing file",
        }

    df = load_snapshot(path)

    df = df[df["resolved_outcome"].notna()].copy()
    df = df[df["market_implied_prob"].notna()].copy()

    if len(df) == 0:
        return {
            "snapshot": snapshot_name,
            "rows_used": 0,
            "strict_open_rows_60m": np.nan,
            "avg_minutes_from_open_to_snapshot": np.nan,
            "naive_brier": np.nan,
            "market_brier": np.nan,
            "model_brier": np.nan,
            "bss_vs_naive": np.nan,
            "bss_vs_market": np.nan,
            "takeaway": "no usable rows",
        }

    numeric_features = [
        c for c in [
            "duration_hours",
            "market_implied_prob",
            "log_volume",
            "log_liquidity",
            "distance_from_0_5",
            "prob_change_24h",
            "history_points_count",
            "minutes_from_open_to_snapshot",
        ] if c in df.columns
    ]
    categorical_features = [c for c in ["category_fallback"] if c in df.columns]

    X = df[numeric_features + categorical_features].copy()
    y = df["resolved_outcome"].astype(int)

    pipeline = build_pipeline(numeric_features, categorical_features)
    pipeline.fit(X, y)
    model_pred = pipeline.predict_proba(X)[:, 1]

    naive_pred = np.full(len(df), 0.5)
    market_pred = pd.to_numeric(df["market_implied_prob"], errors="coerce").values

    naive_brier = brier_score_loss(y, naive_pred)
    market_brier = brier_score_loss(y, market_pred)
    model_brier = brier_score_loss(y, model_pred)

    bss_naive = brier_skill_score(model_brier, naive_brier)
    bss_market = brier_skill_score(model_brier, market_brier)

    if model_brier < market_brier:
        takeaway = "model beats market"
    elif model_brier > market_brier:
        takeaway = "market beats model"
    else:
        takeaway = "tie vs market"

    strict_open_rows_60m = (
        int(df["strict_open_available_60m"].fillna(False).sum())
        if snapshot_name == "open" and "strict_open_available_60m" in df.columns
        else np.nan
    )

    avg_minutes_from_open = (
        float(pd.to_numeric(df["minutes_from_open_to_snapshot"], errors="coerce").mean())
        if snapshot_name == "open" and "minutes_from_open_to_snapshot" in df.columns
        else np.nan
    )

    return {
        "snapshot": snapshot_name,
        "rows_used": int(len(df)),
        "strict_open_rows_60m": strict_open_rows_60m,
        "avg_minutes_from_open_to_snapshot": avg_minutes_from_open,
        "naive_brier": float(naive_brier),
        "market_brier": float(market_brier),
        "model_brier": float(model_brier),
        "bss_vs_naive": float(bss_naive) if bss_naive is not None else np.nan,
        "bss_vs_market": float(bss_market) if bss_market is not None else np.nan,
        "takeaway": takeaway,
    }


def markdown_table(df: pd.DataFrame) -> str:
    if df.empty:
        return "_No rows_"

    cols = list(df.columns)
    header = "| " + " | ".join(cols) + " |"
    sep = "| " + " | ".join(["---"] * len(cols)) + " |"

    rows = []
    for _, row in df.iterrows():
        vals = []
        for c in cols:
            v = row[c]
            if pd.isna(v):
                vals.append("")
            elif isinstance(v, float):
                vals.append(f"{v:.6f}")
            else:
                vals.append(str(v))
        rows.append("| " + " | ".join(vals) + " |")

    return "\n".join([header, sep] + rows)


def run_summarize_offline_results() -> None:
    results = []
    for snapshot_name, path in SNAPSHOTS.items():
        results.append(evaluate_snapshot(snapshot_name, path))

    out_df = pd.DataFrame(results)

    OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    out_df.to_csv(OUTPUT_CSV, index=False)

    md_parts = [
        "# Offline Snapshot Summary\n",
        "This compares naive, market, and model Brier scores across open, mid, and 24h snapshots.\n",
        "\n",
        "Open is reported using the practical v1 definition: first available observed price within 24 hours of market creation.\n",
        "A strict 60-minute open definition is retained as a diagnostic only, and current history data supports very few such rows.\n",
        "\n",
        markdown_table(out_df),
        "\n",
    ]
    OUTPUT_MD.write_text("\n".join(md_parts), encoding="utf-8")

    print(f"[OK] Wrote offline summary CSV to {OUTPUT_CSV}")
    print(f"[OK] Wrote offline summary markdown to {OUTPUT_MD}")
    print("\n[INFO] Offline summary:")
    print(out_df.to_string(index=False))


if __name__ == "__main__":
    run_summarize_offline_results()
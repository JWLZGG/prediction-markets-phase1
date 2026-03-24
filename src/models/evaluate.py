from __future__ import annotations

from pathlib import Path

import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import brier_score_loss
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder

from src.utils.io import read_parquet

INPUT_PATH = Path("data/processed/features_24h_recent_history_enriched.parquet")
OUTPUT_PATH = Path("reports/offline_snapshot_summary.md")


def _build_model() -> Pipeline:
    numeric_features = [
        "duration_hours",
        "market_implied_prob",
        "volume_num",
        "history_points_count",
        "prob_change_24h",
    ]
    categorical_features = ["category_fallback"]

    preprocessor = ColumnTransformer(
        transformers=[
            (
                "num",
                Pipeline(steps=[("imputer", SimpleImputer(strategy="median"))]),
                numeric_features,
            ),
            (
                "cat",
                Pipeline(
                    steps=[
                        ("imputer", SimpleImputer(strategy="most_frequent")),
                        ("onehot", OneHotEncoder(handle_unknown="ignore")),
                    ]
                ),
                categorical_features,
            ),
        ]
    )

    return Pipeline(
        steps=[
            ("preprocessor", preprocessor),
            ("classifier", LogisticRegression(max_iter=1000, random_state=42)),
        ]
    )


def run_evaluate() -> None:
    df = read_parquet(INPUT_PATH).copy()
    required_cols = [
        "resolved_outcome",
        "market_implied_prob",
        "category_fallback",
        "duration_hours",
        "volume_num",
        "history_points_count",
        "prob_change_24h",
    ]
    missing = [c for c in required_cols if c not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    df = df[df["resolved_outcome"].notna() & df["market_implied_prob"].notna()].copy()
    if len(df) < 10:
        raise ValueError("Need at least 10 rows with targets and market probabilities for evaluation")

    y = df["resolved_outcome"].astype(int)
    if y.nunique() < 2:
        raise ValueError("Need at least two classes in resolved_outcome for evaluation")

    feature_cols = [
        "category_fallback",
        "duration_hours",
        "market_implied_prob",
        "volume_num",
        "history_points_count",
        "prob_change_24h",
    ]
    X = df[feature_cols].copy()

    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=0.3,
        random_state=42,
        stratify=y,
    )

    model = _build_model()
    model.fit(X_train, y_train)
    model_probs = model.predict_proba(X_test)[:, 1]
    market_probs = X_test["market_implied_prob"].astype(float).values

    model_brier = brier_score_loss(y_test, model_probs)
    market_brier = brier_score_loss(y_test, market_probs)
    improvement = market_brier - model_brier

    report = "\n".join(
        [
            "# Offline Snapshot Evaluation",
            "",
            f"- Input path: `{INPUT_PATH}`",
            f"- Rows evaluated: `{len(df)}`",
            f"- Train rows: `{len(X_train)}`",
            f"- Test rows: `{len(X_test)}`",
            f"- Positive rate: `{y.mean():.4f}`",
            f"- Model Brier score: `{model_brier:.6f}`",
            f"- Market baseline Brier score: `{market_brier:.6f}`",
            f"- Brier improvement vs market: `{improvement:.6f}`",
        ]
    )

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(report + "\n", encoding="utf-8")

    print(f"[OK] Wrote offline evaluation summary to {OUTPUT_PATH}")
    print(report)


if __name__ == "__main__":
    run_evaluate()

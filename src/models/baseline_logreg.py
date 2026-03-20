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


def run_baseline_model() -> None:
    df = read_parquet(INPUT_PATH).copy()
    print(f"[INFO] Loaded rows from {INPUT_PATH}: {len(df)}")
    print(f"[INFO] Columns: {list(df.columns)}")

    if "resolved_outcome" not in df.columns:
        raise ValueError("resolved_outcome column missing")
    if "market_implied_prob" not in df.columns:
        raise ValueError("market_implied_prob column missing")

    print(f"[INFO] Non-null resolved_outcome: {df['resolved_outcome'].notna().sum()}")
    print(f"[INFO] Non-null market_implied_prob: {df['market_implied_prob'].notna().sum()}")

    df = df[df["resolved_outcome"].notna()].copy()
    print(f"[INFO] After resolved_outcome filter: {len(df)}")

    df = df[df["market_implied_prob"].notna()].copy()
    print(f"[INFO] After market_implied_prob filter: {len(df)}")

    if df.empty:
        print("[WARN] No rows remain after filtering. Exiting baseline run.")
        return

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

    y = df["resolved_outcome"].astype(int)

    feature_cols = [
        "category_fallback",
        "duration_hours",
        "market_implied_prob",
        "volume_num",
        "history_points_count",
        "prob_change_24h",
    ]
    X = df[feature_cols].copy()

    numeric_features = [
        "duration_hours",
        "market_implied_prob",
        "volume_num",
        "history_points_count",
        "prob_change_24h",
    ]
    categorical_features = ["category_fallback"]

    numeric_transformer = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="median")),
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
            ("classifier", LogisticRegression(max_iter=1000, random_state=42)),
        ]
    )

    if len(df) < 10:
        print(f"[WARN] Not enough rows to train/test split: {len(df)}")
        return

    if y.nunique() < 2:
        print("[WARN] Need at least two classes in resolved_outcome.")
        return

    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=0.3,
        random_state=42,
        stratify=y,
    )

    model.fit(X_train, y_train)
    y_prob = model.predict_proba(X_test)[:, 1]

    model_brier = brier_score_loss(y_test, y_prob)

    market_baseline_prob = X_test["market_implied_prob"].astype(float).values
    market_brier = brier_score_loss(y_test, market_baseline_prob)

    print(f"[INFO] Rows used: {len(df)}")
    print(f"[INFO] Train rows: {len(X_train)}")
    print(f"[INFO] Test rows: {len(X_test)}")
    print(f"[INFO] Model Brier score: {model_brier:.6f}")
    print(f"[INFO] Market baseline Brier score: {market_brier:.6f}")

    classifier = model.named_steps["classifier"]
    preprocessor_fitted = model.named_steps["preprocessor"]

    feature_names = preprocessor_fitted.get_feature_names_out()
    coefs = classifier.coef_[0]

    coef_df = pd.DataFrame(
        {
            "feature": feature_names,
            "coefficient": coefs,
        }
    ).sort_values("coefficient", ascending=False)

    print("\n[INFO] Top positive coefficients:")
    positive_df = coef_df.sort_values("coefficient", ascending=False).head(10)

    print("\n[INFO] Top negative coefficients:")
    negative_df = coef_df.sort_values("coefficient", ascending=True).head(10)


if __name__ == "__main__":
    run_baseline_model()
from __future__ import annotations

from pathlib import Path
import pickle

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

INPUT_PATH = Path("data/processed/features_24h_recent_history_enriched.parquet")
MODEL_PATH = Path("reports/best_24h_model.pkl")


def build_best_24h_pipeline() -> Pipeline:
    numeric_features = [
        "duration_hours",
        "market_implied_prob",
        "log_volume",
        "distance_from_0_5",
        "prob_change_24h",
        "history_points_count",
    ]
    categorical_features = ["category_fallback"]

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


def run_train_best_24h_model() -> None:
    df = pd.read_parquet(INPUT_PATH).copy()

    df["log_volume"] = np.log1p(pd.to_numeric(df["volume"], errors="coerce"))

    df = df[df["resolved_outcome"].notna()].copy()
    df = df[df["market_implied_prob"].notna()].copy()

    feature_cols = [
        "category_fallback",
        "duration_hours",
        "market_implied_prob",
        "log_volume",
        "distance_from_0_5",
        "prob_change_24h",
        "history_points_count",
    ]
    X = df[feature_cols].copy()
    y = df["resolved_outcome"].astype(int)

    model = build_best_24h_pipeline()
    model.fit(X, y)

    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(MODEL_PATH, "wb") as f:
        pickle.dump(model, f)

    print(f"[OK] Trained and saved best 24h model to {MODEL_PATH}")
    print(f"[INFO] Training rows used: {len(df)}")


if __name__ == "_main_":
    run_train_best_24h_model()
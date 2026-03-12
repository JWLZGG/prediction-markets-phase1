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

INPUT_PATH = Path("data/processed/features_24h.parquet")


def run_baseline_model() -> None:
    df = read_parquet(INPUT_PATH).copy()
    df = df[df["resolved_outcome"].notna()].copy()

    y = df["resolved_outcome"].astype(int)

    feature_cols = [
        "category",
        "duration_hours",
        "time_to_resolution_hours",
    ]
    X = df[feature_cols].copy()

    numeric_features = ["duration_hours", "time_to_resolution_hours"]
    categorical_features = ["category"]

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

    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=0.3,
        random_state=42,
        stratify=y,
    )

    model.fit(X_train, y_train)
    y_prob = model.predict_proba(X_test)[:, 1]

    brier = brier_score_loss(y_test, y_prob)

    print(f"[INFO] Rows used: {len(df)}")
    print(f"[INFO] Train rows: {len(X_train)}")
    print(f"[INFO] Test rows: {len(X_test)}")
    print(f"[INFO] Brier score: {brier:.6f}")

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
    print(coef_df.head(10).to_string(index=False))

    print("\n[INFO] Top negative coefficients:")
    print(coef_df.tail(10).to_string(index=False))


if __name__ == "__main__":
    run_baseline_model()
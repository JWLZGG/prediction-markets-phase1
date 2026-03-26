from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.calibration import calibration_curve
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import brier_score_loss
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder

INPUT_PATH = Path("data/processed/features_open_recent_enriched.parquet")
PLOT_PATH = Path("reports/calibration_open_recent.png")


def build_model():
    numeric_features = [
        "duration_hours",
        "market_implied_prob",
        "log_volume",
        "log_liquidity",
        "minutes_from_open_to_snapshot",
    ]
    categorical_features = ["category_fallback"]

    numeric_transformer = Pipeline(
        steps=[("imputer", SimpleImputer(strategy="median"))]
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


def evaluate_open_recent() -> None:
    df = pd.read_parquet(INPUT_PATH).copy()

    df["log_volume"] = np.log1p(pd.to_numeric(df["volume"], errors="coerce"))
    df["log_liquidity"] = np.log1p(pd.to_numeric(df["liquidity"], errors="coerce"))
    df["minutes_from_open_to_snapshot"] = pd.to_numeric(
        df["minutes_from_open_to_snapshot"], errors="coerce"
    )

    df = df[df["resolved_outcome"].notna()].copy()
    df = df[df["market_implied_prob"].notna()].copy()

    print(f"[INFO] Raw rows loaded: {len(pd.read_parquet(INPUT_PATH))}")
    print(f"[INFO] Rows after resolved_outcome filter: {df['resolved_outcome'].notna().sum()}")
    print(f"[INFO] Rows after market_implied_prob filter: {len(df)}")

    if df.empty:
        print("[WARN] No rows available for open evaluation.")
        return

    y = df["resolved_outcome"].astype(int)
    X = df[
        [
            "category_fallback",
            "duration_hours",
            "market_implied_prob",
            "log_volume",
            "log_liquidity",
            "minutes_from_open_to_snapshot",
        ]
    ].copy()

    if len(df) < 10:
        print(f"[WARN] Not enough rows for evaluation: {len(df)}")
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

    model = build_model()
    model.fit(X_train, y_train)
    y_prob = model.predict_proba(X_test)[:, 1]

    model_brier = brier_score_loss(y_test, y_prob)
    market_brier = brier_score_loss(
        y_test, X_test["market_implied_prob"].astype(float).values
    )

    print(f"[INFO] Rows used: {len(df)}")
    print(f"[INFO] Train rows: {len(X_train)}")
    print(f"[INFO] Test rows: {len(X_test)}")
    print(f"[INFO] Model Brier score: {model_brier:.6f}")
    print(f"[INFO] Market baseline Brier score: {market_brier:.6f}")
    print(
        f"[INFO] Strict 60m available rows in full open dataset: "
        f"{int(df['strict_open_available_60m'].fillna(False).sum()) if 'strict_open_available_60m' in df.columns else 'N/A'}"
    )

    prob_true, prob_pred = calibration_curve(
        y_test, y_prob, n_bins=10, strategy="quantile"
    )
    market_true, market_pred = calibration_curve(
        y_test,
        X_test["market_implied_prob"].astype(float).values,
        n_bins=10,
        strategy="quantile",
    )

    calib_df = pd.DataFrame(
        {
            "model_pred_mean": prob_pred,
            "model_true_rate": prob_true,
            "market_pred_mean": market_pred,
            "market_true_rate": market_true,
        }
    )
    print("\n[INFO] Calibration table:")
    print(calib_df.to_string(index=False))

    plt.figure(figsize=(7, 7))
    plt.plot([0, 1], [0, 1], linestyle="--")
    plt.plot(prob_pred, prob_true, marker="o", label="Model")
    plt.plot(market_pred, market_true, marker="s", label="Market baseline")
    plt.xlabel("Mean predicted probability")
    plt.ylabel("Observed frequency")
    plt.title("Calibration / Reliability Plot (Recent Open)")
    plt.legend()
    plt.tight_layout()
    plt.savefig(PLOT_PATH, dpi=150)
    print(f"[OK] Saved calibration plot to {PLOT_PATH}")

    classifier = model.named_steps["classifier"]
    preprocessor = model.named_steps["preprocessor"]
    feature_names = preprocessor.get_feature_names_out()
    coefs = classifier.coef_[0]

    coef_df = pd.DataFrame(
        {"feature": feature_names, "coefficient": coefs}
    ).sort_values("coefficient", ascending=False)

    print("\n[INFO] Top positive coefficients:")
    print(coef_df.head(15).to_string(index=False))

    print("\n[INFO] Top negative coefficients:")
    print(coef_df.tail(15).to_string(index=False))


if __name__ == "__main__":
    evaluate_open_recent()
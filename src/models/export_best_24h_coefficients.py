from __future__ import annotations

from pathlib import Path
import numpy as np
import pandas as pd

from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

INPUT_PATH = Path("data/processed/features_24h_recent_history_enriched.parquet")
OUTPUT_CSV = Path("reports/best_24h_coefficients.csv")
OUTPUT_MD = Path("reports/best_24h_coefficients.md")


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


def run_export_best_24h_coefficients() -> None:
    df = pd.read_parquet(INPUT_PATH).copy()

    if "log_volume" not in df.columns and "volume" in df.columns:
        df["log_volume"] = np.log1p(pd.to_numeric(df["volume"], errors="coerce"))

    if "distance_from_0_5" not in df.columns:
        df["distance_from_0_5"] = (pd.to_numeric(df["market_implied_prob"], errors="coerce") - 0.5).abs()

    if "prob_change_24h" not in df.columns:
        df["prob_change_24h"] = 0.0

    if "history_points_count" not in df.columns:
        df["history_points_count"] = 0.0

    df = df[df["resolved_outcome"].notna()].copy()
    df = df[df["market_implied_prob"].notna()].copy()

    numeric_features = [
        "duration_hours",
        "market_implied_prob",
        "log_volume",
        "distance_from_0_5",
        "prob_change_24h",
        "history_points_count",
    ]
    categorical_features = ["category_fallback"]

    X = df[numeric_features + categorical_features].copy()
    y = df["resolved_outcome"].astype(int)

    pipeline = build_pipeline(numeric_features, categorical_features)
    pipeline.fit(X, y)

    preprocessor = pipeline.named_steps["preprocessor"]
    classifier = pipeline.named_steps["classifier"]

    feature_names = preprocessor.get_feature_names_out()
    coefs = classifier.coef_[0]

    coef_df = pd.DataFrame({
        "feature": feature_names,
        "coefficient": coefs,
        "abs_coefficient": np.abs(coefs),
    }).sort_values("abs_coefficient", ascending=False)

    OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    coef_df.to_csv(OUTPUT_CSV, index=False)

    top_pos = coef_df.sort_values("coefficient", ascending=False).head(15)[["feature", "coefficient"]]
    top_neg = coef_df.sort_values("coefficient", ascending=True).head(15)[["feature", "coefficient"]]

    md_parts = [
        "# Best 24h Coefficients\n",
        "## Top positive coefficients\n",
        markdown_table(top_pos),
        "\n## Top negative coefficients\n",
        markdown_table(top_neg),
        "\n",
    ]
    OUTPUT_MD.write_text("\n".join(md_parts), encoding="utf-8")

    print(f"[OK] Wrote coefficient CSV to {OUTPUT_CSV}")
    print(f"[OK] Wrote coefficient markdown to {OUTPUT_MD}")
    print("\n[INFO] Top positive coefficients:")
    print(top_pos.to_string(index=False))
    print("\n[INFO] Top negative coefficients:")
    print(top_neg.to_string(index=False))


if __name__ == "__main__":
    run_export_best_24h_coefficients()
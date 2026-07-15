"""Train a simple loan approval model and report accuracy, precision, and F1 score.

Expected input:
- A CSV file named `loan_data.csv` in the project root, or pass a custom path
  as the first command-line argument.
- A target column named `approved` with values like 0/1, no/yes, or reject/approve.

This file is standalone and does not modify the Flask app.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, f1_score, precision_score, classification_report
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler


DEFAULT_DATASET = Path("loan_data.csv")
TARGET_COLUMN = "approved"


def _normalize_target(values: pd.Series) -> pd.Series:
    if values.dtype.kind in {"i", "u", "f"}:
        return values.astype(int)

    mapped = (
        values.astype(str)
        .str.strip()
        .str.lower()
        .map({
            "1": 1,
            "0": 0,
            "yes": 1,
            "no": 0,
            "approve": 1,
            "approved": 1,
            "reject": 0,
            "rejected": 0,
            "true": 1,
            "false": 0,
        })
    )

    if mapped.isna().any():
        raise ValueError(
            f"Target column '{TARGET_COLUMN}' contains unsupported values: "
            f"{sorted(values.astype(str).unique())}"
        )
    return mapped.astype(int)


def load_data(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(
            f"Dataset not found: {path}. Put your CSV there or pass a path to the script."
        )
    return pd.read_csv(path)


def build_model(data: pd.DataFrame) -> tuple[Pipeline, pd.DataFrame, pd.Series, pd.DataFrame, pd.Series]:
    if TARGET_COLUMN not in data.columns:
        raise ValueError(
            f"Dataset must contain a '{TARGET_COLUMN}' column for the prediction label."
        )

    data = data.dropna(subset=[TARGET_COLUMN]).copy()
    y = _normalize_target(data[TARGET_COLUMN])
    X = data.drop(columns=[TARGET_COLUMN])

    numeric_features = X.select_dtypes(include=["number"]).columns.tolist()
    categorical_features = [col for col in X.columns if col not in numeric_features]

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
            ("classifier", LogisticRegression(max_iter=2000)),
        ]
    )

    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=0.2,
        random_state=42,
        stratify=y if y.nunique() > 1 else None,
    )

    return model, X_train, X_test, y_train, y_test


def main() -> int:
    dataset_path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_DATASET
    data = load_data(dataset_path)
    model, X_train, X_test, y_train, y_test = build_model(data)

    model.fit(X_train, y_train)
    predictions = model.predict(X_test)

    accuracy = accuracy_score(y_test, predictions)
    precision = precision_score(y_test, predictions, zero_division=0)
    f1 = f1_score(y_test, predictions, zero_division=0)

    print(f"Dataset: {dataset_path}")
    print(f"Accuracy:  {accuracy:.4f}")
    print(f"Precision: {precision:.4f}")
    print(f"F1 Score:  {f1:.4f}")
    print("\nClassification report:")
    print(classification_report(y_test, predictions, zero_division=0))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

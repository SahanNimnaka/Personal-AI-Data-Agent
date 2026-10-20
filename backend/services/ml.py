
from typing import Any

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.dummy import DummyClassifier, DummyRegressor
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LinearRegression, LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    f1_score,
    mean_absolute_error,
    precision_score,
    r2_score,
    recall_score,
    root_mean_squared_error,
)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

RANDOM_SEED = 42
MIN_ROWS = 20
MIN_CLASS_COUNT = 2
MIN_CLASS_SAMPLES = 5


def _is_numeric(series: pd.Series) -> bool:
    return pd.api.types.is_numeric_dtype(series)


def _is_categorical(series: pd.Series) -> bool:
    return (
        pd.api.types.is_object_dtype(series)
        or pd.api.types.is_string_dtype(series)
        or isinstance(series.dtype, pd.CategoricalDtype)
        or pd.api.types.is_bool_dtype(series)
    )


def inspect_targets(df: pd.DataFrame) -> dict[str, Any]:
    """
    Report which columns can be used as ML targets and their task type.
    """
    if df.empty or len(df.columns) == 0:
        raise ValueError("The dataset must contain rows and columns.")

    if len(df) < MIN_ROWS:
        raise ValueError(
            f"At least {MIN_ROWS} rows are required to train models; "
            f"this dataset has {len(df)}."
        )

    targets = []

    for column in df.columns:
        series = df[column]
        non_null = series.dropna()

        if non_null.empty:
            task = None
        elif _is_numeric(series):
            if non_null.nunique() <= 1:
                task = None
            else:
                task = "regression"
        elif _is_categorical(series):
            if (
                non_null.nunique() >= MIN_CLASS_COUNT
                and non_null.value_counts().min() >= MIN_CLASS_SAMPLES
            ):
                task = "classification"
            else:
                task = None
        else:
            task = None

        targets.append(
            {
                "column": str(column),
                "dtype": str(series.dtype),
                "eligible": task is not None,
                "task": task,
                "missing_values": int(series.isna().sum()),
                "unique_values": int(non_null.nunique()),
            }
        )

    return {
        "row_count": int(len(df)),
        "columns": [str(c) for c in df.columns],
        "targets": targets,
    }


def _build_preprocessor(
    features: pd.DataFrame,
) -> ColumnTransformer:
    numeric_columns = [
        c for c in features.columns if _is_numeric(features[c])
    ]
    categorical_columns = [
        c for c in features.columns if not _is_numeric(features[c])
    ]

    numeric_pipeline = Pipeline(
        steps=[
            ("impute", SimpleImputer(strategy="median")),
            ("scale", StandardScaler()),
        ]
    )
    categorical_pipeline = Pipeline(
        steps=[
            ("impute", SimpleImputer(strategy="most_frequent")),
            (
                "encode",
                OneHotEncoder(handle_unknown="ignore", sparse_output=False),
            ),
        ]
    )

    return ColumnTransformer(
        transformers=[
            ("num", numeric_pipeline, numeric_columns),
            ("cat", categorical_pipeline, categorical_columns),
        ],
        remainder="drop",
    )


def _regression_candidates() -> list[tuple[str, Any]]:
    return [
        ("baseline_mean", DummyRegressor(strategy="mean")),
        ("linear_regression", LinearRegression()),
        (
            "random_forest",
            RandomForestRegressor(
                n_estimators=100, random_state=RANDOM_SEED
            ),
        ),
    ]


def _classification_candidates() -> list[tuple[str, Any]]:
    return [
        ("baseline_majority", DummyClassifier(strategy="most_frequent")),
        (
            "logistic_regression",
            LogisticRegression(max_iter=1000),
        ),
        (
            "random_forest",
            RandomForestClassifier(
                n_estimators=100, random_state=RANDOM_SEED
            ),
        ),
    ]


def _regression_metrics(y_true: pd.Series, y_pred: np.ndarray) -> dict:
    return {
        "mae": round(float(mean_absolute_error(y_true, y_pred)), 4),
        "rmse": round(float(root_mean_squared_error(y_true, y_pred)), 4),
        "r2": round(float(r2_score(y_true, y_pred)), 4),
    }


def _classification_metrics(y_true: pd.Series, y_pred: np.ndarray) -> dict:
    return {
        "accuracy": round(float(accuracy_score(y_true, y_pred)), 4),
        "precision": round(
            float(
                precision_score(
                    y_true, y_pred, average="weighted", zero_division=0
                )
            ),
            4,
        ),
        "recall": round(
            float(
                recall_score(
                    y_true, y_pred, average="weighted", zero_division=0
                )
            ),
            4,
        ),
        "f1": round(
            float(
                f1_score(
                    y_true, y_pred, average="weighted", zero_division=0
                )
            ),
            4,
        ),
    }


def _primary_metric(task: str, metrics: dict[str, float]) -> tuple[str, float]:
    if task == "regression":
        return "r2", metrics["r2"]
    return "f1", metrics["f1"]


def train_and_compare(
    df: pd.DataFrame,
    target_column: str,
    feature_columns: list[str] | None = None,
    task: str | None = None,
    test_size: float = 0.2,
) -> dict[str, Any]:
    """
    Train baseline and candidate models on held-out test data and compare
    them. Preprocessing is fit on the training split only to avoid
    leakage.
    """
    if df.empty or len(df.columns) == 0:
        raise ValueError("The dataset must contain rows and columns.")

    if target_column not in df.columns:
        raise ValueError(
            f"Target column '{target_column}' does not exist."
        )

    if not 0.1 <= test_size <= 0.5:
        raise ValueError(
            "test_size must be between 0.1 and 0.5."
        )

    if len(df) < MIN_ROWS:
        raise ValueError(
            f"At least {MIN_ROWS} rows are required to train models; "
            f"this dataset has {len(df)}."
        )

    target = df[target_column]

    if target.isna().all():
        raise ValueError(
            f"Target column '{target_column}' contains no usable values."
        )

    if task is None:
        if _is_numeric(target):
            task = "regression"
        elif _is_categorical(target):
            task = "classification"
        else:
            raise ValueError(
                f"Target column '{target_column}' has an unsupported "
                "type for machine learning."
            )

    if task not in {"regression", "classification"}:
        raise ValueError(
            f"Unsupported task '{task}'. Use regression or "
            "classification."
        )

    if task == "regression" and not _is_numeric(target):
        raise ValueError(
            f"Regression requires a numeric target; "
            f"'{target_column}' is not numeric."
        )

    if task == "classification" and not _is_categorical(target):
        raise ValueError(
            f"Classification requires a categorical target; "
            f"'{target_column}' is not categorical."
        )

    if feature_columns is None:
        feature_columns = [
            str(c) for c in df.columns if c != target_column
        ]

    if not feature_columns:
        raise ValueError("At least one feature column is required.")

    if target_column in feature_columns:
        raise ValueError(
            "The target column must not be included in the features."
        )

    missing_features = [
        c for c in feature_columns if c not in df.columns
    ]
    if missing_features:
        raise ValueError(
            "Unknown feature column(s): "
            + ", ".join(missing_features)
            + "."
        )

    # Build the working frame: target + features, dropping rows with a
    # missing target (cannot be used for supervised learning).
    data = df[[target_column, *feature_columns]].dropna(
        subset=[target_column]
    )

    if len(data) < MIN_ROWS:
        raise ValueError(
            f"After removing missing targets, only {len(data)} rows "
            f"remain; at least {MIN_ROWS} are required."
        )

    y = data[target_column]
    X = data[feature_columns]

    if task == "classification":
        class_counts = y.value_counts()
        if class_counts.min() < MIN_CLASS_SAMPLES:
            raise ValueError(
                "Each class needs at least "
                f"{MIN_CLASS_SAMPLES} samples for classification; "
                "the smallest class has "
                f"{int(class_counts.min())}."
            )

    stratify = y if task == "classification" else None

    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=test_size,
        random_state=RANDOM_SEED,
        stratify=stratify,
    )

    candidates = (
        _regression_candidates()
        if task == "regression"
        else _classification_candidates()
    )

    metric_fn = (
        _regression_metrics
        if task == "regression"
        else _classification_metrics
    )

    results = []

    for name, estimator in candidates:
        # A fresh preprocessor is fit only on the training split.
        pipeline = Pipeline(
            steps=[
                ("preprocess", _build_preprocessor(X_train)),
                ("model", estimator),
            ]
        )

        try:
            pipeline.fit(X_train, y_train)
            predictions = pipeline.predict(X_test)
            metrics = metric_fn(y_test, predictions)
        except (ValueError, TypeError) as error:
            results.append(
                {
                    "model": name,
                    "status": "failed",
                    "error": str(error),
                    "metrics": None,
                }
            )
            continue

        results.append(
            {
                "model": name,
                "status": "ok",
                "error": None,
                "metrics": metrics,
            }
        )

    successful = [r for r in results if r["status"] == "ok"]
    if not successful:
        raise ValueError(
            "All candidate models failed to train on this dataset."
        )

    primary_name, _ = _primary_metric(
        task, successful[0]["metrics"]
    )

    reverse = task == "regression"

    best = sorted(
        successful,
        key=lambda r: r["metrics"][primary_name],
        reverse=reverse,
    )[0]

    return {
        "task": task,
        "target_column": str(target_column),
        "target_type": (
            "numeric" if task == "regression" else "categorical"
        ),
        "feature_columns": list(feature_columns),
        "row_count": int(len(data)),
        "train_rows": int(len(X_train)),
        "test_rows": int(len(X_test)),
        "test_size": test_size,
        "random_seed": RANDOM_SEED,
        "primary_metric": primary_name,
        "best_model": best["model"],
        "models": results,
        "notes": (
            "Metrics are computed on held-out test data. The target "
            "column is excluded from features and preprocessing is fit "
            "on the training split only. Small datasets produce "
            "unreliable estimates."
        ),
    }

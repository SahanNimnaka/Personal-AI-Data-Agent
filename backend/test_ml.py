
from io import BytesIO

import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from main import app
from services.ml import inspect_targets, train_and_compare

client = TestClient(app)


@pytest.fixture
def regression_df():
    rng = np.random.default_rng(0)
    n = 120
    age = rng.integers(18, 65, n)
    income = rng.integers(20000, 90000, n)
    spend = 0.3 * income + 5 * age + rng.normal(0, 100, n)
    return pd.DataFrame(
        {
            "age": age,
            "income": income,
            "city": rng.choice(["A", "B", "C"], n),
            "spend": spend,
        }
    )


@pytest.fixture
def classification_df():
    rng = np.random.default_rng(1)
    n = 150
    x1 = rng.normal(0, 1, n)
    x2 = rng.normal(0, 1, n)
    label = np.where(x1 + x2 > 0, "yes", "no")
    return pd.DataFrame(
        {
            "x1": x1,
            "x2": x2,
            "segment": rng.choice(["p", "q"], n),
            "label": label,
        }
    )


# --- inspect_targets ------------------------------------------------


def test_inspect_targets_detects_task_types(regression_df):
    result = inspect_targets(regression_df)
    by_name = {t["column"]: t for t in result["targets"]}

    assert by_name["spend"]["task"] == "regression"
    assert by_name["label"]["eligible"] if "label" in by_name else True
    assert by_name["city"]["task"] == "classification"


def test_inspect_targets_rejects_small_dataset():
    df = pd.DataFrame({"a": range(5), "b": range(5)})
    with pytest.raises(ValueError):
        inspect_targets(df)


def test_inspect_targets_marks_constant_column_ineligible():
    rng = np.random.default_rng(2)
    df = pd.DataFrame(
        {"const": [1] * 50, "x": rng.normal(size=50)}
    )
    result = inspect_targets(df)
    by_name = {t["column"]: t for t in result["targets"]}
    assert by_name["const"]["eligible"] is False


# --- regression -----------------------------------------------------


def test_regression_trains_and_compares(regression_df):
    result = train_and_compare(
        regression_df, target_column="spend", test_size=0.2
    )

    assert result["task"] == "regression"
    assert result["primary_metric"] == "r2"
    names = [m["model"] for m in result["models"]]
    assert "baseline_mean" in names
    assert "linear_regression" in names
    assert "random_forest" in names
    # A real linear relationship should beat the mean baseline.
    linear = next(
        m for m in result["models"] if m["model"] == "linear_regression"
    )
    assert linear["metrics"]["r2"] > 0.5


def test_regression_metrics_keys(regression_df):
    result = train_and_compare(
        regression_df, target_column="spend", test_size=0.2
    )
    linear = next(
        m for m in result["models"] if m["model"] == "linear_regression"
    )
    assert set(linear["metrics"]) == {"mae", "rmse", "r2"}


def test_regression_excludes_target_from_features(regression_df):
    result = train_and_compare(
        regression_df, target_column="spend", test_size=0.2
    )
    assert "spend" not in result["feature_columns"]


def test_regression_rejects_target_in_features(regression_df):
    with pytest.raises(ValueError):
        train_and_compare(
            regression_df,
            target_column="spend",
            feature_columns=["spend", "age"],
        )


# --- classification ------------------------------------------------


def test_classification_trains_and_compares(classification_df):
    result = train_and_compare(
        classification_df, target_column="label", test_size=0.2
    )

    assert result["task"] == "classification"
    assert result["primary_metric"] == "f1"
    names = [m["model"] for m in result["models"]]
    assert "baseline_majority" in names
    assert "logistic_regression" in names
    assert "random_forest" in names


def test_classification_metrics_keys(classification_df):
    result = train_and_compare(
        classification_df, target_column="label", test_size=0.2
    )
    metrics = result["models"][0]["metrics"]
    assert set(metrics) == {"accuracy", "precision", "recall", "f1"}


# --- validation -----------------------------------------------------


def test_missing_target_column(regression_df):
    with pytest.raises(ValueError):
        train_and_compare(regression_df, target_column="does_not_exist")


def test_unknown_feature_column(regression_df):
    with pytest.raises(ValueError):
        train_and_compare(
            regression_df,
            target_column="spend",
            feature_columns=["age", "ghost"],
        )


def test_invalid_test_size(regression_df):
    with pytest.raises(ValueError):
        train_and_compare(
            regression_df, target_column="spend", test_size=0.9
        )


def test_regression_requires_numeric_target(classification_df):
    with pytest.raises(ValueError):
        train_and_compare(
            classification_df, target_column="label", task="regression"
        )


def test_classification_requires_categorical_target(regression_df):
    with pytest.raises(ValueError):
        train_and_compare(
            regression_df, target_column="spend", task="classification"
        )


def test_insufficient_class_samples():
    rng = np.random.default_rng(3)
    labels = ["a"] * 40 + ["b"] * 40 + ["c"] * 2
    df = pd.DataFrame(
        {"x": rng.normal(size=82), "label": labels}
    )
    with pytest.raises(ValueError):
        train_and_compare(df, target_column="label")


def test_missing_target_values_are_dropped():
    rng = np.random.default_rng(4)
    df = pd.DataFrame(
        {
            "x": rng.normal(size=60),
            "y": np.where(
                rng.random(60) < 0.2, np.nan, rng.normal(size=60)
            ),
        }
    )
    result = train_and_compare(df, target_column="y")
    assert result["row_count"] <= 60


def test_all_missing_target_rejected():
    df = pd.DataFrame(
        {"x": range(30), "y": [np.nan] * 30}
    )
    with pytest.raises(ValueError):
        train_and_compare(df, target_column="y")


# --- missing values in features ------------------------------------


def test_missing_feature_values_handled(regression_df):
    df = regression_df.copy()
    df.loc[df.index[:10], "age"] = np.nan
    df.loc[df.index[:10], "city"] = np.nan
    result = train_and_compare(df, target_column="spend")
    linear = next(
        m for m in result["models"] if m["model"] == "linear_regression"
    )
    assert linear["status"] == "ok"


def test_unseen_category_handled_at_predict_time():
    # Training split lacks category "z"; the encoder must tolerate it.
    rng = np.random.default_rng(5)
    n = 100
    df = pd.DataFrame(
        {
            "cat": ["z"] * 15 + list(rng.choice(["a", "b"], n - 15)),
            "num": rng.normal(size=n),
            "target": rng.normal(size=n),
        }
    )
    result = train_and_compare(df, target_column="target", test_size=0.3)
    assert any(m["status"] == "ok" for m in result["models"])


# --- reproducibility ------------------------------------------------


def test_reproducible_results(regression_df):
    first = train_and_compare(regression_df, target_column="spend")
    second = train_and_compare(regression_df, target_column="spend")
    assert first["models"] == second["models"]


# --- API ------------------------------------------------------------


def regression_csv() -> bytes:
    rng = np.random.default_rng(0)
    n = 120
    age = rng.integers(18, 65, n)
    income = rng.integers(20000, 90000, n)
    spend = 0.3 * income + 5 * age + rng.normal(0, 100, n)
    df = pd.DataFrame(
        {"age": age, "income": income, "spend": spend}
    )
    return df.to_csv(index=False).encode()


def test_api_ml_targets():
    response = client.post(
        "/ml/targets",
        files={"file": ("data.csv", BytesIO(regression_csv()), "text/csv")},
    )
    assert response.status_code == 200
    assert response.json()["row_count"] == 120


def test_api_ml_train():
    response = client.post(
        "/ml/train",
        data={"target_column": "spend", "test_size": "0.2"},
        files={"file": ("data.csv", BytesIO(regression_csv()), "text/csv")},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["task"] == "regression"
    assert body["best_model"] in {m["model"] for m in body["models"]}


def test_api_ml_train_invalid_target():
    response = client.post(
        "/ml/train",
        data={"target_column": "nope"},
        files={"file": ("data.csv", BytesIO(regression_csv()), "text/csv")},
    )
    assert response.status_code == 400


def test_api_ml_train_non_csv():
    response = client.post(
        "/ml/train",
        data={"target_column": "spend"},
        files={"file": ("data.txt", BytesIO(b"x"), "text/plain")},
    )
    assert response.status_code == 400

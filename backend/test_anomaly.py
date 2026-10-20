
import pandas as pd
import pytest

from services.anomaly import calculate_correlations, detect_outliers


def test_correlations_constant_column():
    df = pd.DataFrame({"a": [1, 1, 1], "b": [2, 3, 4]})

    result = calculate_correlations(df)

    assert result["correlations"][0]["correlation"] is None


def test_correlations_single_numeric_column():
    with pytest.raises(ValueError):
        calculate_correlations(pd.DataFrame({"a": [1, 2, 3]}))


def test_correlations_no_numeric_columns():
    df = pd.DataFrame({"a": ["x", "y"], "b": ["p", "q"]})

    with pytest.raises(ValueError):
        calculate_correlations(df)


def test_correlations_unsupported_method():
    df = pd.DataFrame({"a": [1, 2, 3], "b": [4, 5, 6]})

    with pytest.raises(ValueError):
        calculate_correlations(df, method="not-a-method")


def test_correlations_empty_dataset():
    with pytest.raises(ValueError):
        calculate_correlations(pd.DataFrame())


def test_outliers_missing_column():
    with pytest.raises(ValueError):
        detect_outliers(pd.DataFrame({"sales": [1, 2, 3]}), "profit")


def test_outliers_non_numeric_column():
    df = pd.DataFrame({"category": ["A", "B", "C"]})

    with pytest.raises(ValueError):
        detect_outliers(df, "category")


def test_outliers_all_missing_values():
    df = pd.DataFrame({"sales": [None, None]})

    with pytest.raises(ValueError):
        detect_outliers(df, "sales")


def test_outliers_no_outliers_found():
    df = pd.DataFrame({"sales": [10, 11, 12, 13, 14]})

    result = detect_outliers(df, "sales")

    assert result["outlier_count"] == 0
    assert result["outliers"] == []

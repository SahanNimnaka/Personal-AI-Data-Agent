
import pandas as pd
import pytest

from services.analysis import descriptive_statistics, group_by_column
from services.profiling import profile_dataset
from services.anomaly import calculate_correlations, detect_outliers


@pytest.fixture
def sample_df():
    return pd.DataFrame({
        "product": ["A", "B", "C", "D", "E"],
        "category": [
            "Electronics",
            "Furniture",
            "Electronics",
            "Furniture",
            "Electronics",
        ],
        "sales": [12, 18, 25, 15, 30],
        "price": [500, 1200, 300, 150, 750],
    })


def test_profile_dataset(sample_df):
    result = profile_dataset(sample_df)

    assert result["overview"]["rows"] == 5
    assert result["overview"]["columns"] == 4
    assert result["overview"]["total_missing_values"] == 0


def test_descriptive_statistics(sample_df):
    result = descriptive_statistics(sample_df, "sales")

    assert result["count"] == 5
    assert result["mean"] == pytest.approx(20.0)
    assert result["minimum"] == 12.0
    assert result["maximum"] == 30.0


def test_group_by_column(sample_df):
    result = group_by_column(sample_df, "category", "sales")

    groups = {item["category"]: item for item in result["groups"]}

    assert groups["Electronics"]["sum"] == 67
    assert groups["Furniture"]["sum"] == 33


def test_calculate_correlations(sample_df):
    result = calculate_correlations(sample_df)

    assert "sales" in result["numeric_columns"]
    assert "price" in result["numeric_columns"]
    assert len(result["correlations"]) == 1


def test_detect_outliers():
    df = pd.DataFrame({"sales": [10, 12, 13, 11, 14, 12, 100]})

    result = detect_outliers(df, "sales")

    assert result["outlier_count"] == 1
    assert result["outliers"][0]["value"] == 100.0


def test_invalid_descriptive_column(sample_df):
    with pytest.raises(ValueError):
        descriptive_statistics(sample_df, "profit")


def test_invalid_outlier_column(sample_df):
    with pytest.raises(ValueError):
        detect_outliers(sample_df, "profit")

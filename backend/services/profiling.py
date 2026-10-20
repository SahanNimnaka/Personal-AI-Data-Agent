
from typing import Any

import pandas as pd


def profile_dataset(df: pd.DataFrame) -> dict[str, Any]:
    """
    Generate a data-quality and statistical profile for a DataFrame.
    Does not modify the original DataFrame.
    """
    if not isinstance(df, pd.DataFrame):
        raise TypeError("Expected a pandas DataFrame.")

    if df.empty or len(df.columns) == 0:
        raise ValueError("The dataset must contain rows and columns.")

    columns = []

    for column in df.columns:
        series = df[column]
        missing_count = int(series.isna().sum())
        unique_count = int(series.nunique(dropna=True))

        if pd.api.types.is_numeric_dtype(series):
            column_type = "numeric"
        elif pd.api.types.is_datetime64_any_dtype(series):
            column_type = "datetime"
        else:
            column_type = "categorical"

        columns.append(
            {
                "name": str(column),
                "data_type": str(series.dtype),
                "column_type": column_type,
                "missing_values": missing_count,
                "missing_percentage": round(
                    missing_count / len(df) * 100, 2
                ),
                "unique_values": unique_count,
                "is_constant": unique_count <= 1,
            }
        )

    numeric_df = df.select_dtypes(include="number")
    numeric_statistics = {}

    for column in numeric_df.columns:
        series = numeric_df[column]
        numeric_statistics[str(column)] = {
            "mean": _safe_float(series.mean()),
            "median": _safe_float(series.median()),
            "standard_deviation": _safe_float(series.std()),
            "minimum": _safe_float(series.min()),
            "maximum": _safe_float(series.max()),
        }

    return {
        "overview": {
            "rows": int(len(df)),
            "columns": int(len(df.columns)),
            "duplicate_rows": int(df.duplicated().sum()),
            "total_missing_values": int(df.isna().sum().sum()),
            "memory_usage_bytes": int(
                df.memory_usage(index=True, deep=True).sum()
            ),
        },
        "columns": columns,
        "numeric_statistics": numeric_statistics,
    }


def _safe_float(value: Any) -> float | None:
    """Convert a numeric result to a JSON-safe float."""
    if pd.isna(value):
        return None

    return float(value)

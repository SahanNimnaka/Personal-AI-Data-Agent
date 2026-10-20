
from typing import Any

import pandas as pd

from services.json_utils import safe_float, to_json_safe


def descriptive_statistics(
    df: pd.DataFrame,
    column: str,
) -> dict[str, Any]:
    """Calculate descriptive statistics for a numeric column."""

    if column not in df.columns:
        raise ValueError(f"Column '{column}' does not exist.")

    if not pd.api.types.is_numeric_dtype(df[column]):
        raise ValueError(f"Column '{column}' must be numeric.")

    series = df[column].dropna()

    if series.empty:
        raise ValueError(
            f"Column '{column}' has no valid numeric values."
        )

    return {
        "column": column,
        "count": int(series.count()),
        "mean": safe_float(series.mean()),
        "median": safe_float(series.median()),
        "standard_deviation": (
            safe_float(series.std()) if len(series) > 1 else None
        ),
        "minimum": safe_float(series.min()),
        "maximum": safe_float(series.max()),
    }


def group_by_column(
    df: pd.DataFrame,
    group_column: str,
    value_column: str,
) -> dict[str, Any]:
    """Calculate count, sum, and mean for each group."""

    if group_column not in df.columns:
        raise ValueError(
            f"Group column '{group_column}' does not exist."
        )

    if value_column not in df.columns:
        raise ValueError(
            f"Value column '{value_column}' does not exist."
        )

    if not pd.api.types.is_numeric_dtype(df[value_column]):
        raise ValueError(
            f"Value column '{value_column}' must be numeric."
        )

    grouped = df.groupby(group_column, dropna=False)[value_column]

    result = grouped.agg(["count", "sum", "mean"]).reset_index()

    return {
        "group_column": group_column,
        "value_column": value_column,
        "groups": to_json_safe(
            result.fillna("").to_dict(orient="records")
        ),
    }

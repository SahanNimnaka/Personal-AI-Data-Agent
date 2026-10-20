
from typing import Any

import pandas as pd


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
        "mean": float(series.mean()),
        "median": float(series.median()),
        "standard_deviation": (
            float(series.std()) if len(series) > 1 else None
        ),
        "minimum": float(series.min()),
        "maximum": float(series.max()),
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
        "groups": result.fillna("").to_dict(orient="records"),
    }

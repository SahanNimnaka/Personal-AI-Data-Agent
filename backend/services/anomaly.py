
import pandas as pd


def calculate_correlations(
    df: pd.DataFrame,
    method: str = "pearson",
) -> dict:
    """
    Calculate correlations between numerical columns.

    Missing values are handled pairwise by pandas.
    Correlation does not establish causation.
    """
    if df.empty:
        raise ValueError("The dataset is empty.")

    if method not in {"pearson", "spearman", "kendall"}:
        raise ValueError(
            "Unsupported correlation method. "
            "Use pearson, spearman, or kendall."
        )

    numeric_df = df.select_dtypes(include="number")

    if numeric_df.shape[1] < 2:
        raise ValueError(
            "At least two numerical columns are required."
        )

    correlations = numeric_df.corr(
        method=method,
        min_periods=2,
    )

    results = []

    columns = list(correlations.columns)

    for i, column_a in enumerate(columns):
        for column_b in columns[i + 1:]:
            value = correlations.loc[column_a, column_b]

            results.append(
                {
                    "column_a": str(column_a),
                    "column_b": str(column_b),
                    "correlation": (
                        round(float(value), 4)
                        if pd.notna(value)
                        else None
                    ),
                }
            )

    return {
        "method": method,
        "numeric_columns": [str(c) for c in columns],
        "correlations": results,
        "interpretation_note": (
            "Correlation measures association, not causation. "
            "Small datasets may produce unreliable estimates."
        ),
    }


def detect_outliers(df: pd.DataFrame, column: str) -> dict:
    if df.empty:
        raise ValueError("The dataset is empty.")

    if column not in df.columns:
        raise ValueError(f"Column '{column}' does not exist.")

    series = df[column]

    # Check for an entirely missing column first.
    if series.isna().all():
        raise ValueError(f"Column '{column}' contains no usable values.")

    if not pd.api.types.is_numeric_dtype(series):
        raise ValueError(f"Column '{column}' must be numeric.")

    series = series.dropna()

    q1 = float(series.quantile(0.25))
    q3 = float(series.quantile(0.75))
    iqr = q3 - q1

    lower_bound = q1 - 1.5 * iqr
    upper_bound = q3 + 1.5 * iqr

    mask = (series < lower_bound) | (series > upper_bound)

    outliers = [
        {
            "row_index": int(index),
            "value": float(value),
        }
        for index, value in series[mask].items()
    ]

    return {
        "column": column,
        "method": "IQR",
        "q1": q1,
        "q3": q3,
        "iqr": float(iqr),
        "lower_bound": float(lower_bound),
        "upper_bound": float(upper_bound),
        "outlier_count": len(outliers),
        "outliers": outliers,
        "interpretation_note": (
            "Flagged values are potential outliers, not necessarily errors."
        ),
    }


from typing import Any

import pandas as pd
import plotly.express as px


def create_chart(
    df: pd.DataFrame,
    chart_type: str,
    x_column: str,
    y_column: str | None = None,
) -> dict[str, Any]:
    """Create a Plotly chart and return its JSON representation."""

    if df.empty:
        raise ValueError("Cannot create a chart from an empty dataset.")

    if x_column not in df.columns:
        raise ValueError(f"Column '{x_column}' does not exist.")

    if y_column is not None and y_column not in df.columns:
        raise ValueError(f"Column '{y_column}' does not exist.")

    if chart_type not in {"bar", "line", "scatter", "histogram", "box"}:
        raise ValueError("Unsupported chart type.")

    if chart_type == "histogram":
        fig = px.histogram(
            df,
            x=x_column,
            title=f"Distribution of {x_column}",
        )

    elif chart_type == "box":
        fig = px.box(
            df,
            x=x_column,
            y=y_column,
            title=f"Distribution of {y_column or x_column}",
        )

    else:
        if y_column is None:
            raise ValueError(
                f"Chart type '{chart_type}' requires a y_column."
            )

        if chart_type == "bar":
            fig = px.bar(
                df,
                x=x_column,
                y=y_column,
                title=f"{y_column} by {x_column}",
            )
        elif chart_type == "line":
            fig = px.line(
                df,
                x=x_column,
                y=y_column,
                title=f"{y_column} by {x_column}",
            )
        else:
            fig = px.scatter(
                df,
                x=x_column,
                y=y_column,
                title=f"{y_column} vs {x_column}",
            )

    return fig.to_dict()

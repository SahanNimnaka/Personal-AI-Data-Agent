
import base64
import json
from typing import Any

import numpy as np
import pandas as pd
import plotly.express as px
from plotly.utils import PlotlyJSONEncoder


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
        raise ValueError(
            "Unsupported chart type. "
            "Use bar, line, scatter, histogram, or box."
        )

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

    return _to_plain_json(fig.to_dict())


def _to_plain_json(obj: Any) -> Any:
    """
    Recursively convert a Plotly figure dict into plain JSON types.

    Plotly 6+ encodes numeric arrays as {"dtype", "bdata"} base64
    dicts, which are valid for plotly.js but unreadable for API
    consumers. Decode them back into regular lists.
    """
    if isinstance(obj, dict):
        if set(obj) == {"dtype", "bdata"}:
            array = np.frombuffer(
                base64.b64decode(obj["bdata"]),
                dtype=np.dtype(obj["dtype"]),
            )
            return array.tolist()

        return {
            key: _to_plain_json(value)
            for key, value in obj.items()
        }

    if isinstance(obj, (list, tuple)):
        return [_to_plain_json(item) for item in obj]

    if isinstance(obj, np.ndarray):
        return obj.tolist()

    if isinstance(obj, (np.integer,)):
        return int(obj)

    if isinstance(obj, (np.floating,)):
        return float(obj)

    if isinstance(obj, (np.bool_,)):
        return bool(obj)

    if isinstance(obj, (np.str_,)):
        return str(obj)

    if isinstance(obj, float) and json.dumps(obj) == "Infinity":
        return None

    return obj

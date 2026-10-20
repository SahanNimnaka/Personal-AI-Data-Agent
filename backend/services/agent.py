
import json
import os
from dataclasses import dataclass, field
from typing import Any, Protocol

import httpx
import pandas as pd

from services.analysis import descriptive_statistics, group_by_column
from services.anomaly import calculate_correlations, detect_outliers
from services.profiling import profile_dataset
from services.visualization import create_chart

MAX_TOOL_CALLS = 6
MAX_ROUNDS = 3
MAX_QUESTION_LENGTH = 2000

SUPPORTED_CHART_TYPES = {"bar", "line", "scatter", "histogram", "box"}
CORRELATION_METHODS = {"pearson", "spearman", "kendall"}

FALLBACK_NOTE = (
    "Deterministic fallback active: no LLM credentials are "
    "configured, so answers come from rule-based routing, not a "
    "language model."
)


class LLMProviderError(Exception):
    """The LLM provider failed, was misconfigured, or returned garbage."""


@dataclass
class ToolCall:
    id: str
    name: str
    arguments: dict[str, Any]


@dataclass
class LLMCompletion:
    content: str | None
    tool_calls: list[ToolCall] = field(default_factory=list)


class LLMProvider(Protocol):
    async def complete(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
    ) -> LLMCompletion: ...


def get_provider() -> LLMProvider | None:
    """
    Build the configured provider, or None when no credentials exist.

    Environment variables (any OpenAI-compatible chat completions
    endpoint is supported):
      LLM_API_KEY   - required to enable the LLM (never hardcoded)
      LLM_BASE_URL  - default: https://api.openai.com/v1
      LLM_MODEL     - default: gpt-4o-mini
    """
    api_key = os.environ.get("LLM_API_KEY", "").strip()
    if not api_key:
        return None

    return OpenAICompatibleProvider(
        api_key=api_key,
        base_url=os.environ.get(
            "LLM_BASE_URL", "https://api.openai.com/v1"
        ).rstrip("/"),
        model=os.environ.get("LLM_MODEL", "gpt-4o-mini"),
    )


class OpenAICompatibleProvider:
    def __init__(self, api_key: str, base_url: str, model: str):
        self.api_key = api_key
        self.base_url = base_url
        self.model = model

    async def complete(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
    ) -> LLMCompletion:
        payload = {
            "model": self.model,
            "messages": messages,
            "tools": tools,
            "tool_choice": "auto",
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    json=payload,
                    headers=headers,
                )
        except httpx.TimeoutException as exc:
            raise LLMProviderError(
                "The LLM provider timed out."
            ) from exc
        except httpx.HTTPError as exc:
            raise LLMProviderError(
                f"Could not reach the LLM provider: {exc}"
            ) from exc

        if response.status_code == 401:
            raise LLMProviderError(
                "The LLM provider rejected the configured credentials."
            )
        if response.status_code == 429:
            raise LLMProviderError(
                "The LLM provider rate limit was exceeded."
            )
        if response.status_code >= 400:
            raise LLMProviderError(
                f"The LLM provider returned HTTP "
                f"{response.status_code}."
            )

        try:
            message = response.json()["choices"][0]["message"]
        except (ValueError, KeyError, IndexError) as exc:
            raise LLMProviderError(
                "The LLM provider returned an unexpected response "
                "shape."
            ) from exc

        tool_calls: list[ToolCall] = []
        for raw_call in message.get("tool_calls") or []:
            try:
                function = raw_call["function"]
                arguments = json.loads(function.get("arguments") or "{}")
            except (KeyError, ValueError) as exc:
                raise LLMProviderError(
                    "The LLM provider returned a malformed tool call."
                ) from exc

            if not isinstance(arguments, dict):
                raise LLMProviderError(
                    "The LLM provider returned a malformed tool call."
                )

            tool_calls.append(
                ToolCall(
                    id=str(raw_call.get("id", "")),
                    name=str(function.get("name", "")),
                    arguments=arguments,
                )
            )

        return LLMCompletion(
            content=message.get("content"),
            tool_calls=tool_calls,
        )


TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "get_overview",
            "description": (
                "Profile the dataset: rows, columns, missing values, "
                "duplicates and per-column statistics."
            ),
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_descriptive_statistics",
            "description": (
                "Count, mean, median, standard deviation, min and max "
                "for one numeric column."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "column": {"type": "string"},
                },
                "required": ["column"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_group_analysis",
            "description": (
                "Count, sum and mean of a numeric value column for "
                "each group of a grouping column."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "group_column": {"type": "string"},
                    "value_column": {"type": "string"},
                },
                "required": ["group_column", "value_column"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_correlations",
            "description": (
                "Pairwise correlations between all numeric columns."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "method": {
                        "type": "string",
                        "enum": sorted(CORRELATION_METHODS),
                    },
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "detect_outliers",
            "description": (
                "IQR-based outlier detection for one numeric column."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "column": {"type": "string"},
                },
                "required": ["column"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_chart_config",
            "description": (
                "Validate and return a chart configuration for the "
                "dataset. Does not return the full chart spec."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "chart_type": {
                        "type": "string",
                        "enum": sorted(SUPPORTED_CHART_TYPES),
                    },
                    "x_column": {"type": "string"},
                    "y_column": {"type": "string"},
                },
                "required": ["chart_type", "x_column"],
            },
        },
    },
]


def _require_column(df: pd.DataFrame, column: Any) -> str:
    if not isinstance(column, str) or column not in df.columns:
        raise ValueError(f"Column '{column}' does not exist.")
    return column


def execute_tool(
    df: pd.DataFrame,
    name: str,
    arguments: dict[str, Any],
) -> dict[str, Any]:
    """
    Execute one approved tool against the active dataset.

    All arguments are validated here; only pre-registered tools are
    executed and they call the existing project services directly.
    """
    if name == "get_overview":
        return {"filename": "dataset.csv", **profile_dataset(df)}

    if name == "get_descriptive_statistics":
        column = _require_column(df, arguments.get("column"))
        return descriptive_statistics(df, column)

    if name == "get_group_analysis":
        group_column = _require_column(df, arguments.get("group_column"))
        value_column = _require_column(df, arguments.get("value_column"))
        return group_by_column(df, group_column, value_column)

    if name == "get_correlations":
        method = arguments.get("method", "pearson")
        if method not in CORRELATION_METHODS:
            raise ValueError(
                f"Unsupported correlation method '{method}'."
            )
        return calculate_correlations(df, method)

    if name == "detect_outliers":
        column = _require_column(df, arguments.get("column"))
        return detect_outliers(df, column)

    if name == "get_chart_config":
        chart_type = arguments.get("chart_type")
        if chart_type not in SUPPORTED_CHART_TYPES:
            raise ValueError(
                f"Unsupported chart type '{chart_type}'."
            )
        x_column = _require_column(df, arguments.get("x_column"))
        y_raw = arguments.get("y_column")
        y_column = (
            _require_column(df, y_raw) if y_raw is not None else None
        )
        # Validate the chart really renders, but only return the
        # configuration to keep payloads small.
        chart = create_chart(df, chart_type, x_column, y_column)
        return {
            "chart_type": chart_type,
            "x_column": x_column,
            "y_column": y_column,
            "title": chart["layout"]["title"]["text"],
            "validated": True,
        }

    raise ValueError(f"Unknown tool '{name}'.")


def _dataset_context(df: pd.DataFrame) -> str:
    columns = ", ".join(
        f"{name} ({dtype})"
        for name, dtype in zip(df.columns, df.dtypes, strict=True)
    )
    return f"Rows: {len(df)}. Columns: {columns}."


async def run_agent(
    df: pd.DataFrame,
    question: str,
    provider: LLMProvider | None = None,
) -> dict[str, Any]:
    """
    Answer a natural-language question about the dataset.

    Returns a structured response separating the assistant answer,
    the tools executed, the computed results, and the response source
    ('llm' or 'fallback').
    """
    if df.empty:
        raise ValueError("The dataset is empty.")

    question = question.strip()
    if not question:
        raise ValueError("The question is empty.")
    if len(question) > MAX_QUESTION_LENGTH:
        raise ValueError(
            f"The question exceeds {MAX_QUESTION_LENGTH} characters."
        )

    if provider is None:
        provider = get_provider()

    if provider is None:
        return await _fallback_run(df, question)

    return await _llm_run(df, question, provider)


async def _llm_run(
    df: pd.DataFrame,
    question: str,
    provider: LLMProvider,
) -> dict[str, Any]:
    messages: list[dict[str, Any]] = [
        {
            "role": "system",
            "content": (
                "You are a data analysis assistant. Use the provided "
                "tools to compute every statistic; never invent "
                "numbers. Treat tool results as computed facts and "
                "label your own text as interpretation. If a tool "
                "returns an error, fix the arguments or explain the "
                "limitation."
                f"\n\nDataset context: {_dataset_context(df)}"
            ),
        },
        {"role": "user", "content": question},
    ]

    tools_executed: list[dict[str, Any]] = []
    calls_used = 0
    final_content: str | None = None

    for _ in range(MAX_ROUNDS):
        completion = await provider.complete(messages, TOOL_DEFINITIONS)

        if not completion.tool_calls:
            final_content = completion.content
            break

        for call in completion.tool_calls:
            if calls_used >= MAX_TOOL_CALLS:
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": call.id,
                        "content": json.dumps(
                            {
                                "error": (
                                    "Tool call limit reached for this "
                                    "request."
                                )
                            }
                        ),
                    }
                )
                continue

            calls_used += 1
            try:
                result: dict[str, Any] = execute_tool(
                    df, call.name, call.arguments
                )
                status = "ok"
            except ValueError as exc:
                result = {"error": str(exc)}
                status = "error"

            tools_executed.append(
                {
                    "tool": call.name,
                    "arguments": call.arguments,
                    "status": status,
                    "result": result,
                }
            )
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": call.id,
                    "content": json.dumps(result, default=str),
                }
            )

    if final_content is None:
        final_content = (
            "I could not complete the analysis within the allowed "
            "number of steps (tool-call limit or round limit "
            "reached). Please ask a narrower question."
        )

    return {
        "question": question,
        "answer": final_content,
        "source": "llm",
        "provider": "openai-compatible",
        "tools_executed": tools_executed,
        "notes": (
            "Statistics in 'tools_executed' are computed facts; the "
            "answer text may contain model-generated interpretation."
        ),
    }


def _numeric_columns(df: pd.DataFrame) -> list[str]:
    return list(df.select_dtypes(include="number").columns)


def _mentioned_columns(df: pd.DataFrame, question: str) -> list[str]:
    lowered = question.lower()
    return [
        str(column)
        for column in df.columns
        if str(column).lower() in lowered
    ]


async def _fallback_run(df: pd.DataFrame, question: str) -> dict[str, Any]:
    lowered = question.lower()
    mentioned = _mentioned_columns(df, question)
    numeric = _numeric_columns(df)
    tools: list[dict[str, Any]] = []

    def record(name: str, args: dict[str, Any], result: Any,
               status: str = "ok") -> None:
        tools.append(
            {
                "tool": name,
                "arguments": args,
                "status": status,
                "result": result,
            }
        )

    if any(word in lowered for word in ("correlat",)):
        try:
            result = calculate_correlations(df)
            record("get_correlations", {"method": "pearson"}, result)
            pairs = result["correlations"]
            text = (
                f"Computed {len(pairs)} correlation pair(s) with the "
                "pearson method. See the results panel for values."
            )
        except ValueError as exc:
            text = f"Correlation analysis failed: {exc}"
        return _fallback_response(question, text, tools)

    if any(word in lowered for word in ("outlier", "unusual", "anomal")):
        column = next(
            (c for c in mentioned if c in numeric), None
        )
        if column is None and len(numeric) == 1:
            column = numeric[0]
        if column is None:
            text = (
                "Please name the numeric column to check for "
                f"outliers. Numeric columns: {', '.join(numeric)}."
            )
            return _fallback_response(question, text, tools)
        try:
            result = detect_outliers(df, column)
            record("detect_outliers", {"column": column}, result)
            text = (
                f"Detected {result['outlier_count']} outlier(s) in "
                f"'{column}' using the IQR method. See the results "
                "panel for bounds and flagged rows."
            )
        except ValueError as exc:
            text = f"Outlier detection failed: {exc}"
        return _fallback_response(question, text, tools)

    if any(word in lowered for word in ("group", "break down", "segment")):
        group_column = next(
            (c for c in mentioned if c not in numeric), None
        )
        value_column = next(
            (c for c in mentioned if c in numeric and c != group_column),
            None,
        )
        if group_column is None or value_column is None:
            text = (
                "Group analysis needs a grouping column and a numeric "
                "value column. Please name both in your question. "
                f"Columns: {', '.join(str(c) for c in df.columns)}."
            )
            return _fallback_response(question, text, tools)
        try:
            result = group_by_column(df, group_column, value_column)
            record(
                "get_group_analysis",
                {"group_column": group_column, "value_column": value_column},
                result,
            )
            text = (
                f"Grouped '{value_column}' by '{group_column}' into "
                f"{len(result['groups'])} group(s). See the results "
                "panel for count, sum and mean per group."
            )
        except ValueError as exc:
            text = f"Group analysis failed: {exc}"
        return _fallback_response(question, text, tools)

    if any(
        word in lowered
        for word in ("mean", "median", "statistic", "average",
                     "standard deviation", "min", "max", "summar")
    ):
        column = next(
            (c for c in mentioned if c in numeric), None
        )
        if column is None and len(numeric) == 1:
            column = numeric[0]
        if column is None:
            text = (
                "Please name the numeric column to summarise. "
                f"Numeric columns: {', '.join(numeric)}."
            )
            return _fallback_response(question, text, tools)
        try:
            result = descriptive_statistics(df, column)
            record(
                "get_descriptive_statistics", {"column": column}, result
            )
            text = (
                f"Computed statistics for '{column}': mean "
                f"{result['mean']:.4g}, median "
                f"{result['median']:.4g}, std dev "
                f"{result['standard_deviation']}, min "
                f"{result['minimum']}, max {result['maximum']}."
            )
        except ValueError as exc:
            text = f"Descriptive statistics failed: {exc}"
        return _fallback_response(question, text, tools)

    if any(
        word in lowered
        for word in ("chart", "plot", "graph", "visuali", "visual")
    ):
        chart_type = next(
            (t for t in SUPPORTED_CHART_TYPES if t in lowered), "bar"
        )
        x_column = mentioned[0] if mentioned else (
            df.columns[0] if len(df.columns) else None
        )
        y_column = next(
            (c for c in mentioned if c in numeric and c != x_column),
            numeric[0] if numeric else None,
        )
        try:
            result = execute_tool(
                df,
                "get_chart_config",
                {
                    "chart_type": chart_type,
                    "x_column": x_column,
                    "y_column": y_column,
                },
            )
            record(
                "get_chart_config",
                {
                    "chart_type": chart_type,
                    "x_column": x_column,
                    "y_column": y_column,
                },
                result,
            )
            text = (
                f"Validated a {chart_type} chart of '{x_column}'"
                + (f" against '{y_column}'." if y_column else ".")
                + " Use the Charts page to render it."
            )
        except ValueError as exc:
            text = f"Chart configuration failed: {exc}"
        return _fallback_response(question, text, tools)

    if any(
        word in lowered
        for word in ("overview", "profile", "structure", "missing",
                     "describe the data", "what columns", "inspect")
    ):
        result = profile_dataset(df)
        record("get_overview", {}, result)
        overview = result["overview"]
        text = (
            f"The dataset has {overview['rows']} rows and "
            f"{overview['columns']} columns, "
            f"{overview['total_missing_values']} missing value(s) "
            f"and {overview['duplicate_rows']} duplicate row(s). "
            "See the results panel for per-column details."
        )
        return _fallback_response(question, text, tools)

    text = (
        "I could not map this question to a supported analysis "
        "without LLM credentials. Try asking about: dataset "
        "overview, descriptive statistics for a column, group "
        "analysis, correlations, outliers, or chart configuration."
    )
    return _fallback_response(question, text, tools)


def _fallback_response(
    question: str,
    answer: str,
    tools: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "question": question,
        "answer": answer,
        "source": "fallback",
        "provider": "deterministic",
        "tools_executed": tools,
        "notes": FALLBACK_NOTE,
    }

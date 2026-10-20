
import asyncio
from io import BytesIO

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from main import app
from services.agent import (
    LLMCompletion,
    LLMProviderError,
    ToolCall,
    execute_tool,
    run_agent,
)


def run(coro):
    return asyncio.run(coro)


client = TestClient(app)

SAMPLE_CSV = (
    b"product,category,sales,price\n"
    b"Laptop,Electronics,15,1200\n"
    b"Phone,Electronics,30,800\n"
    b"Desk,Furniture,12,250\n"
    b"Chair,Furniture,25,150\n"
    b"Tablet,Electronics,18,500\n"
)


@pytest.fixture
def sample_df():
    return pd.DataFrame(
        {
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
        }
    )


class ScriptedProvider:
    """A fake provider returning pre-scripted completions in order."""

    def __init__(self, completions):
        self.completions = list(completions)
        self.calls = 0
        self.captured_messages = []

    async def complete(self, messages, tools):
        self.captured_messages.append(list(messages))
        index = min(self.calls, len(self.completions) - 1)
        self.calls += 1
        return self.completions[index]


class ExplodingProvider:
    async def complete(self, messages, tools):
        raise LLMProviderError("Provider exploded.")


# --- Tool execution -------------------------------------------------


def test_execute_tool_descriptive(sample_df):
    result = execute_tool(
        sample_df, "get_descriptive_statistics", {"column": "sales"}
    )
    assert result["mean"] == pytest.approx(20.0)


def test_execute_tool_overview(sample_df):
    result = execute_tool(sample_df, "get_overview", {})
    assert result["overview"]["rows"] == 5


def test_execute_tool_group(sample_df):
    result = execute_tool(
        sample_df,
        "get_group_analysis",
        {"group_column": "category", "value_column": "sales"},
    )
    assert len(result["groups"]) == 2


def test_execute_tool_correlations(sample_df):
    result = execute_tool(sample_df, "get_correlations", {})
    assert "sales" in result["numeric_columns"]


def test_execute_tool_outliers():
    df = pd.DataFrame({"sales": [10, 12, 13, 11, 14, 12, 100]})
    result = execute_tool(df, "detect_outliers", {"column": "sales"})
    assert result["outlier_count"] == 1


def test_execute_tool_chart_config(sample_df):
    result = execute_tool(
        sample_df,
        "get_chart_config",
        {"chart_type": "bar", "x_column": "product", "y_column": "sales"},
    )
    assert result["validated"] is True
    assert result["title"] == "sales by product"


def test_execute_tool_invalid_column(sample_df):
    with pytest.raises(ValueError):
        execute_tool(
            sample_df, "get_descriptive_statistics", {"column": "profit"}
        )


def test_execute_tool_invalid_chart_type(sample_df):
    with pytest.raises(ValueError):
        execute_tool(
            sample_df,
            "get_chart_config",
            {"chart_type": "pie", "x_column": "product"},
        )


def test_execute_tool_invalid_method(sample_df):
    with pytest.raises(ValueError):
        execute_tool(
            sample_df, "get_correlations", {"method": "not-a-method"}
        )


def test_execute_tool_unknown_tool(sample_df):
    with pytest.raises(ValueError):
        execute_tool(sample_df, "drop_table", {})


# --- LLM run --------------------------------------------------------


def test_llm_run_executes_tool_and_answers(sample_df):
    provider = ScriptedProvider(
        [
            LLMCompletion(
                content=None,
                tool_calls=[
                    ToolCall(
                        id="1",
                        name="get_descriptive_statistics",
                        arguments={"column": "sales"},
                    )
                ],
            ),
            LLMCompletion(content="The mean sales is 20."),
        ]
    )

    result = run(
        run_agent(sample_df, "What is the mean sales?", provider=provider)
    )

    assert result["source"] == "llm"
    assert result["answer"] == "The mean sales is 20."
    assert len(result["tools_executed"]) == 1
    assert result["tools_executed"][0]["status"] == "ok"


def test_llm_run_invalid_tool_argument(sample_df):
    provider = ScriptedProvider(
        [
            LLMCompletion(
                content=None,
                tool_calls=[
                    ToolCall(
                        id="1",
                        name="get_descriptive_statistics",
                        arguments={"column": "profit"},
                    )
                ],
            ),
            LLMCompletion(content="That column does not exist."),
        ]
    )

    result = run(run_agent(sample_df, "Mean profit?", provider=provider))

    assert result["tools_executed"][0]["status"] == "error"


def test_llm_run_provider_error_propagates(sample_df):
    with pytest.raises(LLMProviderError):
        run(run_agent(sample_df, "Anything", provider=ExplodingProvider()))


def test_llm_run_enforces_tool_call_limit(sample_df):
    # Every completion requests another tool call, forever.
    looping = LLMCompletion(
        content=None,
        tool_calls=[
            ToolCall(
                id="x",
                name="get_overview",
                arguments={},
            )
        ],
    )
    provider = ScriptedProvider([looping])

    result = run(run_agent(sample_df, "loop", provider=provider))

    assert len(result["tools_executed"]) <= 6
    assert result["source"] == "llm"


# --- Deterministic fallback ----------------------------------------


def test_fallback_statistics(sample_df):
    result = run(
        run_agent(
            sample_df, "What is the mean of the sales column?", provider=None
        )
    )
    assert result["source"] == "fallback"
    assert result["tools_executed"][0]["tool"] == (
        "get_descriptive_statistics"
    )
    assert "20" in result["answer"]


def test_fallback_overview(sample_df):
    result = run(run_agent(sample_df, "Give me an overview", provider=None))
    assert result["source"] == "fallback"
    assert result["tools_executed"][0]["tool"] == "get_overview"


def test_fallback_correlations(sample_df):
    result = run(
        run_agent(sample_df, "Show correlations", provider=None)
    )
    assert result["tools_executed"][0]["tool"] == "get_correlations"


def test_fallback_outliers_missing_column(sample_df):
    result = run(run_agent(sample_df, "Any outliers?", provider=None))
    # Two+ numeric columns and none named -> asks for clarification.
    assert result["tools_executed"] == []
    assert "column" in result["answer"].lower()


def test_fallback_group_missing_columns(sample_df):
    result = run(run_agent(sample_df, "Group the data", provider=None))
    assert result["tools_executed"] == []
    assert "group" in result["answer"].lower()


def test_fallback_unmapped_question(sample_df):
    result = run(run_agent(sample_df, "Hello there", provider=None))
    assert result["source"] == "fallback"
    assert result["tools_executed"] == []


# --- run_agent validation ------------------------------------------


def test_run_agent_empty_question(sample_df):
    with pytest.raises(ValueError):
        run(run_agent(sample_df, "   ", provider=None))


def test_run_agent_too_long_question(sample_df):
    with pytest.raises(ValueError):
        run(run_agent(sample_df, "x" * 3000, provider=None))


# --- API endpoint --------------------------------------------------


def test_agent_chat_fallback(monkeypatch):
    monkeypatch.delenv("LLM_API_KEY", raising=False)

    response = client.post(
        "/agent/chat",
        data={"question": "Give me an overview"},
        files={"file": ("sample.csv", BytesIO(SAMPLE_CSV), "text/csv")},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["source"] == "fallback"
    assert body["tools_executed"][0]["tool"] == "get_overview"


def test_agent_chat_empty_question():
    response = client.post(
        "/agent/chat",
        data={"question": "   "},
        files={"file": ("sample.csv", BytesIO(SAMPLE_CSV), "text/csv")},
    )
    assert response.status_code == 400


def test_agent_chat_rejects_non_csv():
    response = client.post(
        "/agent/chat",
        data={"question": "hello"},
        files={"file": ("data.txt", BytesIO(b"x"), "text/plain")},
    )
    assert response.status_code == 400


def test_agent_chat_provider_error(monkeypatch):
    async def failing_agent(df, question):
        raise LLMProviderError("Provider down.")

    monkeypatch.setattr("main.run_agent", failing_agent)

    response = client.post(
        "/agent/chat",
        data={"question": "hello"},
        files={"file": ("sample.csv", BytesIO(SAMPLE_CSV), "text/csv")},
    )
    assert response.status_code == 502


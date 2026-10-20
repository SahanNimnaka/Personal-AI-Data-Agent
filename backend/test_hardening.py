
"""
Regression tests for the security/reliability hardening pass.

These cover concrete issues found during review:
- Extreme (but finite) numeric inputs used to raise HTTP 500 in
  descriptive statistics, profiling and outlier detection.
- Non-finite floats (NaN/Infinity) could leak into JSON responses.
- The column-count limit and generic 500 behaviour.
"""

import io
import json
import math

from fastapi.testclient import TestClient

from main import MAX_COLUMNS, app

client = TestClient(app, raise_server_exceptions=False)

# Finite floats whose intermediate maths (e.g. std dev, IQR) can
# overflow to +-inf.
EXTREME_CSV = b"x\n1e308\n-1e308\n1e308\n"


def _files(content: bytes, name: str = "extreme.csv"):
    return {"file": (name, io.BytesIO(content), "text/csv")}


def _assert_finite_json(response):
    """Parse a response and assert no non-finite tokens appear."""
    text = response.text
    assert "NaN" not in text
    assert "Infinity" not in text
    # json.loads accepts NaN/Infinity by default, so guard explicitly.
    json.loads(text, parse_constant=_reject_constant)


def _reject_constant(value):  # pragma: no cover - only on failure
    raise AssertionError(f"Non-finite JSON constant found: {value}")


def test_descriptive_extreme_values_no_500():
    response = client.post(
        "/analysis/descriptive",
        params={"column": "x"},
        files=_files(EXTREME_CSV),
    )
    assert response.status_code == 200
    _assert_finite_json(response)


def test_profile_extreme_values_no_500():
    response = client.post(
        "/datasets/profile", files=_files(EXTREME_CSV)
    )
    assert response.status_code == 200
    _assert_finite_json(response)


def test_outliers_extreme_values_no_500():
    response = client.post(
        "/analysis/outliers",
        data={"column": "x"},
        files=_files(EXTREME_CSV),
    )
    assert response.status_code == 200
    _assert_finite_json(response)


def test_group_extreme_values_finite_json():
    csv = b"g,x\na,1e308\na,-1e308\n"
    response = client.post(
        "/analysis/group",
        params={"group_column": "g", "value_column": "x"},
        files=_files(csv),
    )
    assert response.status_code == 200
    _assert_finite_json(response)


def test_correlations_extreme_values_finite_json():
    csv = b"a,b\n1e308,1\n-1e308,2\n1e308,3\n"
    response = client.post(
        "/analysis/correlations", files=_files(csv)
    )
    assert response.status_code == 200
    _assert_finite_json(response)


def test_too_many_columns_rejected():
    columns = ",".join(f"c{i}" for i in range(MAX_COLUMNS + 1))
    row = ",".join("1" for _ in range(MAX_COLUMNS + 1))
    csv = (columns + "\n" + row + "\n").encode()

    response = client.post("/datasets/upload", files=_files(csv, "wide.csv"))
    assert response.status_code == 400
    assert "columns" in response.json()["detail"].lower()


def test_wide_within_limit_accepted():
    columns = ",".join(f"c{i}" for i in range(MAX_COLUMNS))
    row = ",".join("1" for _ in range(MAX_COLUMNS))
    csv = (columns + "\n" + row + "\n").encode()

    response = client.post("/datasets/upload", files=_files(csv, "ok.csv"))
    assert response.status_code == 200
    assert response.json()["columns_count"] == MAX_COLUMNS


def test_unhandled_error_body_is_generic(monkeypatch):
    """
    Force an unexpected error inside an endpoint and confirm the client
    receives a generic message with no traceback or paths.
    """
    import main
    from services import profiling

    def boom(_df):
        raise RuntimeError("secret internal detail: C:\\secret\\path")

    monkeypatch.setattr(profiling, "profile_dataset", boom)
    monkeypatch.setattr(main, "profile_dataset", boom, raising=False)

    response = client.post(
        "/datasets/profile", files=_files(b"x\n1\n")
    )
    assert response.status_code == 500
    body = response.json()
    assert body["detail"] == "An unexpected server error occurred."
    text = response.text
    assert "secret internal detail" not in text
    assert "Traceback" not in text
    assert "C:\\secret\\path" not in text


def test_json_safe_conversion():
    from services.json_utils import safe_float, to_json_safe

    assert safe_float(float("inf")) is None
    assert safe_float(float("nan")) is None
    assert safe_float(1.5) == 1.5

    converted = to_json_safe(
        {"a": float("inf"), "b": float("nan"), "c": 3.0}
    )
    assert converted["a"] is None
    assert converted["b"] is None
    assert converted["c"] == 3.0
    assert math.isfinite(converted["c"])

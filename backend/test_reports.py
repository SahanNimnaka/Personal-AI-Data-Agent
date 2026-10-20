
import json

import pytest
from fastapi.testclient import TestClient

from main import app
from services.reports import ReportError, build_report

client = TestClient(app)


def sample_payload() -> dict:
    return {
        "filename": "sample_sales.csv",
        "rows": 5,
        "columns": 4,
        "sections": [
            {
                "type": "profile",
                "data": {
                    "overview": {
                        "rows": 5,
                        "columns": 4,
                        "duplicate_rows": 0,
                        "total_missing_values": 0,
                    }
                },
            },
            {
                "type": "descriptive",
                "data": {
                    "column": "sales",
                    "mean": 20.0,
                    "median": 18.0,
                    "minimum": 12.0,
                    "maximum": 30.0,
                },
            },
            {
                "type": "outliers",
                "data": {
                    "column": "sales",
                    "outlier_count": 0,
                    "outliers": [],
                },
            },
        ],
    }


# --- build_report ---------------------------------------------------


def test_build_json_report():
    content, media_type, filename = build_report(
        sample_payload(), "json"
    )
    assert media_type == "application/json"
    assert filename == "sample_sales-report.json"

    parsed = json.loads(content)
    assert parsed["filename"] == "sample_sales.csv"
    assert "generated_at" in parsed
    assert len(parsed["sections"]) == 3


def test_build_csv_report():
    content, media_type, filename = build_report(
        sample_payload(), "csv"
    )
    assert media_type == "text/csv"
    assert filename == "sample_sales-report.csv"
    text = content.decode("utf-8")
    assert "Personal AI Data Agent report" in text
    assert "sales" in text
    assert "Interpretation notes" in text


def test_build_html_report():
    content, media_type, filename = build_report(
        sample_payload(), "html"
    )
    assert media_type == "text/html"
    assert filename == "sample_sales-report.html"
    text = content.decode("utf-8")
    assert "<!doctype html>" in text
    assert "Dataset profile" in text


def test_unsupported_format():
    with pytest.raises(ReportError):
        build_report(sample_payload(), "pdf")


def test_empty_sections_allowed():
    payload = {
        "filename": "empty.csv",
        "sections": [],
    }
    content, _, _ = build_report(payload, "html")
    assert "No analysis sections" in content.decode("utf-8")


def test_missing_filename_rejected():
    with pytest.raises(ReportError):
        build_report({"sections": []}, "json")


def test_unknown_section_type_rejected():
    payload = {
        "filename": "x.csv",
        "sections": [{"type": "malware", "data": {}}],
    }
    with pytest.raises(ReportError):
        build_report(payload, "json")


def test_non_object_payload_rejected():
    with pytest.raises(ReportError):
        build_report(["not", "a", "dict"], "json")


def test_too_many_sections_rejected():
    payload = {
        "filename": "x.csv",
        "sections": [
            {"type": "profile", "data": {}} for _ in range(20)
        ],
    }
    with pytest.raises(ReportError):
        build_report(payload, "json")


# --- HTML escaping --------------------------------------------------


def test_html_escaping_of_user_text():
    payload = {
        "filename": "<script>alert('xss')</script>.csv",
        "sections": [
            {
                "type": "descriptive",
                "data": {"column": "<img src=x onerror=alert(1)>"},
            }
        ],
    }
    content, _, _ = build_report(payload, "html")
    text = content.decode("utf-8")
    assert "<script>alert" not in text
    assert "&lt;script&gt;" in text
    assert "<img src=x" not in text


def test_csv_not_executed_as_code():
    payload = {
        "filename": "x.csv",
        "sections": [
            {"type": "descriptive", "data": {"note": "=1+1"}}
        ],
    }
    content, _, _ = build_report(payload, "csv")
    # Value is written verbatim as data, never evaluated.
    assert b"=1+1" in content


# --- API ------------------------------------------------------------


def test_api_json_report_headers():
    response = client.post(
        "/reports/generate?format=json",
        json=sample_payload(),
    )
    assert response.status_code == 200
    assert response.headers["content-type"].startswith(
        "application/json"
    )
    assert (
        'filename="sample_sales-report.json"'
        in response.headers["content-disposition"]
    )


def test_api_html_report_headers():
    response = client.post(
        "/reports/generate?format=html",
        json=sample_payload(),
    )
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert "attachment" in response.headers["content-disposition"]


def test_api_csv_report_headers():
    response = client.post(
        "/reports/generate?format=csv",
        json=sample_payload(),
    )
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")


def test_api_unsupported_format_returns_400():
    response = client.post(
        "/reports/generate?format=pdf",
        json=sample_payload(),
    )
    assert response.status_code == 400


def test_api_invalid_payload_returns_400():
    response = client.post(
        "/reports/generate?format=json",
        json={"sections": []},
    )
    assert response.status_code == 400


def test_api_oversized_payload_returns_400():
    payload = {
        "filename": "big.csv",
        "sections": [
            {
                "type": "profile",
                "data": {"blob": "x" * (3 * 1024 * 1024)},
            }
        ],
    }
    response = client.post(
        "/reports/generate?format=json",
        json=payload,
    )
    assert response.status_code == 400

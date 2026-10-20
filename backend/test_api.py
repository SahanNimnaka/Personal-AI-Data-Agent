
from io import BytesIO
from pathlib import Path

from fastapi.testclient import TestClient

from main import app

client = TestClient(app)

SAMPLE_CSV_PATH = Path(__file__).parent / "sample_sales.csv"


def _csv_files(content: bytes, filename: str = "test.csv"):
    return {"file": (filename, BytesIO(content), "text/csv")}


def test_root_endpoint():
    response = client.get("/")

    assert response.status_code == 200
    assert response.json()["status"] == "success"


def test_health_endpoint():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_upload_csv():
    csv_content = b"product,sales\nA,10\nB,20\n"

    response = client.post(
        "/datasets/upload",
        files={
            "file": (
                "test.csv",
                BytesIO(csv_content),
                "text/csv",
            )
        },
    )

    assert response.status_code == 200
    assert response.json()["rows"] == 2
    assert response.json()["columns_count"] == 2


def test_reject_non_csv_upload():
    response = client.post(
        "/datasets/upload",
        files={
            "file": (
                "test.txt",
                BytesIO(b"some text"),
                "text/plain",
            )
        },
    )

    assert response.status_code == 400


def test_api_descriptive_statistics():
    csv_content = b"sales\n10\n20\n30\n"

    response = client.post(
        "/analysis/descriptive",
        params={"column": "sales"},
        files={
            "file": (
                "test.csv",
                BytesIO(csv_content),
                "text/csv",
            )
        },
    )

    assert response.status_code == 200
    assert response.json()["mean"] == 20.0


def test_api_outlier_detection():
    csv_content = b"sales\n10\n12\n13\n11\n14\n12\n100\n"

    response = client.post(
        "/analysis/outliers",
        data={"column": "sales"},
        files={
            "file": (
                "outliers.csv",
                BytesIO(csv_content),
                "text/csv",
            )
        },
    )

    assert response.status_code == 200
    assert response.json()["outlier_count"] == 1


def test_api_profile_dataset():
    csv_content = b"product,sales\nA,10\nB,20\n"

    response = client.post(
        "/datasets/profile",
        files=_csv_files(csv_content),
    )

    assert response.status_code == 200
    assert response.json()["overview"]["rows"] == 2
    assert response.json()["overview"]["columns"] == 2


def test_api_group_analysis():
    csv_content = b"category,sales\nA,10\nB,20\nA,5\n"

    response = client.post(
        "/analysis/group",
        params={"group_column": "category", "value_column": "sales"},
        files=_csv_files(csv_content),
    )

    assert response.status_code == 200
    groups = {
        item["category"]: item
        for item in response.json()["groups"]
    }
    assert groups["A"]["sum"] == 15
    assert groups["B"]["sum"] == 20


def test_api_group_analysis_missing_column():
    csv_content = b"category,sales\nA,10\nB,20\n"

    response = client.post(
        "/analysis/group",
        params={"group_column": "category", "value_column": "profit"},
        files=_csv_files(csv_content),
    )

    assert response.status_code == 400


def test_api_correlations():
    csv_content = b"a,b\n1,2\n3,4\n5,7\n"

    response = client.post(
        "/analysis/correlations",
        params={"method": "pearson"},
        files=_csv_files(csv_content),
    )

    assert response.status_code == 200
    assert response.json()["method"] == "pearson"
    assert len(response.json()["correlations"]) == 1


def test_api_correlations_invalid_method():
    csv_content = b"a,b\n1,2\n3,4\n"

    response = client.post(
        "/analysis/correlations",
        params={"method": "not-a-method"},
        files=_csv_files(csv_content),
    )

    assert response.status_code == 400


def test_api_correlations_too_few_numeric_columns():
    csv_content = b"name\nAlice\nBob\n"

    response = client.post(
        "/analysis/correlations",
        files=_csv_files(csv_content),
    )

    assert response.status_code == 400


def test_api_chart_bar_with_sample_sales():
    csv_content = SAMPLE_CSV_PATH.read_bytes()

    response = client.post(
        "/visualizations/chart",
        params={
            "chart_type": "bar",
            "x_column": "product",
            "y_column": "sales",
        },
        files=_csv_files(csv_content, "sample_sales.csv"),
    )

    assert response.status_code == 200

    body = response.json()
    assert body["chart_type"] == "bar"
    assert len(body["chart"]["data"]) == 1
    assert body["chart"]["data"][0]["type"] == "bar"
    assert body["chart"]["layout"]["title"]["text"] == "sales by product"

    trace = body["chart"]["data"][0]
    assert list(trace["x"]) == ["Laptop", "Phone", "Desk", "Chair", "Tablet"]
    assert list(trace["y"]) == [15, 30, 12, 25, 18]


def test_api_chart_histogram_without_y_column():
    csv_content = b"sales\n10\n20\n30\n20\n"

    response = client.post(
        "/visualizations/chart",
        params={"chart_type": "histogram", "x_column": "sales"},
        files=_csv_files(csv_content),
    )

    assert response.status_code == 200
    assert response.json()["chart"]["data"][0]["type"] == "histogram"


def test_api_chart_invalid_chart_type():
    csv_content = b"product,sales\nA,10\nB,20\n"

    response = client.post(
        "/visualizations/chart",
        params={
            "chart_type": "pie",
            "x_column": "product",
            "y_column": "sales",
        },
        files=_csv_files(csv_content),
    )

    assert response.status_code == 400


def test_api_chart_missing_column():
    csv_content = b"product,sales\nA,10\nB,20\n"

    response = client.post(
        "/visualizations/chart",
        params={
            "chart_type": "bar",
            "x_column": "profit",
            "y_column": "sales",
        },
        files=_csv_files(csv_content),
    )

    assert response.status_code == 400


def test_api_chart_missing_y_column_for_bar():
    csv_content = b"product,sales\nA,10\nB,20\n"

    response = client.post(
        "/visualizations/chart",
        params={"chart_type": "bar", "x_column": "product"},
        files=_csv_files(csv_content),
    )

    assert response.status_code == 400


def test_api_empty_file_rejected():
    response = client.post(
        "/datasets/upload",
        files=_csv_files(b""),
    )

    assert response.status_code == 400


def test_api_malformed_csv_rejected():
    response = client.post(
        "/datasets/upload",
        files=_csv_files(b"\xff\xfe\x00\x01not a csv"),
    )

    assert response.status_code == 400


def test_api_header_only_csv_rejected():
    response = client.post(
        "/datasets/upload",
        files=_csv_files(b"product,sales\n"),
    )

    assert response.status_code == 400


def test_api_oversized_file_rejected():
    oversized = b"x" * (10 * 1024 * 1024 + 1)

    response = client.post(
        "/datasets/upload",
        files=_csv_files(oversized, "big.csv"),
    )

    assert response.status_code == 413

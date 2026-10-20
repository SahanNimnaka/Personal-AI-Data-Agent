
import csv
import html
import io
import json
from datetime import datetime, timezone
from typing import Any

SUPPORTED_FORMATS = {"json", "csv", "html"}

MAX_SECTIONS = 12
MAX_JSON_BYTES = 2 * 1024 * 1024

SECTION_TITLES = {
    "profile": "Dataset profile",
    "descriptive": "Descriptive statistics",
    "group": "Group analysis",
    "correlations": "Correlations",
    "outliers": "Outlier detection",
    "ml": "Machine learning evaluation",
}


class ReportError(Exception):
    """A report could not be generated from the supplied data."""


def _coerce_sections(raw: Any) -> list[dict[str, Any]]:
    if raw is None:
        return []
    if not isinstance(raw, list):
        raise ReportError("sections must be a list.")
    if len(raw) > MAX_SECTIONS:
        raise ReportError(
            f"At most {MAX_SECTIONS} sections are allowed."
        )

    sections: list[dict[str, Any]] = []
    for item in raw:
        if not isinstance(item, dict):
            raise ReportError("Each section must be an object.")
        key = item.get("type")
        data = item.get("data")
        if not isinstance(key, str) or key not in SECTION_TITLES:
            raise ReportError(
                f"Unknown section type '{key}'. Supported: "
                + ", ".join(sorted(SECTION_TITLES))
            )
        if not isinstance(data, dict):
            raise ReportError(
                f"Section '{key}' must include an object 'data'."
            )
        sections.append({"type": key, "data": data})

    return sections


def _validate_payload(raw: Any) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise ReportError("The report payload must be an object.")

    filename = raw.get("filename")
    if not isinstance(filename, str) or not filename.strip():
        raise ReportError("A dataset filename is required.")

    try:
        encoded = json.dumps(raw)
    except (TypeError, ValueError) as exc:
        raise ReportError(
            "The report payload could not be serialized."
        ) from exc

    if len(encoded.encode("utf-8")) > MAX_JSON_BYTES:
        raise ReportError("The report payload is too large.")

    sections = _coerce_sections(raw.get("sections"))

    return {
        "filename": filename.strip(),
        "rows": raw.get("rows"),
        "columns": raw.get("columns"),
        "sections": sections,
    }


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def build_report(payload: Any, fmt: str) -> tuple[bytes, str, str]:
    """
    Build a report in the requested format.

    Returns (content_bytes, media_type, filename).
    """
    fmt = (fmt or "").lower()
    if fmt not in SUPPORTED_FORMATS:
        raise ReportError(
            "Unsupported format. Use json, csv, or html."
        )

    report = _validate_payload(payload)
    report["generated_at"] = _now_iso()

    stem = report["filename"].rsplit(".", 1)[0] or "report"

    if fmt == "json":
        content = json.dumps(
            report, indent=2, default=str
        ).encode("utf-8")
        return content, "application/json", f"{stem}-report.json"

    if fmt == "csv":
        content = _to_csv(report).encode("utf-8")
        return content, "text/csv", f"{stem}-report.csv"

    content = _to_html(report).encode("utf-8")
    return content, "text/html", f"{stem}-report.html"


def _to_csv(report: dict[str, Any]) -> str:
    buffer = io.StringIO()
    writer = csv.writer(buffer)

    writer.writerow(["Personal AI Data Agent report"])
    writer.writerow(["Generated at", report["generated_at"]])
    writer.writerow(["Dataset", report["filename"]])
    writer.writerow(["Rows", report.get("rows", "")])
    writer.writerow(["Columns", report.get("columns", "")])
    writer.writerow([])

    for section in report["sections"]:
        title = SECTION_TITLES[section["type"]]
        writer.writerow([title])
        for key, value in _flatten(section["data"]):
            writer.writerow([key, value])
        writer.writerow([])

    writer.writerow(["Interpretation notes"])
    writer.writerow(
        [
            "Value",
            "Correlation is not causation; flagged outliers are "
            "candidates, not errors; ML metrics are from held-out "
            "test data.",
        ]
    )

    return buffer.getvalue()


def _flatten(data: dict[str, Any], prefix: str = "") -> list[tuple[str, Any]]:
    rows: list[tuple[str, Any]] = []
    for key, value in data.items():
        label = f"{prefix}{key}"
        if isinstance(value, dict):
            rows.extend(_flatten(value, prefix=f"{label}."))
        elif isinstance(value, list):
            if not value:
                rows.append((label, ""))
            elif all(isinstance(item, dict) for item in value):
                for index, item in enumerate(value):
                    rows.extend(
                        _flatten(item, prefix=f"{label}[{index}].")
                    )
            else:
                rows.append((label, ", ".join(str(v) for v in value)))
        else:
            rows.append((label, value))
    return rows


def _esc(value: Any) -> str:
    return html.escape(str(value))


def _to_html(report: dict[str, Any]) -> str:
    parts: list[str] = [
        "<!doctype html>",
        '<html lang="en"><head><meta charset="utf-8">',
        "<title>Personal AI Data Agent report</title>",
        "<style>",
        "body{font-family:system-ui,Arial,sans-serif;margin:2rem;"
        "color:#1e293b;line-height:1.5}",
        "h1{border-bottom:2px solid #2563eb;padding-bottom:.5rem}",
        "h2{margin-top:2rem;color:#1d4ed8}",
        "table{border-collapse:collapse;width:100%;margin-top:.5rem}",
        "th,td{border:1px solid #cbd5e1;padding:.4rem .6rem;"
        "text-align:left;font-size:.9rem}",
        "th{background:#f1f5f9}",
        ".note{background:#fef9c3;border-left:4px solid #eab308;"
        "padding:.75rem 1rem;margin-top:1.5rem;font-size:.9rem}",
        "footer{margin-top:2rem;color:#64748b;font-size:.8rem}",
        "</style></head><body>",
        "<h1>Personal AI Data Agent report</h1>",
        "<table>",
        f"<tr><th>Dataset</th><td>{_esc(report['filename'])}</td></tr>",
        f"<tr><th>Generated at</th><td>{_esc(report['generated_at'])}</td></tr>",
    ]

    if report.get("rows") is not None:
        parts.append(
            f"<tr><th>Rows</th><td>{_esc(report['rows'])}</td></tr>"
        )
    if report.get("columns") is not None:
        parts.append(
            f"<tr><th>Columns</th><td>{_esc(report['columns'])}</td></tr>"
        )
    parts.append("</table>")

    if not report["sections"]:
        parts.append(
            "<p><em>No analysis sections were included in this "
            "report.</em></p>"
        )

    for section in report["sections"]:
        title = SECTION_TITLES[section["type"]]
        parts.append(f"<h2>{_esc(title)}</h2>")
        parts.append("<table>")
        for key, value in _flatten(section["data"]):
            parts.append(
                f"<tr><th>{_esc(key)}</th><td>{_esc(value)}</td></tr>"
            )
        parts.append("</table>")

    parts.append(
        '<div class="note"><strong>Interpretation notes.</strong> '
        "Correlation does not imply causation. Flagged outliers are "
        "potential data points, not necessarily errors. Machine "
        "learning metrics are computed on held-out test data and may "
        "be unreliable for small datasets. Reports reflect only the "
        "analyses supplied by the user; they are not persisted "
        "server-side.</div>"
    )
    parts.append(
        "<footer>Generated by the Personal AI Data Agent.</footer>"
    )
    parts.append("</body></html>")

    return "\n".join(parts)


import logging
import os
from io import BytesIO

import pandas as pd
from fastapi import (
    Body,
    FastAPI,
    File,
    Form,
    HTTPException,
    Query,
    Request,
    UploadFile,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from services.profiling import profile_dataset
from services.analysis import descriptive_statistics, group_by_column
from services.visualization import create_chart
from services.anomaly import calculate_correlations, detect_outliers
from services.agent import (
    LLMProviderError,
    MAX_QUESTION_LENGTH,
    run_agent,
)
from services.ml import inspect_targets, train_and_compare
from services.reports import ReportError, build_report

app = FastAPI(
    title="Personal AI Data Agent",
    description=(
        "An AI-powered platform for data analysis, "
        "statistics, and machine learning."
    ),
    version="0.1.0",
)

DEFAULT_CORS_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]


def parse_cors_origins(raw: str | None) -> list[str]:
    """
    Parse the comma-separated CORS_ORIGINS environment variable.

    Returns the default local-development origins when the variable is
    unset or blank. Wildcards are rejected because they are unsafe for
    public deployments. Whitespace and empty entries are ignored.
    """
    if raw is None or not raw.strip():
        return list(DEFAULT_CORS_ORIGINS)

    origins: list[str] = []
    for entry in raw.split(","):
        origin = entry.strip()
        if not origin:
            continue
        if origin == "*":
            raise ValueError(
                "CORS_ORIGINS must not contain the wildcard '*'. "
                "List explicit origins instead."
            )
        if origin not in origins:
            origins.append(origin)

    if not origins:
        return list(DEFAULT_CORS_ORIGINS)

    return origins


app.add_middleware(
    CORSMiddleware,
    allow_origins=parse_cors_origins(os.environ.get("CORS_ORIGINS")),
    allow_methods=["*"],
    allow_headers=["*"],
)

logger = logging.getLogger("personal_ai_data_agent")


@app.exception_handler(Exception)
async def unhandled_exception_handler(
    request: Request, exc: Exception
) -> JSONResponse:
    # Log full diagnostics server-side; return a generic body so no
    # stack traces, paths, or environment details reach clients.
    logger.exception("Unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content={"detail": "An unexpected server error occurred."},
    )


MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB
PREVIEW_ROWS = 5
MAX_COLUMNS = 2000


async def _read_csv_upload(
    file: UploadFile,
    *,
    require_rows: bool = True,
) -> pd.DataFrame:
    """
    Validate and parse an uploaded CSV with consistent limits.

    Raises HTTPException with a safe, generic message on any problem.
    """
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(
            status_code=400,
            detail="Please upload a CSV file.",
        )

    content = await file.read(MAX_FILE_SIZE + 1)

    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413,
            detail="File exceeds the 10 MB limit.",
        )

    if not content:
        raise HTTPException(
            status_code=400,
            detail="The uploaded file is empty.",
        )

    try:
        df = pd.read_csv(BytesIO(content))
    except (pd.errors.ParserError, UnicodeDecodeError, ValueError):
        raise HTTPException(
            status_code=400,
            detail="The file could not be parsed as a valid CSV.",
        ) from None

    if len(df.columns) > MAX_COLUMNS:
        raise HTTPException(
            status_code=400,
            detail=(
                f"The CSV exceeds the maximum of {MAX_COLUMNS} columns."
            ),
        )

    if df.empty or len(df.columns) == 0:
        raise HTTPException(
            status_code=400,
            detail="The CSV must contain a header and at least one data row.",
        )

    return df


@app.get("/")
def root():
    return {
        "message": "Personal AI Data Agent API is running!",
        "status": "success",
    }


@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "service": "personal-ai-data-agent",
    }


@app.post("/datasets/upload")
async def upload_dataset(file: UploadFile = File(...)):
    df = await _read_csv_upload(file)

    missing_values = {
        str(column): int(count)
        for column, count in df.isna().sum().items()
    }

    return {
        "filename": file.filename,
        "rows": len(df),
        "columns_count": len(df.columns),
        "columns": [
            {
                "name": str(column),
                "data_type": str(df[column].dtype),
                "missing_values": missing_values[str(column)],
            }
            for column in df.columns
        ],
        "preview": df.head(PREVIEW_ROWS).fillna("").to_dict(
            orient="records"
        ),
    }
@app.post("/datasets/profile")
async def profile_uploaded_dataset(file: UploadFile = File(...)):
    df = await _read_csv_upload(file)

    return {
        "filename": file.filename,
        **profile_dataset(df),
    }

@app.post("/analysis/descriptive")
async def analyze_descriptive(
    file: UploadFile = File(...),
    column: str = "",
):
    df = await _read_csv_upload(file)

    try:
        return descriptive_statistics(df, column)
    except (ValueError, TypeError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from None


@app.post("/analysis/group")
async def analyze_groups(
    file: UploadFile = File(...),
    group_column: str = "",
    value_column: str = "",
):
    df = await _read_csv_upload(file)

    try:
        return group_by_column(df, group_column, value_column)
    except (ValueError, TypeError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from None


@app.post("/visualizations/chart")
async def generate_chart(
    file: UploadFile = File(...),
    chart_type: str = "bar",
    x_column: str = "",
    y_column: str | None = None,
):
    df = await _read_csv_upload(file)

    try:
        chart = create_chart(df, chart_type, x_column, y_column)
    except (ValueError, TypeError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from None

    return {
        "chart_type": chart_type,
        "chart": chart,
    }


@app.post("/analysis/correlations")
async def analyze_correlations(
    file: UploadFile = File(...),
    method: str = "pearson",
):
    df = await _read_csv_upload(file)

    try:
        result = calculate_correlations(df, method)
    except (ValueError, TypeError) as error:
        raise HTTPException(status_code=400, detail=str(error)) from None

    return {"filename": file.filename, **result}


@app.post("/analysis/outliers")
async def analyze_outliers(
    file: UploadFile = File(...),
    column: str = Form(...),
):
    df = await _read_csv_upload(file)

    try:
        result = detect_outliers(df, column)
    except (ValueError, TypeError) as error:
        raise HTTPException(status_code=400, detail=str(error)) from None

    return {"filename": file.filename, **result}


@app.post("/agent/chat")
async def agent_chat(
    file: UploadFile = File(...),
    question: str = Form(...),
):
    if not question.strip():
        raise HTTPException(
            status_code=400,
            detail="The question must not be empty.",
        )

    if len(question) > MAX_QUESTION_LENGTH:
        raise HTTPException(
            status_code=400,
            detail=(
                f"The question exceeds {MAX_QUESTION_LENGTH} "
                "characters."
            ),
        )

    df = await _read_csv_upload(file)

    try:
        return await run_agent(df, question)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from None
    except LLMProviderError as error:
        raise HTTPException(status_code=502, detail=str(error)) from None


@app.post("/ml/targets")
async def ml_targets(file: UploadFile = File(...)):
    df = await _read_csv_upload(file)

    try:
        result = inspect_targets(df)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from None

    return {"filename": file.filename, **result}


@app.post("/ml/train")
async def ml_train(
    file: UploadFile = File(...),
    target_column: str = Form(...),
    feature_columns: str = Form(""),
    task: str = Form(""),
    test_size: float = Form(0.2),
):
    df = await _read_csv_upload(file)

    features = [
        column.strip()
        for column in feature_columns.split(",")
        if column.strip()
    ] or None

    try:
        result = train_and_compare(
            df,
            target_column=target_column,
            feature_columns=features,
            task=task or None,
            test_size=test_size,
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from None

    return {"filename": file.filename, **result}


@app.post("/reports/generate")
def generate_report_endpoint(
    payload: dict = Body(...),
    format: str = Query("json"),
):
    # Reports are built purely from results the user already computed;
    # nothing is recalculated, stored, or executed.
    try:
        content, media_type, filename = build_report(payload, format)
    except ReportError as error:
        raise HTTPException(status_code=400, detail=str(error)) from None

    return Response(
        content=content,
        media_type=media_type,
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"'
        },
    )

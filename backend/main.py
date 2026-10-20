
from io import BytesIO

import pandas as pd
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from services.profiling import profile_dataset
from services.analysis import descriptive_statistics, group_by_column
from services.visualization import create_chart
from services.anomaly import calculate_correlations, detect_outliers
from services.agent import (
    LLMProviderError,
    MAX_QUESTION_LENGTH,
    run_agent,
)

app = FastAPI(
    title="Personal AI Data Agent",
    description=(
        "An AI-powered platform for data analysis, "
        "statistics, and machine learning."
    ),
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_methods=["*"],
    allow_headers=["*"],
)

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB
PREVIEW_ROWS = 5


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
    if not file.filename:
        raise HTTPException(
            status_code=400,
            detail="A filename is required.",
        )

    if not file.filename.lower().endswith(".csv"):
        raise HTTPException(
            status_code=400,
            detail="Only CSV files are supported.",
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

    if df.empty or len(df.columns) == 0:
        raise HTTPException(
            status_code=400,
            detail="The CSV must contain a header and at least one data row.",
        )

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
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(
            status_code=400,
            detail="Only CSV files are supported.",
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

    if df.empty or len(df.columns) == 0:
        raise HTTPException(
            status_code=400,
            detail="The CSV must contain a header and at least one data row.",
        )

    return {
        "filename": file.filename,
        **profile_dataset(df),
    }

@app.post("/analysis/descriptive")
async def analyze_descriptive(
    file: UploadFile = File(...),
    column: str = "",
):
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(
            status_code=400,
            detail="Only CSV files are supported.",
        )

    content = await file.read(MAX_FILE_SIZE + 1)

    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413,
            detail="File exceeds the 10 MB limit.",
        )

    try:
        df = pd.read_csv(BytesIO(content))
        result = descriptive_statistics(df, column)
    except (pd.errors.ParserError, UnicodeDecodeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from None

    return result


@app.post("/analysis/group")
async def analyze_groups(
    file: UploadFile = File(...),
    group_column: str = "",
    value_column: str = "",
):
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(
            status_code=400,
            detail="Only CSV files are supported.",
        )

    content = await file.read(MAX_FILE_SIZE + 1)

    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413,
            detail="File exceeds the 10 MB limit.",
        )

    try:
        df = pd.read_csv(BytesIO(content))
        result = group_by_column(df, group_column, value_column)
    except (pd.errors.ParserError, UnicodeDecodeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from None

    return result


@app.post("/visualizations/chart")
async def generate_chart(
    file: UploadFile = File(...),
    chart_type: str = "bar",
    x_column: str = "",
    y_column: str | None = None,
):
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(
            status_code=400,
            detail="Only CSV files are supported.",
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
        chart = create_chart(df, chart_type, x_column, y_column)
    except (pd.errors.ParserError, UnicodeDecodeError, ValueError) as exc:
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

    try:
        df = pd.read_csv(BytesIO(content))
        result = calculate_correlations(df, method)
        return {"filename": file.filename, **result}

    except (pd.errors.ParserError, UnicodeDecodeError, ValueError) as error:
        raise HTTPException(status_code=400, detail=str(error))

@app.post("/analysis/outliers")
async def analyze_outliers(
    file: UploadFile = File(...),
    column: str = Form(...),
):
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

    try:
        df = pd.read_csv(BytesIO(content))
        result = detect_outliers(df, column)
        return {"filename": file.filename, **result}

    except (pd.errors.ParserError, UnicodeDecodeError, ValueError) as error:
        raise HTTPException(status_code=400, detail=str(error))


@app.post("/agent/chat")
async def agent_chat(
    file: UploadFile = File(...),
    question: str = Form(...),
):
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(
            status_code=400,
            detail="Please upload a CSV file.",
        )

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

    if df.empty or len(df.columns) == 0:
        raise HTTPException(
            status_code=400,
            detail="The CSV must contain a header and at least one data row.",
        )

    try:
        return await run_agent(df, question)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from None
    except LLMProviderError as error:
        raise HTTPException(status_code=502, detail=str(error)) from None

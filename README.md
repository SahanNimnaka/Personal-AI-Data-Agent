# Personal AI Data Agent

An AI-powered platform for data analysis, statistics, visualization, and
machine learning. Upload a CSV and explore it through profiling, descriptive
and group analysis, charts, correlations, outlier detection, a natural-language
agent, and ML model comparison — then export the results as a report.

- **Backend:** Python 3.13, FastAPI, Uvicorn, pandas, NumPy, SciPy,
  scikit-learn, Plotly.
- **Frontend:** React, TypeScript, Vite, Tailwind CSS, Vitest.

## Features

- CSV upload and dataset profiling (rows, columns, missing values, dtypes).
- Descriptive statistics and group-by analysis.
- Charts (bar, line, scatter, histogram, box) rendered with Plotly.
- Correlation analysis (Pearson, Spearman, Kendall) and IQR outlier detection.
- AI agent with a fixed tool allowlist and a deterministic offline fallback.
- Machine-learning training and evaluation (baseline vs. linear/logistic
  regression and random forest) on held-out test data.
- Report export as JSON, CSV, or HTML from the analyses you actually ran.

## Repository layout

```
backend/    FastAPI application, analysis services, tests
frontend/   React + Vite single-page dashboard
docs/       Project documentation
```

## Prerequisites (Windows)

- Python 3.13+
- Node.js 20+ (includes npm)
- PowerShell 5.1+ (built in)

## Backend setup (Windows PowerShell)

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

If script execution is blocked when activating the venv, run once:

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

Start the API (development, auto-reload):

```powershell
cd backend
.\.venv\Scripts\python.exe -m uvicorn main:app --reload --port 8000
```

- API root: http://localhost:8000/
- Health check: http://localhost:8000/health
- Interactive docs: http://localhost:8000/docs

## Frontend setup (Windows PowerShell)

```powershell
cd frontend
npm install
```

Create a local environment file (optional — the default already points at
`http://localhost:8000`):

```powershell
Copy-Item .env.example .env
```

Start the dev server:

```powershell
npm run dev
```

Open http://localhost:5173 in your browser.

## Environment variables

The backend reads these optional variables (all empty by default; the app
works without them using the deterministic offline fallback):

| Variable       | Purpose                                         | Default                     |
| -------------- | ----------------------------------------------- | --------------------------- |
| `LLM_API_KEY`  | Enables the LLM agent (OpenAI-compatible).      | *(unset — fallback mode)*   |
| `LLM_BASE_URL` | Base URL of the chat-completions endpoint.      | `https://api.openai.com/v1` |
| `LLM_MODEL`    | Model name sent to the provider.                | `gpt-4o-mini`               |

Set them for the current PowerShell session only (never commit them):

```powershell
$env:LLM_API_KEY = "your-key-here"
$env:LLM_MODEL   = "gpt-4o-mini"
```

The frontend reads one optional variable from `frontend/.env`:

| Variable            | Purpose                        | Default                 |
| ------------------- | ------------------------------ | ----------------------- |
| `VITE_API_BASE_URL` | Base URL of the FastAPI server | `http://localhost:8000` |

**Never commit real credentials.** `.env` files are git-ignored; only
`.env.example` templates are tracked.

## Testing

Backend (from `backend/`):

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

Frontend (from `frontend/`):

```powershell
npm test
```

Frontend production build:

```powershell
npm run build
```

## API overview

| Method | Path                     | Purpose                                  |
| ------ | ------------------------ | ---------------------------------------- |
| GET    | `/`                      | Service banner                           |
| GET    | `/health`                | Health check                             |
| POST   | `/datasets/upload`       | Upload and preview a CSV                 |
| POST   | `/datasets/profile`      | Full dataset profile                     |
| POST   | `/analysis/descriptive`  | Descriptive statistics for one column    |
| POST   | `/analysis/group`        | Group-by aggregation                     |
| POST   | `/visualizations/chart`  | Plotly chart configuration               |
| POST   | `/analysis/correlations` | Pairwise correlations                    |
| POST   | `/analysis/outliers`     | IQR outlier detection                    |
| POST   | `/agent/chat`            | Natural-language question about a dataset |
| POST   | `/ml/targets`            | List eligible ML target columns          |
| POST   | `/ml/train`              | Train and compare models                 |
| POST   | `/reports/generate`      | Export a report (JSON/CSV/HTML)          |

## Safety limits

- Uploads are capped at **10 MB** and must have a `.csv` filename.
- CSVs are limited to **2000 columns**.
- Agent questions are limited to **2000 characters**; the agent executes at
  most **6 tool calls** across **3 rounds**, restricted to a fixed tool
  allowlist.
- ML requires at least **20 rows**; classification needs at least **2 classes**
  with **5+ samples** each; `test_size` must be between **0.1 and 0.5**.
- Report payloads are limited to **2 MB** and **12 sections**, and all
  user-supplied text is HTML-escaped in HTML reports.
- Unexpected server errors are logged server-side and return a generic
  message to the client (no stack traces, paths, or secrets).

## Known limitations

- No authentication or user accounts; intended for local/personal use.
- No persistence: analyses and reports are computed per request and are not
  stored. PostgreSQL/database support is **not implemented** and is deferred.
- The LLM agent requires outbound network access; without credentials it uses
  a deterministic rule-based fallback that covers common question types.
- ML metrics are computed on held-out test data and are unreliable on small
  datasets.
- Very large or extremely wide datasets are bounded by the limits above for
  predictable resource use.

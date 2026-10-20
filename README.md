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

Copy `backend/.env.example` to `backend/.env` and fill in values as
needed. All backend variables are optional; the app works without them
using the deterministic offline fallback. See `backend/.env.example` for
the full annotated list.

| Variable       | Purpose                                                    | Default                                     |
| -------------- | ---------------------------------------------------------- | ------------------------------------------- |
| `LLM_API_KEY`  | Enables the LLM agent (OpenAI-compatible). Server-side only. | *(unset — fallback mode)*                 |
| `LLM_BASE_URL` | Base URL of the chat-completions endpoint.                 | `https://api.openai.com/v1`                 |
| `LLM_MODEL`    | Model name sent to the provider.                           | `gpt-4o-mini`                               |
| `CORS_ORIGINS` | Comma-separated allowed browser origins. Wildcards rejected. | local dev origins (see below)             |
| `PORT`         | Port the server binds to (set automatically by most hosts). | `8000`                                      |
| `LOG_LEVEL`    | Uvicorn log level (`info`, `debug`, `warning`).            | `info`                                      |

When `CORS_ORIGINS` is unset, the following local development origins are
allowed:

```
http://localhost:5173,http://127.0.0.1:5173
```

For production, set it to your deployed frontend origin, for example:

```powershell
$env:CORS_ORIGINS = "https://your-frontend.vercel.app"
```

Set variables for the current PowerShell session only (never commit them):

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

## Deployment

The app is a stateless API plus a static frontend. There is no database,
and no files are persisted, so both parts can scale horizontally.

### Deployment order

1. Deploy the **backend** first and note its public URL.
2. Set the frontend's `VITE_API_BASE_URL` to that URL **before building**.
3. Deploy the **frontend**.
4. Set the backend's `CORS_ORIGINS` to the deployed frontend origin and
   redeploy the backend.

### Backend on Render

1. Create a **Web Service** pointing at this repository.
2. Settings:
   - **Root directory:** `backend`
   - **Build command:** `pip install -r requirements.txt`
   - **Start command:** `python run.py`
   - **Health check path:** `/health`
   - **Environment:** Python 3.13
3. Environment variables (Render → Environment):
   - `CORS_ORIGINS` = your Vercel frontend origin
     (e.g. `https://your-frontend.vercel.app`)
   - `LLM_API_KEY` *(optional)* — only if you want the LLM agent enabled.
   - `LLM_BASE_URL`, `LLM_MODEL` *(optional)* — provider overrides.
   - `PORT` is injected automatically by Render; `run.py` reads it and
     binds `0.0.0.0`.
4. Confirm `https://<your-service>.onrender.com/health` returns
   `{"status": "healthy", ...}`.

The start command binds Uvicorn to `0.0.0.0` and the host-provided `PORT`,
falling back to `8000` locally. Run it directly for production:

```powershell
cd backend
python run.py
```

### Frontend on Vercel

1. Import the repository as a **Vercel project**.
2. Settings:
   - **Root directory:** `frontend`
   - **Build command:** `npm run build`
   - **Output directory:** `dist`
   - **Install command:** `npm install`
3. **Environment variable (set before building):**
   - `VITE_API_BASE_URL` = the deployed backend URL, no trailing slash
     (e.g. `https://your-service.onrender.com`).
4. Deploy, then copy the resulting origin into the backend's
   `CORS_ORIGINS`.

> `VITE_API_BASE_URL` is **inlined into the bundle at build time** by
> Vite. Changing it after deployment has no effect — you must rebuild and
> redeploy the frontend. There is no runtime override.

### Data and state on deployment

- Uploaded CSVs are read into memory per request and are **never written
  to disk**; each request is stateless.
- Analysis and ML results live in browser memory only. They are **not
  saved between browser reloads** and are not shared across users or
  instances.
- Report downloads are generated on demand and streamed back; nothing is
  stored server-side.

### Public exposure warning

This application has **no authentication and no rate limiting**. It is
intended for local or personal use. **Publicly exposing it is unsafe**,
and it is especially risky when `LLM_API_KEY` is configured — anyone who
can reach `/agent/chat` can consume your provider quota. Treat proper
authentication and rate limiting as **deployment blockers** for any
unrestricted public deployment. Do not assume the app is secure for open
access as-is.

## Known limitations

- No authentication, rate limiting, or user accounts; intended for
  local/personal use. Public exposure is a deployment blocker until these
  exist.
- No persistence: uploaded data and analysis results are held in memory
  only and are lost between browser reloads. PostgreSQL/database support is
  **not implemented** and is deferred.
- The LLM agent requires outbound network access; without credentials it uses
  a deterministic rule-based fallback that covers common question types.
- ML metrics are computed on held-out test data and are unreliable on small
  datasets.
- Very large or extremely wide datasets are bounded by the limits above for
  predictable resource use.

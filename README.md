# AI Log-to-Incident Report Generator

End-to-end project:
- `frontend/`: Next.js + Tailwind dashboard (multi-file log upload + report UI)
- `backend/`: FastAPI pipeline (parse -> time filter -> correlate -> root-cause -> Gemini/LangChain -> JSON report)

## Prerequisites

### Frontend
- Node.js 18+ (recommended)
- npm (ships with Node)

### Backend
- Python 3.9+ (works on 3.9; recommended 3.10+ for newer Google SDK support)
- `pip` (use `python3 -m pip ...`)

## Dependencies

### Frontend (direct)
Installed via `frontend/package.json`:
- `next`, `react`, `react-dom`
- `tailwindcss`, `postcss`, `autoprefixer`
- `typescript`, `@types/node`, `@types/react`, `@types/react-dom`

### Backend (direct)
Installed via `backend/requirements.txt`:
- `fastapi`
- `uvicorn[standard]`
- `python-multipart` (multipart file uploads)
- `drain3` (log template mining)
- `langchain-core` (prompting + parsing)
- `langchain-google-genai` (Gemini via LangChain)
- `pydantic` (validation)

## Setup

### 1) Backend environment variables (Gemini)

Create `backend/.env`:

```env
# Required (pick one)
GEMINI_API_KEY=YOUR_GEMINI_KEY
# or:
# GOOGLE_API_KEY=YOUR_GEMINI_KEY

# Optional
GEMINI_MODEL=gemini-2.5-flash

# Optional tuning
LLM_TIMEOUT_SECONDS=60
LLM_MAX_EVENTS=60
LLM_MAX_LOGS_PER_EVENT=6
```

### 2) Install backend dependencies

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements.txt
```

### 3) Install frontend dependencies

```bash
cd frontend
npm install
```

Optional: set a custom backend URL for the frontend by creating `frontend/.env.local`:

```env
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
```

## Run

### Terminal 1: Backend

```bash
cd backend
source .venv/bin/activate
uvicorn main:app --host 0.0.0.0 --port 8000
```

Health check:
- Open `http://localhost:8000/health`

### Terminal 2: Frontend

```bash
cd frontend
npm run dev
```

Open:
- `http://localhost:3000`

## Backend API

### `GET /health`
Returns `{ "status": "ok" }`.

### `POST /upload-logs`
Multipart file upload (saves to temp session dir) and returns file metadata.
- Field name: `files` (repeat for multiple files)

### `POST /generate-report`
Multipart form fields:
- Files: `logs` (preferred) or `files` (repeat for multiple files)
- `start_time`: timestamp string
- `end_time`: timestamp string
- `architecture`: description string (or `architecture_description`)

Supported timestamp inputs include:
- ISO with seconds: `2026-04-16T09:14:03Z`
- ISO minute precision (from `<input type="datetime-local">`): `2026-04-16T09:10`
- `YYYY-MM-DD HH:MM:SS`
- Epoch seconds/millis

Example `curl`:

```bash
curl -X POST http://localhost:8000/generate-report \
  -F "logs=@app.log" \
  -F "logs=@db.log" \
  -F "start_time=2026-04-16T09:10" \
  -F "end_time=2026-04-16T09:30" \
  -F "architecture=API Gateway -> services -> Postgres/Redis on Kubernetes"
```

## Troubleshooting

### 502: "LLM report generation failed"
- Confirm your key is set in `backend/.env` and restart `uvicorn`.
- If the key is missing, the backend returns HTTP 400 with a specific message.

### Browser shows "Failed to fetch"
- Backend must be running and reachable.
- Verify `http://localhost:8000/health`.
- If your frontend runs on `127.0.0.1:3000`, that origin is allowed by default CORS.

### Python / Google SDK warnings
If you see warnings about Python 3.9 being EOL, upgrading to Python 3.10+ will reduce these and improve compatibility long-term.


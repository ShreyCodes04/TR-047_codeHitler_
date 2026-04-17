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

You can also copy `frontend/.env.example` and update it for local development.

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

## Deploy Frontend To Vercel

This frontend is a standard Next.js app in `frontend/`, so Vercel can deploy it directly.

### Before deploying

1. Confirm your Render backend URL works:
   - Example: `https://your-render-service.onrender.com/health`
   - It should return `{ "status": "ok" }`
2. In Render, add/update `CORS_ORIGINS` so your Vercel site is allowed.
   - Example value:

```env
CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000,https://your-project.vercel.app
```

If you later connect a custom domain, add that too:

```env
CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000,https://your-project.vercel.app,https://yourdomain.com
```

3. Redeploy the Render backend after changing backend environment variables.

### Vercel project settings

When importing the repo into Vercel, use:

- Framework Preset: `Next.js`
- Root Directory: `frontend`
- Build Command: `npm run build`
- Output Directory: leave default
- Install Command: `npm install`

### Vercel environment variables

Add these in Vercel Project Settings -> Environment Variables:

```env
NEXT_PUBLIC_API_BASE_URL=https://your-render-service.onrender.com
```

Optional:

```env
NEXT_PUBLIC_SPLINE_SCENE_URL=https://prod.spline.design/your-scene-url/scene.splinecode
```

### Step-by-step deployment

1. Push the repository to GitHub.
2. Log in to Vercel.
3. Click `Add New...` -> `Project`.
4. Import your GitHub repository.
5. Set the root directory to `frontend`.
6. Verify Vercel detected `Next.js`.
7. Add `NEXT_PUBLIC_API_BASE_URL` with your Render backend URL.
8. Click `Deploy`.
9. After deployment finishes, open the Vercel URL.
10. Test:
   - `/`
   - `/login`
   - `/dashboard`
   - login/register flow
   - report generation flow

### If the frontend loads but API calls fail

Check these in order:

1. `NEXT_PUBLIC_API_BASE_URL` in Vercel points to the Render backend base URL with no trailing slash.
2. Render backend has `CORS_ORIGINS` including the exact Vercel domain.
3. Render backend is healthy at `/health`.
4. Your backend secrets like `GEMINI_API_KEY` or `GROQ_API_KEY` are still set in Render.

### Python / Google SDK warnings
If you see warnings about Python 3.9 being EOL, upgrading to Python 3.10+ will reduce these and improve compatibility long-term.

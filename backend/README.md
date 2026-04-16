# AI Log Analysis Backend (FastAPI)

FastAPI backend that:
- uploads and stores log files temporarily
- parses + correlates logs into events
- ranks suspected root causes
- generates a structured report via Gemini (LangChain)

For full end-to-end setup (frontend + backend), see the top-level `README.md`.

## Run

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements.txt
# required for LLM step (pick one)
export GEMINI_API_KEY="YOUR_KEY"
# or:
# export GOOGLE_API_KEY="YOUR_KEY"
uvicorn main:app --host 0.0.0.0 --port 8000
```

## Endpoints

- `POST /upload-logs` (multipart form)
  - field name: `files` (one or more files)

Example:

```bash
curl -X POST http://localhost:8000/upload-logs \
  -F "files=@app.log" \
  -F "files=@db.log"
```

- `POST /generate-report` (multipart form)
  - files: `logs` (preferred) or `files` (repeat for multiple)
  - `start_time`, `end_time`
  - `architecture` (or `architecture_description`)

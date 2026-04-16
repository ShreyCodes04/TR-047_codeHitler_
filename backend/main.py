from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routes.generate_report import router as generate_report_router
from routes.upload_logs import router as upload_logs_router
from utils.logging import configure_logging
from utils.settings import settings


@asynccontextmanager
async def lifespan(_: FastAPI):
    configure_logging()
    yield


app = FastAPI(
    title="AI Log Analysis API",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(upload_logs_router)
app.include_router(generate_report_router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}

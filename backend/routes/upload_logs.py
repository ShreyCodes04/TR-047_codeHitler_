from __future__ import annotations

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, File, HTTPException, UploadFile
from pydantic import BaseModel, Field

from services.storage import cleanup_old_sessions, save_uploads
from utils.settings import settings


router = APIRouter()


class UploadedFileMeta(BaseModel):
    original_name: str
    content_type: Optional[str] = None
    size_bytes: int
    sha256: str
    saved_as: str
    temp_path: str


class UploadLogsResponse(BaseModel):
    session_id: str
    saved_dir: str
    expires_at: datetime
    total_bytes: int
    file_count: int = Field(ge=0)
    files: list[UploadedFileMeta]


@router.post("/upload-logs", response_model=UploadLogsResponse)
async def upload_logs(
    background_tasks: BackgroundTasks,
    files: list[UploadFile] = File(...),
) -> UploadLogsResponse:
    if not files:
        raise HTTPException(status_code=400, detail="No files uploaded. Use form field name 'files'.")

    if len(files) > settings.max_files:
        raise HTTPException(
            status_code=413,
            detail=f"Too many files. Max is {settings.max_files}.",
        )

    # Best-effort cleanup of old sessions without blocking the request path.
    background_tasks.add_task(cleanup_old_sessions)

    try:
        saved = await save_uploads(files)
    finally:
        # Ensure UploadFile handles are closed to release resources.
        for file in files:
            try:
                await file.close()
            except Exception:
                pass

    return UploadLogsResponse(
        session_id=saved.session_id,
        saved_dir=str(saved.saved_dir),
        expires_at=saved.expires_at,
        total_bytes=saved.total_bytes,
        file_count=len(saved.files),
        files=[
            UploadedFileMeta(
                original_name=file_meta.original_name,
                content_type=file_meta.content_type,
                size_bytes=file_meta.size_bytes,
                sha256=file_meta.sha256,
                saved_as=file_meta.saved_as,
                temp_path=str(file_meta.temp_path),
            )
            for file_meta in saved.files
        ],
    )

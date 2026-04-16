from __future__ import annotations

import hashlib
import os
import re
import shutil
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional
from uuid import uuid4

from fastapi import HTTPException, UploadFile

from utils.settings import settings


SAFE_NAME_RE = re.compile(r"[^A-Za-z0-9._-]+")


@dataclass(frozen=True)
class SavedFile:
    original_name: str
    content_type: Optional[str]
    size_bytes: int
    sha256: str
    saved_as: str
    temp_path: Path


@dataclass(frozen=True)
class SaveResult:
    session_id: str
    saved_dir: Path
    expires_at: datetime
    total_bytes: int
    files: list[SavedFile]


def _ensure_temp_root() -> Path:
    temp_root = Path(settings.temp_dir).expanduser().resolve()
    temp_root.mkdir(parents=True, exist_ok=True)
    return temp_root


def _safe_filename(filename: str) -> str:
    candidate = (filename or "upload.log").strip()
    candidate = candidate.replace(os.sep, "_")
    candidate = SAFE_NAME_RE.sub("_", candidate)
    if candidate in {"", ".", ".."}:
        candidate = "upload.log"
    return candidate[:180]


async def save_uploads(files: list[UploadFile]) -> SaveResult:
    temp_root = _ensure_temp_root()
    session_id = uuid4().hex
    session_dir = temp_root / session_id
    session_dir.mkdir(parents=True, exist_ok=True)

    expires_at = datetime.now(timezone.utc) + timedelta(seconds=settings.temp_ttl_seconds)
    saved_files: list[SavedFile] = []
    total_bytes = 0

    try:
        for index, upload in enumerate(files, start=1):
            original_name = upload.filename or f"upload-{index}.log"
            safe_name = _safe_filename(original_name)

            # Avoid accidental overwrites on duplicate names.
            target_path = session_dir / safe_name
            if target_path.exists():
                target_path = session_dir / f"{Path(safe_name).stem}-{uuid4().hex[:8]}{Path(safe_name).suffix}"

            sha256 = hashlib.sha256()
            size_bytes = 0

            with target_path.open("wb") as out:
                while True:
                    chunk = await upload.read(settings.chunk_size)
                    if not chunk:
                        break
                    size_bytes += len(chunk)
                    total_bytes += len(chunk)

                    if size_bytes > settings.max_file_bytes:
                        raise HTTPException(
                            status_code=413,
                            detail=f"File too large: {original_name}. Max is {settings.max_file_bytes} bytes.",
                        )
                    if total_bytes > settings.max_total_bytes:
                        raise HTTPException(
                            status_code=413,
                            detail=f"Total upload too large. Max is {settings.max_total_bytes} bytes.",
                        )

                    sha256.update(chunk)
                    out.write(chunk)

            saved_files.append(
                SavedFile(
                    original_name=original_name,
                    content_type=upload.content_type,
                    size_bytes=size_bytes,
                    sha256=sha256.hexdigest(),
                    saved_as=target_path.name,
                    temp_path=target_path,
                )
            )

        return SaveResult(
            session_id=session_id,
            saved_dir=session_dir,
            expires_at=expires_at,
            total_bytes=total_bytes,
            files=saved_files,
        )
    except Exception:
        # On any error, remove the partially-written session to keep temp clean.
        shutil.rmtree(session_dir, ignore_errors=True)
        raise


def cleanup_old_sessions() -> None:
    temp_root = _ensure_temp_root()
    cutoff = datetime.now(timezone.utc) - timedelta(seconds=settings.temp_ttl_seconds)

    for entry in temp_root.iterdir():
        if not entry.is_dir():
            continue
        try:
            stat = entry.stat()
            modified = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc)
            if modified < cutoff:
                shutil.rmtree(entry, ignore_errors=True)
        except Exception:
            # Best-effort only: avoid failing requests because cleanup had issues.
            continue

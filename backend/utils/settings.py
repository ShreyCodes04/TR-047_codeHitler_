import os
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional


def _load_local_env() -> None:
    env_path = Path(__file__).resolve().parent.parent / ".env"
    if not env_path.exists():
        return

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip("\"'")
        os.environ.setdefault(key, value)


_load_local_env()


def _parse_int(value: Optional[str], default: int) -> int:
    try:
        return int(value) if value is not None else default
    except ValueError:
        return default


def _parse_csv(value: Optional[str], default: List[str]) -> List[str]:
    if not value:
        return default
    return [part.strip() for part in value.split(",") if part.strip()]


@dataclass(frozen=True)
class Settings:
    temp_dir: str
    temp_ttl_seconds: int
    max_files: int
    max_file_bytes: int
    max_total_bytes: int
    chunk_size: int
    cors_origins: list[str]
    llm_provider: str
    groq_api_key: str
    groq_model: str
    google_api_key: str
    gemini_api_key: str
    gemini_model: str
    llm_timeout_seconds: int
    llm_max_events: int
    llm_max_logs_per_event: int
    jwt_secret: str
    jwt_exp_minutes: int


settings = Settings(
    temp_dir=os.getenv("TEMP_UPLOAD_DIR", "/tmp/ai-log-analysis-uploads"),
    temp_ttl_seconds=_parse_int(os.getenv("TEMP_UPLOAD_TTL_SECONDS"), 24 * 60 * 60),
    max_files=_parse_int(os.getenv("MAX_UPLOAD_FILES"), 20),
    max_file_bytes=_parse_int(os.getenv("MAX_UPLOAD_FILE_BYTES"), 50 * 1024 * 1024),
    max_total_bytes=_parse_int(os.getenv("MAX_UPLOAD_TOTAL_BYTES"), 200 * 1024 * 1024),
    chunk_size=_parse_int(os.getenv("UPLOAD_CHUNK_SIZE"), 1024 * 1024),
    cors_origins=_parse_csv(
        os.getenv("CORS_ORIGINS"),
        [
            "http://localhost:3000",
            "http://127.0.0.1:3000",
            "http://localhost:3001",
            "http://127.0.0.1:3001",
        ],
    ),
    llm_provider=os.getenv("LLM_PROVIDER", "auto").strip().lower(),
    groq_api_key=os.getenv("GROQ_API_KEY", ""),
    groq_model=os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile"),
    google_api_key=os.getenv("GOOGLE_API_KEY", ""),
    gemini_api_key=os.getenv("GEMINI_API_KEY", ""),
    gemini_model=os.getenv("GEMINI_MODEL", "gemini-2.5-flash"),
    llm_timeout_seconds=_parse_int(os.getenv("LLM_TIMEOUT_SECONDS"), 60),
    llm_max_events=_parse_int(os.getenv("LLM_MAX_EVENTS"), 30),
    llm_max_logs_per_event=_parse_int(os.getenv("LLM_MAX_LOGS_PER_EVENT"), 4),
    jwt_secret=os.getenv("JWT_SECRET", "dev-secret-change-me"),
    jwt_exp_minutes=_parse_int(os.getenv("JWT_EXP_MINUTES"), 60 * 24 * 7),
)

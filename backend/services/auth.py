from datetime import datetime, timezone
from typing import Optional

from passlib.context import CryptContext

from utils.db import get_conn


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return pwd_context.verify(password, password_hash)


def create_user(email: str, password: str) -> None:
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO users (email, password_hash, created_at) VALUES (?, ?, ?)",
            (email.lower().strip(), hash_password(password), datetime.now(tz=timezone.utc).isoformat()),
        )
        conn.commit()


def get_user_by_email(email: str) -> Optional[dict]:
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM users WHERE email = ?", (email.lower().strip(),)).fetchone()
        return dict(row) if row else None


def authenticate(email: str, password: str) -> bool:
    user = get_user_by_email(email)
    if not user:
        return False
    return verify_password(password, user["password_hash"])


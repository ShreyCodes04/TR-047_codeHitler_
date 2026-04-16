from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

from jose import JWTError, jwt

from utils.settings import settings


ALGORITHM = "HS256"


def create_access_token(subject: str) -> str:
    now = datetime.now(tz=timezone.utc)
    exp = now + timedelta(minutes=int(settings.jwt_exp_minutes))
    payload: Dict[str, Any] = {"sub": subject, "iat": int(now.timestamp()), "exp": int(exp.timestamp())}
    return jwt.encode(payload, settings.jwt_secret, algorithm=ALGORITHM)


def decode_token(token: str) -> Optional[dict]:
    try:
        return jwt.decode(token, settings.jwt_secret, algorithms=[ALGORITHM])
    except JWTError:
        return None


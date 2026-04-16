from fastapi import APIRouter, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, EmailStr

from services.auth import authenticate, create_user, get_user_by_email
from utils.jwt import create_access_token, decode_token


router = APIRouter(prefix="/auth", tags=["auth"])
bearer = HTTPBearer(auto_error=False)


class AuthRequest(BaseModel):
    email: EmailStr
    password: str


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


@router.post("/register", response_model=AuthResponse)
def register(payload: AuthRequest) -> AuthResponse:
    if len(payload.password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters.")

    existing = get_user_by_email(payload.email)
    if existing:
        raise HTTPException(status_code=409, detail="User already exists.")

    create_user(payload.email, payload.password)
    return AuthResponse(access_token=create_access_token(payload.email))


@router.post("/login", response_model=AuthResponse)
def login(payload: AuthRequest) -> AuthResponse:
    if not authenticate(payload.email, payload.password):
        raise HTTPException(status_code=401, detail="Invalid email or password.")
    return AuthResponse(access_token=create_access_token(payload.email))


@router.get("/me")
def me(credentials: HTTPAuthorizationCredentials = bearer):
    if not credentials:
        raise HTTPException(status_code=401, detail="Missing Authorization header.")
    decoded = decode_token(credentials.credentials)
    if not decoded or "sub" not in decoded:
        raise HTTPException(status_code=401, detail="Invalid token.")
    user = get_user_by_email(decoded["sub"])
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")
    return {"email": user["email"], "created_at": user["created_at"]}


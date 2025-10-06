from datetime import datetime, timedelta, timezone
from typing import Optional
import os

from fastapi import APIRouter, Depends, HTTPException, Response, Request, status
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session
from passlib.context import CryptContext
from jose import jwt, JWTError

from app.db import get_db
from app.models import User

JWT_SECRET = os.getenv("JWT_SECRET", "change-me")  # nastav v Render env
JWT_ALG = "HS256"
ACCESS_TOKEN_EXPIRE_MIN = 60 * 24 * 7  # 7 dní
COOKIE_NAME = "auth"

COOKIE_KW = dict(
    httponly=True,
    secure=True,         # Render = HTTPS
    samesite="none",     # cross-site z frontendu
    path="/",
    max_age=ACCESS_TOKEN_EXPIRE_MIN * 60,
)

router = APIRouter(prefix="/auth", tags=["auth"])
pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")


class RegisterIn(BaseModel):
    email: EmailStr
    name: str
    password: str


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    id: int
    email: EmailStr
    name: str

    class Config:
        from_attributes = True


def hash_pw(pw: str) -> str:
    return pwd_ctx.hash(pw)


def verify_pw(pw: str, hashed: str) -> bool:
    return pwd_ctx.verify(pw, hashed)


def make_access_token(sub: str) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": sub,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MIN)).timestamp()),
        "type": "access",
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALG)


def decode_token(token: str) -> dict:
    return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALG])


def set_auth_cookie(resp: Response, token: str) -> None:
    resp.set_cookie(COOKIE_NAME, token, **COOKIE_KW)


def clear_auth_cookie(resp: Response) -> None:
    resp.delete_cookie(COOKIE_NAME, path=COOKIE_KW["path"], samesite=COOKIE_KW["samesite"])


def current_user(request: Request, db: Session = Depends(get_db)) -> User:
    token: Optional[str] = request.cookies.get(COOKIE_NAME)
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    try:
        payload = decode_token(token)
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    email = payload.get("sub")
    user: Optional[User] = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user


@router.post("/register", response_model=UserOut)
def register(body: RegisterIn, response: Response, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.email == body.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    user = User(email=body.email, name=body.name, password_hash=hash_pw(body.password))
    db.add(user)
    db.commit()
    db.refresh(user)

    token = make_access_token(user.email)
    set_auth_cookie(response, token)
    return user


@router.post("/login")
def login(body: LoginIn, response: Response, db: Session = Depends(get_db)):
    user: Optional[User] = db.query(User).filter(User.email == body.email).first()
    if not user or not verify_pw(body.password, user.password_hash):
        # 401 pro špatné přihlášení (ne 403)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    token = make_access_token(user.email)
    set_auth_cookie(response, token)
    return {"ok": True}


@router.post("/logout")
def logout(response: Response):
    clear_auth_cookie(response)
    return {"ok": True}


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(current_user)):
    return user

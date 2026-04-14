from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import Depends, HTTPException, status, Cookie
from fastapi.security import OAuth2PasswordBearer
import jwt
from jwt import PyJWTError
import bcrypt
from sqlmodel import Session

from database import get_session_dependency

from models import Player

#jwt config
SECRET_KEY = "hardik-roxx"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24

MAX_BCRYPT_PASSWORD_BYTES = 72
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/login")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    if plain_password is None:
        return False
    # bcrypt accepts at most 72 bytes; protect here
    if len(plain_password.encode("utf-8")) > MAX_BCRYPT_PASSWORD_BYTES:
        raise ValueError(f"Password too long: bcrypt limits to {MAX_BCRYPT_PASSWORD_BYTES} bytes; truncate before hashing")
    return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password)


def get_password_hash(password: str) -> str:
    if password is None:
        raise ValueError("Password is required")
    if len(password.encode("utf-8")) > MAX_BCRYPT_PASSWORD_BYTES:
        raise ValueError(f"Password too long: bcrypt limits to {MAX_BCRYPT_PASSWORD_BYTES} bytes; truncate before hashing")
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def decode_access_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except PyJWTError:
        raise


def get_current_user(token: str = Depends(oauth2_scheme), session: Session = Depends(get_session_dependency)) -> Player:
    from fastapi import HTTPException

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except PyJWTError:
        raise credentials_exception

    player = session.query(Player).filter(Player.username == username).first()
    if player is None:
        raise credentials_exception
    return player


def get_current_user_from_cookie(session_id: Optional[str] = Cookie(None), session: Session = Depends(get_session_dependency)) -> Player:
    """Dependency to authenticate a player using the `session_id` cookie.

    Returns the `Player` or raises 401.
    """
    if not session_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing session cookie")

    try:
        payload = decode_access_token(session_id)
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    player = session.query(Player).filter(Player.username == username).first()
    if player is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    return player

"""
JWT Authentication for Admin Panel.
"""
from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
import bcrypt
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer
from fastapi import Cookie
from loguru import logger
import os

from config import ADMIN_IDS
from database import get_admin_user, update_admin_last_login

# JWT Configuration
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-in-production-use-env-variable")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 480  # 8 hours

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/admin/login", auto_error=False)


def _truncate_password_bytes(password: str, max_bytes: int = 72) -> bytes:
    """Truncate password to max_bytes, handling UTF-8 character boundaries."""
    password_bytes = password.encode('utf-8')
    if len(password_bytes) <= max_bytes:
        return password_bytes
    
    # Truncate to max_bytes
    truncated_bytes = password_bytes[:max_bytes]
    
    # If truncation happened at a UTF-8 character boundary, we're good
    # Otherwise, we need to find the last valid UTF-8 character boundary
    try:
        # Try to decode to check if we're at a valid boundary
        truncated_bytes.decode('utf-8')
        return truncated_bytes
    except UnicodeDecodeError:
        # Backtrack to find valid UTF-8 boundary
        while len(truncated_bytes) > 0:
            try:
                truncated_bytes.decode('utf-8')
                return truncated_bytes
            except UnicodeDecodeError:
                truncated_bytes = truncated_bytes[:-1]
        return truncated_bytes


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    # Bcrypt has a 72-byte limit, so truncate if necessary
    password_bytes = _truncate_password_bytes(plain_password, max_bytes=72)
    # Ensure hashed_password is bytes
    if isinstance(hashed_password, str):
        hashed_password_bytes = hashed_password.encode('utf-8')
    else:
        hashed_password_bytes = hashed_password
    
    try:
        return bcrypt.checkpw(password_bytes, hashed_password_bytes)
    except (ValueError, TypeError):
        return False


def get_password_hash(password: str) -> str:
    """Hash a password. Bcrypt has a 72-byte limit, so truncate if necessary."""
    # Bcrypt has a 72-byte limit, so truncate if necessary
    password_bytes = _truncate_password_bytes(password, max_bytes=72)
    # Generate salt and hash
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password_bytes, salt)
    # Return as string (bcrypt format)
    return hashed.decode('utf-8')


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Create a JWT access token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


async def authenticate_admin(email: str, password: str) -> Optional[dict]:
    """Authenticate an admin user."""
    import asyncio
    
    user = await get_admin_user(email)
    if not user:
        return None
    
    if not verify_password(password, user["password_hash"]):
        return None
    
    # Update last login
    await update_admin_last_login(email)
    
    return user


async def get_current_admin(
    request: Request,
    token: str = Depends(oauth2_scheme),
    access_token: str = Cookie(None)
) -> dict:
    """Get current authenticated admin from JWT token (cookie or header)."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    # Try to get token from cookie first, then from header
    token_value = access_token or token
    if not token_value:
        raise credentials_exception
    
    try:
        payload = jwt.decode(token_value, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    user = await get_admin_user(email)
    if user is None:
        raise credentials_exception
    
    return user


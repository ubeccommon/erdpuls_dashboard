"""
Erdpuls Collective Threshold Model - Authentication
"""
from datetime import datetime, timedelta
from typing import Optional

from fastapi import Depends, HTTPException, status, Request
from fastapi.responses import RedirectResponse
from passlib.context import CryptContext
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
from sqlalchemy.orm import Session

from .database import get_db
from .models import User
from .config import get_settings

settings = get_settings()

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Session serializer
serializer = URLSafeTimedSerializer(settings.secret_key)

# Session cookie settings
SESSION_COOKIE_NAME = "erdpuls_session"
SESSION_MAX_AGE = 60 * 60 * 24 * 7  # 7 days


def hash_password(password: str) -> str:
    """Hash a password."""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return pwd_context.verify(plain_password, hashed_password)


def create_session_token(user_id: str) -> str:
    """Create a signed session token."""
    return serializer.dumps({"user_id": user_id})


def verify_session_token(token: str) -> Optional[str]:
    """Verify a session token and return user_id if valid."""
    try:
        data = serializer.loads(token, max_age=SESSION_MAX_AGE)
        return data.get("user_id")
    except (BadSignature, SignatureExpired):
        return None


def get_current_user_optional(request: Request, db: Session = Depends(get_db)) -> Optional[User]:
    """Get current user from session cookie (returns None if not logged in)."""
    token = request.cookies.get(SESSION_COOKIE_NAME)
    if not token:
        return None
    
    user_id = verify_session_token(token)
    if not user_id:
        return None
    
    user = db.query(User).filter(User.id == user_id, User.is_active == True).first()
    return user


def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    """Get current user from session cookie (raises exception if not logged in)."""
    user = get_current_user_optional(request, db)
    if not user:
        # For API routes, raise exception
        if request.url.path.startswith("/api/"):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Not authenticated"
            )
        # For web routes, redirect to login
        raise HTTPException(
            status_code=status.HTTP_303_SEE_OTHER,
            headers={"Location": f"/login?next={request.url.path}"}
        )
    return user


def get_admin_user(request: Request, db: Session = Depends(get_db)) -> User:
    """Get current user and verify admin role."""
    user = get_current_user(request, db)
    if not user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return user


def authenticate_user(email: str, password: str, db: Session) -> Optional[User]:
    """Authenticate a user by email and password."""
    user = db.query(User).filter(User.email == email.lower()).first()
    if not user:
        return None
    if not verify_password(password, user.password_hash):
        return None
    if not user.is_active:
        return None
    return user


def create_user(
    email: str, 
    password: str, 
    name: Optional[str] = None,
    role: str = "user",
    db: Session = None
) -> User:
    """Create a new user."""
    # Check if email already exists
    existing = db.query(User).filter(User.email == email.lower()).first()
    if existing:
        raise ValueError("Email already registered")
    
    user = User(
        email=email.lower(),
        password_hash=hash_password(password),
        name=name,
        role=role
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def set_session_cookie(response, user_id: str):
    """Set the session cookie on a response."""
    token = create_session_token(user_id)
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=token,
        max_age=SESSION_MAX_AGE,
        httponly=True,
        samesite="lax",
        secure=False  # Set to True in production with HTTPS
    )
    return response


def clear_session_cookie(response):
    """Clear the session cookie."""
    response.delete_cookie(SESSION_COOKIE_NAME)
    return response

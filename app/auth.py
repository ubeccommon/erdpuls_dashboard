"""
Erdpuls Collective Threshold Model - Authentication

Features:
- Password hashing and verification
- Session management with activity-based timeout
- Password reset token generation and verification

© 2026 Michel Garand | Lizenz: CC BY-NC-SA 4.0 | https://creativecommons.org/licenses/by-nc-sa/4.0/deed.de
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
SESSION_MAX_AGE = 60 * 60 * 24 * 7  # 7 days absolute maximum

# Inactivity timeout (configurable via environment or default)
# Default: 30 minutes of inactivity = auto logout
SESSION_INACTIVITY_TIMEOUT = getattr(settings, 'session_inactivity_timeout', 60 * 30)

# Password reset token expiry: 1 hour
PASSWORD_RESET_TOKEN_MAX_AGE = 60 * 60


def hash_password(password: str) -> str:
    """Hash a password."""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return pwd_context.verify(plain_password, hashed_password)


def create_session_token(user_id: str) -> str:
    """Create a signed session token with activity timestamp."""
    return serializer.dumps({
        "user_id": user_id,
        "last_activity": datetime.utcnow().isoformat()
    })


def verify_session_token(token: str, check_inactivity: bool = True) -> Optional[str]:
    """
    Verify a session token and return user_id if valid.
    
    Checks both:
    - Absolute expiry (7 days from creation)
    - Inactivity timeout (30 minutes since last activity)
    
    Returns user_id if valid, None otherwise.
    """
    try:
        data = serializer.loads(token, max_age=SESSION_MAX_AGE)
        user_id = data.get("user_id")
        
        if not user_id:
            return None
        
        # Check inactivity timeout
        if check_inactivity:
            last_activity_str = data.get("last_activity")
            if last_activity_str:
                try:
                    last_activity = datetime.fromisoformat(last_activity_str)
                    inactive_seconds = (datetime.utcnow() - last_activity).total_seconds()
                    if inactive_seconds > SESSION_INACTIVITY_TIMEOUT:
                        return None  # Session expired due to inactivity
                except (ValueError, TypeError):
                    pass  # If parsing fails, allow session to continue
        
        return user_id
        
    except (BadSignature, SignatureExpired):
        return None


def get_current_user_optional(request: Request, db: Session = Depends(get_db)) -> Optional[User]:
    """Get current user from session cookie (returns None if not logged in or session expired)."""
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
    role: str = "member",
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
    """Set the session cookie on a response with fresh activity timestamp."""
    token = create_session_token(user_id)
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=token,
        max_age=SESSION_MAX_AGE,
        httponly=True,
        samesite="lax",
        secure=True  # HTTPS required in production
    )
    return response


def refresh_session_cookie(response, user_id: str):
    """
    Refresh the session cookie with updated activity timestamp.
    Call this on user actions to extend the inactivity timeout.
    """
    return set_session_cookie(response, user_id)


def clear_session_cookie(response):
    """Clear the session cookie."""
    response.delete_cookie(SESSION_COOKIE_NAME)
    return response


# ============================================
# Password Reset Functions
# ============================================

def create_password_reset_token(user_id: str, email: str) -> str:
    """
    Create a secure, time-limited password reset token.
    
    Token contains user_id and email hash for double verification.
    Expires after PASSWORD_RESET_TOKEN_MAX_AGE (1 hour).
    """
    return serializer.dumps({
        "user_id": user_id,
        "email": email.lower(),
        "purpose": "password_reset",
        "created_at": datetime.utcnow().isoformat()
    })


def verify_password_reset_token(token: str) -> Optional[dict]:
    """
    Verify a password reset token.
    
    Returns dict with 'user_id' and 'email' if valid, None otherwise.
    Token expires after 1 hour.
    """
    try:
        data = serializer.loads(token, max_age=PASSWORD_RESET_TOKEN_MAX_AGE)
        
        # Verify it's a password reset token
        if data.get("purpose") != "password_reset":
            return None
        
        user_id = data.get("user_id")
        email = data.get("email")
        
        if not user_id or not email:
            return None
        
        return {
            "user_id": user_id,
            "email": email
        }
        
    except SignatureExpired:
        return None  # Token expired
    except BadSignature:
        return None  # Invalid/tampered token


def get_password_reset_url(token: str) -> str:
    """Generate the full password reset URL using clean path."""
    base_url = settings.base_url.rstrip('/')
    # Use /r/ instead of /reset-password?token= to avoid spam filters
    return f"{base_url}/r/{token}"

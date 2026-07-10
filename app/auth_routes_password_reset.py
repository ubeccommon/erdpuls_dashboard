"""
Password Reset Routes - Add these to your existing app/routers/auth.py file

© 2024–2026 Michel Garand | License: GNU AGPL v3.0 | https://www.gnu.org/licenses/agpl-3.0.html

Add these imports at the top of auth.py:
    from ..auth import (
        authenticate_user, create_user, hash_password,
        get_current_user_optional, get_current_user,
        set_session_cookie, clear_session_cookie,
        SESSION_COOKIE_NAME,
        # New password reset imports:
        create_password_reset_token,
        verify_password_reset_token,
        get_password_reset_url
    )
    from ..email import send_password_reset_email

Then add these routes to your auth.py router:
"""


# ============================================
# Forgot Password - Request Reset
# ============================================

@router.get("/forgot-password", response_class=HTMLResponse)
def forgot_password_page(
    request: Request,
    success: Optional[str] = None,
    error: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Forgot password page - enter email to receive reset link"""
    lang = get_lang(request)
    user = get_current_user_optional(request, db)
    
    # Already logged in - redirect to dashboard
    if user:
        return RedirectResponse(url="/dashboard", status_code=303)
    
    return templates.TemplateResponse(
        "auth/forgot_password.html",
        {
            "request": request,
            "lang": lang,
            "success": success,
            "error": error
        }
    )


@router.post("/forgot-password")
def forgot_password_submit(
    request: Request,
    email: str = Form(...),
    db: Session = Depends(get_db)
):
    """Process forgot password request - send reset email"""
    lang = get_lang(request)
    
    # Look up user by email
    user = db.query(User).filter(User.email == email.lower()).first()
    
    # Always show success message (don't reveal if email exists)
    # This prevents email enumeration attacks
    if user and user.is_active:
        # Create reset token and send email
        token = create_password_reset_token(user.id, user.email)
        reset_url = get_password_reset_url(token)
        
        # Import the email function
        from ..email import send_password_reset_email
        send_password_reset_email(
            to_email=user.email,
            reset_url=reset_url,
            lang=lang
        )
    
    # Always redirect with success (prevents email enumeration)
    return RedirectResponse(
        url="/forgot-password?success=sent",
        status_code=303
    )


# ============================================
# Reset Password - Enter New Password
# ============================================

@router.get("/reset-password", response_class=HTMLResponse)
def reset_password_page(
    request: Request,
    token: str = None,
    error: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Reset password page - enter new password"""
    lang = get_lang(request)
    
    # Verify token is present
    if not token:
        return RedirectResponse(
            url="/forgot-password?error=missing_token",
            status_code=303
        )
    
    # Verify token is valid (not expired, not tampered)
    token_data = verify_password_reset_token(token)
    if not token_data:
        return RedirectResponse(
            url="/forgot-password?error=invalid_token",
            status_code=303
        )
    
    # Verify user still exists and is active
    user = db.query(User).filter(
        User.id == token_data["user_id"],
        User.email == token_data["email"],
        User.is_active == True
    ).first()
    
    if not user:
        return RedirectResponse(
            url="/forgot-password?error=invalid_token",
            status_code=303
        )
    
    return templates.TemplateResponse(
        "auth/reset_password.html",
        {
            "request": request,
            "lang": lang,
            "token": token,
            "email": user.email,
            "error": error
        }
    )


@router.post("/reset-password")
def reset_password_submit(
    request: Request,
    token: str = Form(...),
    password: str = Form(...),
    password_confirm: str = Form(...),
    db: Session = Depends(get_db)
):
    """Process password reset - update password"""
    lang = get_lang(request)
    
    # Verify token again
    token_data = verify_password_reset_token(token)
    if not token_data:
        return RedirectResponse(
            url="/forgot-password?error=invalid_token",
            status_code=303
        )
    
    # Validate passwords match
    if password != password_confirm:
        return RedirectResponse(
            url=f"/reset-password?token={token}&error=password_mismatch",
            status_code=303
        )
    
    # Validate password length
    if len(password) < 8:
        return RedirectResponse(
            url=f"/reset-password?token={token}&error=password_short",
            status_code=303
        )
    
    # Get user and update password
    user = db.query(User).filter(
        User.id == token_data["user_id"],
        User.email == token_data["email"],
        User.is_active == True
    ).first()
    
    if not user:
        return RedirectResponse(
            url="/forgot-password?error=invalid_token",
            status_code=303
        )
    
    # Update password
    user.password_hash = hash_password(password)
    db.commit()
    
    # Redirect to login with success message
    return RedirectResponse(
        url="/login?success=password_reset",
        status_code=303
    )

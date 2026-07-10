"""
Session Refresh API Endpoint - Add this to your existing app/routers/api.py file

© 2024–2026 Michel Garand | License: GNU AGPL v3.0 | https://www.gnu.org/licenses/agpl-3.0.html

Add this import:
    from ..auth import get_current_user_optional, refresh_session_cookie

Add this route to your api.py router:
"""

@router.post("/session/refresh")
def refresh_session(
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Refresh the user's session cookie.
    Called by the frontend to extend session on user activity.
    """
    from ..auth import get_current_user_optional, refresh_session_cookie
    from fastapi.responses import JSONResponse
    
    user = get_current_user_optional(request, db)
    
    if not user:
        return JSONResponse(
            status_code=401,
            content={"detail": "Not authenticated"}
        )
    
    response = JSONResponse(content={"status": "ok"})
    refresh_session_cookie(response, user.id)
    return response

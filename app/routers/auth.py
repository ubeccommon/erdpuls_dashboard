"""
Erdpuls Collective Threshold Model - Auth Router
With role-based permissions for offering creation and password reset.

© 2024–2026 Michel Garand | License: GNU AGPL v3.0 | https://www.gnu.org/licenses/agpl-3.0.html
"""
from typing import Optional, List

from fastapi import APIRouter, Depends, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import User
from ..auth import (
    authenticate_user, create_user, hash_password,
    get_current_user_optional, get_current_user,
    set_session_cookie, clear_session_cookie,
    SESSION_COOKIE_NAME,
    # Password reset functions
    create_password_reset_token,
    verify_password_reset_token,
    get_password_reset_url
)
from ..roles import (
    UserRole, can_create_offering, can_publish_direct, 
    can_approve_offerings, has_role_or_higher
)
from ..email import send_password_reset_email

router = APIRouter(tags=["auth"])
templates = Jinja2Templates(directory="templates")


def get_lang(request: Request) -> str:
    """Get language from query param or cookie"""
    lang = request.query_params.get('lang')
    if lang and lang in ['en', 'de', 'pl']:
        return lang
    return request.cookies.get('lang', 'en')


def get_user_home(user: User) -> str:
    """Get the appropriate home page for a user based on their role"""
    # Admins and moderators go to admin panel
    if has_role_or_higher(user.role, UserRole.MODERATOR.value):
        return "/admin"
    return "/dashboard"


# ============================================
# Login
# ============================================

@router.get("/login", response_class=HTMLResponse)
def login_page(
    request: Request, 
    next: Optional[str] = None,
    error: Optional[str] = None,
    success: Optional[str] = None,
    expired: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Login page"""
    lang = get_lang(request)
    user = get_current_user_optional(request, db)
    
    # Already logged in - redirect to appropriate page
    if user:
        if next:
            return RedirectResponse(url=next, status_code=303)
        return RedirectResponse(url=get_user_home(user), status_code=303)
    
    return templates.TemplateResponse(
        "auth/login.html",
        {
            "request": request,
            "lang": lang,
            "next": next,
            "error": error,
            "success": success,
            "expired": expired
        }
    )


@router.post("/login")
def login(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    next: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    """Process login"""
    user = authenticate_user(email, password, db)
    
    if not user:
        return RedirectResponse(
            url=f"/login?error=invalid&next={next or ''}",
            status_code=303
        )
    
    # Update last login
    from datetime import datetime
    user.last_login = datetime.utcnow()
    db.commit()
    
    # Create session and redirect
    if next:
        redirect_url = next
    else:
        redirect_url = get_user_home(user)
    
    response = RedirectResponse(url=redirect_url, status_code=303)
    set_session_cookie(response, user.id)
    return response


# ============================================
# Logout
# ============================================

@router.get("/logout")
@router.post("/logout")
def logout(request: Request):
    """Log out"""
    response = RedirectResponse(url="/", status_code=303)
    clear_session_cookie(response)
    return response


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
# Uses /r/{token} path to avoid spam filter triggers on email URLs
# ============================================

@router.get("/r/{token}", response_class=HTMLResponse)
def reset_password_page(
    request: Request,
    token: str,
    error: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Reset password page - enter new password"""
    lang = get_lang(request)
    
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


@router.post("/r/{token}")
def reset_password_submit(
    request: Request,
    token: str,
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
            url=f"/r/{token}?error=password_mismatch",
            status_code=303
        )
    
    # Validate password length
    if len(password) < 8:
        return RedirectResponse(
            url=f"/r/{token}?error=password_short",
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


# ============================================
# Register
# ============================================

@router.get("/register", response_class=HTMLResponse)
def register_page(
    request: Request,
    error: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Registration page"""
    lang = get_lang(request)
    user = get_current_user_optional(request, db)
    
    # Already logged in - redirect to appropriate page
    if user:
        return RedirectResponse(url=get_user_home(user), status_code=303)
    
    return templates.TemplateResponse(
        "auth/register.html",
        {
            "request": request,
            "lang": lang,
            "error": error
        }
    )


@router.post("/register")
def register(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    password_confirm: str = Form(...),
    name: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    """Process registration"""
    lang = get_lang(request)
    
    # Validate passwords match
    if password != password_confirm:
        return RedirectResponse(
            url="/register?error=password_mismatch",
            status_code=303
        )
    
    # Validate password length
    if len(password) < 8:
        return RedirectResponse(
            url="/register?error=password_short",
            status_code=303
        )
    
    # Try to create user with 'member' role (default)
    try:
        user = create_user(
            email=email,
            password=password,
            name=name,
            role=UserRole.MEMBER.value,  # New users are members by default
            db=db
        )
    except ValueError as e:
        return RedirectResponse(
            url="/register?error=email_exists",
            status_code=303
        )
    
    # Log in the new user
    response = RedirectResponse(url="/dashboard?welcome=1", status_code=303)
    set_session_cookie(response, user.id)
    return response


# ============================================
# Dashboard
# ============================================

@router.get("/dashboard", response_class=HTMLResponse)
def dashboard(
    request: Request,
    welcome: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """User dashboard"""
    lang = get_lang(request)
    user = get_current_user_optional(request, db)
    
    if not user:
        return RedirectResponse(url="/login?next=/dashboard", status_code=303)
    
    # Get user's offerings (only if they can create)
    from ..models import Offering
    my_offerings = []
    if can_create_offering(user.role):
        my_offerings = db.query(Offering).filter(
            Offering.creator_id == user.id
        ).order_by(Offering.created_at.desc()).all()
        
        # Add computed properties
        for o in my_offerings:
            o._total = o.get_total_contributed(db)
            o._reg_count = o.get_registration_count(db)
            o._percent = round((float(o._total) / float(o.threshold_amount)) * 100, 1) if o.threshold_amount else 0
    
    # For moderators and admins, get all offerings
    all_offerings = None
    if can_approve_offerings(user.role):
        all_offerings = db.query(Offering).order_by(Offering.created_at.desc()).all()
        for o in all_offerings:
            o._total = o.get_total_contributed(db)
            o._reg_count = o.get_registration_count(db)
            o._percent = round((float(o._total) / float(o.threshold_amount)) * 100, 1) if o.threshold_amount else 0
    
    # Check if user can create offerings
    user_can_create = can_create_offering(user.role)
    
    return templates.TemplateResponse(
        "auth/dashboard.html",
        {
            "request": request,
            "lang": lang,
            "user": user,
            "my_offerings": my_offerings,
            "all_offerings": all_offerings,
            "welcome": welcome,
            "can_create": user_can_create
        }
    )


# ============================================
# Create Offering
# ============================================

@router.get("/dashboard/create", response_class=HTMLResponse)
def create_offering_page(
    request: Request,
    db: Session = Depends(get_db)
):
    """Create offering page"""
    lang = get_lang(request)
    user = get_current_user_optional(request, db)
    
    if not user:
        return RedirectResponse(url="/login?next=/dashboard/create", status_code=303)
    
    # Check if user has permission to create offerings
    if not can_create_offering(user.role):
        return RedirectResponse(url="/dashboard?error=no_create_permission", status_code=303)
    
    # Only the places this person belongs to. Offering every initiative to
    # everyone would invite attaching work to a place one has nothing to
    # do with, and the check below would then reject it after the fact.
    from ..membership import initiatives_for
    initiatives = initiatives_for(db, user, "member")

    return templates.TemplateResponse(
        "auth/create_offering.html",
        {
            "request": request,
            "lang": lang,
            "user": user,
            "initiatives": initiatives
        }
    )


@router.post("/dashboard/create")
def create_offering(
    request: Request,
    title: str = Form(...),
    title_de: Optional[str] = Form(None),
    title_pl: Optional[str] = Form(None),
    title_uk: Optional[str] = Form(None),
    description: str = Form(...),
    description_de: Optional[str] = Form(None),
    description_pl: Optional[str] = Form(None),
    description_uk: Optional[str] = Form(None),
    delivery_language: List[str] = Form(default=['de']),
    currency: str = Form(default='EUR'),
    initiative_id: str = Form(default=''),
    facilitator_cost: float = Form(0),
    materials_cost: float = Form(0),
    catering_cost: float = Form(0),
    space_cost: float = Form(0),
    sustainability_contribution: float = Form(0),
    event_date: Optional[str] = Form(None),
    registration_deadline: str = Form(...),
    contribution_deadline_date: str = Form(...),
    contribution_deadline_time: str = Form("23:59"),
    max_participants: Optional[int] = Form(None),
    organizer_name: str = Form(...),
    organizer_email: str = Form(...),
    organizer_phone: Optional[str] = Form(None),
    solidarity_financing: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    """Create a new offering"""
    user = get_current_user_optional(request, db)
    
    if not user:
        return RedirectResponse(url="/login?next=/dashboard/create", status_code=303)
    
    # Check if user has permission to create offerings
    if not can_create_offering(user.role):
        return RedirectResponse(url="/dashboard?error=no_create_permission", status_code=303)
    
    from datetime import datetime
    from decimal import Decimal
    from ..models import Offering
    
    # Validate delivery_language
    valid_languages = {'de', 'en', 'pl', 'uk'}
    # An offering's figures are in its own currency and are never
    # converted; an unknown code would make every figure on it meaningless.
    if currency not in {'EUR', 'PLN', 'UAH'}:
        return RedirectResponse(url="/dashboard/create?error=currency_invalid", status_code=303)

    # An offering may only be attached to a place its author belongs to.
    # Checked here and not only in the form, because a hand-crafted post
    # would otherwise attach work to any initiative.
    if initiative_id:
        from ..membership import member_at_least
        if not member_at_least(db, user, initiative_id, "member"):
            return RedirectResponse(url="/dashboard/create?error=not_a_member",
                                    status_code=303)
    delivery_language = [lang for lang in delivery_language if lang in valid_languages]
    if not delivery_language:
        delivery_language = ['de']  # Default fallback
    
    # Validate title lengths (security: prevent abuse)
    TITLE_MIN = 3
    TITLE_MAX = 255
    
    if len(title) < TITLE_MIN:
        return RedirectResponse(url="/dashboard/create?error=title_too_short", status_code=303)
    if len(title) > TITLE_MAX:
        return RedirectResponse(url="/dashboard/create?error=title_too_long", status_code=303)
    
    # Validate optional titles only if provided
    if title_de and (len(title_de) < TITLE_MIN or len(title_de) > TITLE_MAX):
        return RedirectResponse(url="/dashboard/create?error=title_de_invalid", status_code=303)
    if title_pl and (len(title_pl) < TITLE_MIN or len(title_pl) > TITLE_MAX):
        return RedirectResponse(url="/dashboard/create?error=title_pl_invalid", status_code=303)
    if title_uk and (len(title_uk) < TITLE_MIN or len(title_uk) > TITLE_MAX):
        return RedirectResponse(url="/dashboard/create?error=title_uk_invalid", status_code=303)
    
    # Validate description lengths (security: prevent abuse)
    DESC_MIN = 50
    DESC_MAX = 5000
    
    if len(description) < DESC_MIN:
        return RedirectResponse(url="/dashboard/create?error=description_too_short", status_code=303)
    if len(description) > DESC_MAX:
        return RedirectResponse(url="/dashboard/create?error=description_too_long", status_code=303)
    
    # Validate optional descriptions only if provided
    if description_de and (len(description_de) < DESC_MIN or len(description_de) > DESC_MAX):
        return RedirectResponse(url="/dashboard/create?error=description_de_invalid", status_code=303)
    if description_pl and (len(description_pl) < DESC_MIN or len(description_pl) > DESC_MAX):
        return RedirectResponse(url="/dashboard/create?error=description_pl_invalid", status_code=303)
    
    # Calculate threshold
    threshold = (
        Decimal(str(facilitator_cost)) +
        Decimal(str(materials_cost)) +
        Decimal(str(catering_cost)) +
        Decimal(str(space_cost)) +
        Decimal(str(sustainability_contribution))
    )
    
    # Parse dates - handle various formats browsers might send
    def parse_date(date_str):
        if not date_str or date_str.strip() == '':
            return None
        
        date_str = date_str.strip()
        
        formats = [
            '%Y-%m-%dT%H:%M:%S', '%Y-%m-%dT%H:%M', '%Y-%m-%d %H:%M:%S',
            '%Y-%m-%d %H:%M', '%Y-%m-%d', '%d.%m.%Y %H:%M', '%d.%m.%Y', '%d/%m/%Y',
        ]
        
        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue
        
        try:
            return datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        except:
            pass
        
        try:
            date_part = date_str.split('T')[0].split(' ')[0]
            return datetime.strptime(date_part, '%Y-%m-%d')
        except:
            pass
        
        return None
    
    def parse_datetime(date_str, time_str):
        if not date_str:
            return None
        combined = f"{date_str} {time_str or '23:59'}"
        try:
            return datetime.strptime(combined, '%Y-%m-%d %H:%M')
        except:
            return parse_date(date_str)
    
    parsed_event_date = parse_date(event_date)
    parsed_registration = parse_date(registration_deadline)
    parsed_contribution = parse_datetime(contribution_deadline_date, contribution_deadline_time)
    
    if not parsed_registration:
        return RedirectResponse(url="/dashboard/create?error=invalid_registration_date", status_code=303)
    if not parsed_contribution:
        return RedirectResponse(url="/dashboard/create?error=invalid_contribution_date", status_code=303)
    
    # Determine initial status based on user's role
    # Facilitators, moderators, and admins can publish directly
    # Creators need approval (draft status)
    if can_publish_direct(user.role):
        initial_status = 'open'
    else:
        initial_status = 'draft'
    
    offering = Offering(
        title=title,
        title_de=title_de or None,
        title_pl=title_pl or None,
        title_uk=title_uk or None,
        description=description,
        description_de=description_de or None,
        description_pl=description_pl or None,
        description_uk=description_uk or None,
        delivery_language=delivery_language,
        threshold_amount=threshold,
        currency=currency,
        initiative_id=initiative_id or None,
        facilitator_cost=Decimal(str(facilitator_cost)),
        materials_cost=Decimal(str(materials_cost)),
        catering_cost=Decimal(str(catering_cost)),
        space_cost=Decimal(str(space_cost)),
        sustainability_contribution=Decimal(str(sustainability_contribution)),
        event_date=parsed_event_date,
        registration_deadline=parsed_registration,
        contribution_deadline=parsed_contribution,
        max_participants=max_participants or None,
        organizer_name=organizer_name,
        organizer_email=organizer_email,
        organizer_phone=organizer_phone or None,
        creator_id=user.id,
        created_by=user.name or user.email,
        status=initial_status
    )
    
    db.add(offering)
    db.commit()

    # Optional: finance this offering through the solidarity module.
    # Only for facilitator and above, since that is who may open the
    # module at all — a creator ticking this box would otherwise make a
    # session they cannot reach. Nothing is copied but the words: the
    # offering's costs are EUR and the session budget is UAH, and no
    # conversion happens anywhere in the module. The facilitator enters
    # the UAH budget; the EUR threshold travels only as a reference note.
    if solidarity_financing:
        from ..roles import has_role_or_higher
        from ..membership import member_at_least as _member_at_least
        if (has_role_or_higher(user.role, "facilitator")
                and offering.initiative_id
                and _member_at_least(db, user, offering.initiative_id, "facilitator")):
            from sqlalchemy import text as _sql
            db.refresh(offering)
            label = offering.title[:120]
            if db.execute(_sql("SELECT 1 FROM solidarity.camp_session WHERE label = :l"),
                          {"l": label}).first():
                label = f"{label} ({str(offering.id)[:8]})"
            # A session must know where it happens: it is mounted under an
            # initiative and its record keeps that place directly, so it
            # survives this offering's deletion. An offering with no
            # initiative therefore cannot open one.
            if not offering.initiative_id:
                return RedirectResponse(
                    url="/dashboard?created=1&solidarity=no_initiative", status_code=303)
            note = ("Opened from an Erdpuls offering. Threshold "
                    f"{offering.threshold_amount} {offering.currency}"
                    + ("." if offering.currency == 'UAH' else
                       " — reference only, not converted. Enter the session budget in UAH."))
            db.execute(_sql("""INSERT INTO solidarity.camp_session
                               (label, description, offering_id, initiative_id, note)
                               VALUES (:l, :d, :o, :i, :n)"""),
                       {"l": label, "d": offering.description or "",
                        "o": str(offering.id), "i": str(offering.initiative_id),
                        "n": note})
            db.commit()
            slug = db.execute(_sql("SELECT slug FROM erdpuls_threshold.initiatives WHERE id = :i"),
                              {"i": str(offering.initiative_id)}).scalar()
            return RedirectResponse(url=f"/{slug}/solidarity/", status_code=303)

    return RedirectResponse(url="/dashboard?created=1", status_code=303)


# ============================================
# Manage Offering
# ============================================

@router.get("/dashboard/offering/{offering_id}", response_class=HTMLResponse)
def manage_offering_page(
    offering_id: str,
    request: Request,
    db: Session = Depends(get_db)
):
    """Manage a specific offering"""
    lang = get_lang(request)
    user = get_current_user_optional(request, db)
    
    if not user:
        return RedirectResponse(url=f"/login?next=/dashboard/offering/{offering_id}", status_code=303)
    
    from ..models import Offering, Registration, Contribution
    
    offering = db.query(Offering).filter(Offering.id == offering_id).first()
    if not offering:
        raise HTTPException(status_code=404, detail="Offering not found")
    
    # Check permission: own offering OR moderator/admin
    is_owner = offering.creator_id == user.id
    is_moderator = can_approve_offerings(user.role)
    
    if not is_owner and not is_moderator:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Get registrations
    registrations = db.query(Registration).filter(
        Registration.offering_id == offering_id
    ).order_by(Registration.registered_at.desc()).all()
    
    # Get contributions
    contributions = db.query(Contribution).filter(
        Contribution.offering_id == offering_id
    ).order_by(Contribution.contributed_at.desc()).all()
    
    # Add computed properties
    offering._total = offering.get_total_contributed(db)
    offering._reg_count = len(registrations)
    offering._percent = round((float(offering._total) / float(offering.threshold_amount)) * 100, 1)
    offering._threshold_reached = float(offering._total) >= float(offering.threshold_amount)
    
    return templates.TemplateResponse(
        "auth/manage_offering.html",
        {
            "request": request,
            "lang": lang,
            "user": user,
            "offering": offering,
            "registrations": registrations,
            "contributions": contributions,
            "can_approve": is_moderator
        }
    )


@router.post("/dashboard/offering/{offering_id}/status")
def update_offering_status(
    offering_id: str,
    request: Request,
    status: str = Form(...),
    db: Session = Depends(get_db)
):
    """Update offering status"""
    user = get_current_user_optional(request, db)
    
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    
    from ..models import Offering
    
    offering = db.query(Offering).filter(Offering.id == offering_id).first()
    if not offering:
        raise HTTPException(status_code=404, detail="Offering not found")
    
    # Check permission: only moderators and admins can change status
    if not can_approve_offerings(user.role):
        raise HTTPException(status_code=403, detail="Moderator access required")
    
    valid_statuses = ['draft', 'open', 'threshold_met', 'confirmed', 'completed', 'cancelled']
    if status not in valid_statuses:
        raise HTTPException(status_code=400, detail="Invalid status")
    
    offering.status = status
    db.commit()
    
    return RedirectResponse(url=f"/dashboard/offering/{offering_id}?updated=1", status_code=303)


# ============================================
# Edit Offering
# ============================================

EDITABLE_STATUSES = ['draft', 'open', 'threshold_met']

@router.get("/dashboard/offering/{offering_id}/edit", response_class=HTMLResponse)
def edit_offering_page(
    offering_id: str,
    request: Request,
    db: Session = Depends(get_db)
):
    """Edit offering page"""
    lang = get_lang(request)
    user = get_current_user_optional(request, db)
    
    if not user:
        return RedirectResponse(url=f"/login?next=/dashboard/offering/{offering_id}/edit", status_code=303)
    
    from ..models import Offering
    
    offering = db.query(Offering).filter(Offering.id == offering_id).first()
    if not offering:
        raise HTTPException(status_code=404, detail="Offering not found")
    
    # Check permission: own offering OR moderator/admin
    is_owner = offering.creator_id == user.id
    is_moderator = can_approve_offerings(user.role)
    
    if not is_owner and not is_moderator:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Check if editable
    if offering.status not in EDITABLE_STATUSES:
        return RedirectResponse(url=f"/dashboard/offering/{offering_id}?error=not_editable", status_code=303)
    
    return templates.TemplateResponse(
        "auth/edit_offering.html",
        {
            "request": request,
            "lang": lang,
            "user": user,
            "offering": offering
        }
    )


@router.post("/dashboard/offering/{offering_id}/edit")
def edit_offering(
    offering_id: str,
    request: Request,
    title: str = Form(...),
    title_de: Optional[str] = Form(None),
    title_pl: Optional[str] = Form(None),
    description: str = Form(...),
    description_de: Optional[str] = Form(None),
    description_pl: Optional[str] = Form(None),
    delivery_language: List[str] = Form(default=['de']),
    facilitator_cost: float = Form(0),
    materials_cost: float = Form(0),
    catering_cost: float = Form(0),
    space_cost: float = Form(0),
    sustainability_contribution: float = Form(0),
    event_date: Optional[str] = Form(None),
    registration_deadline: str = Form(...),
    contribution_deadline_date: str = Form(...),
    contribution_deadline_time: str = Form("23:59"),
    max_participants: Optional[int] = Form(None),
    organizer_name: str = Form(...),
    organizer_email: str = Form(...),
    organizer_phone: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    """Update an existing offering"""
    user = get_current_user_optional(request, db)
    
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    
    from datetime import datetime
    from decimal import Decimal
    from ..models import Offering
    
    offering = db.query(Offering).filter(Offering.id == offering_id).first()
    if not offering:
        raise HTTPException(status_code=404, detail="Offering not found")
    
    # Check permission
    is_owner = offering.creator_id == user.id
    is_moderator = can_approve_offerings(user.role)
    
    if not is_owner and not is_moderator:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Check if editable
    if offering.status not in EDITABLE_STATUSES:
        return RedirectResponse(url=f"/dashboard/offering/{offering_id}?error=not_editable", status_code=303)
    
    # Validate delivery_language
    valid_languages = {'de', 'en', 'pl', 'uk'}
    # An offering's figures are in its own currency and are never
    # converted; an unknown code would make every figure on it meaningless.
    if currency not in {'EUR', 'PLN', 'UAH'}:
        return RedirectResponse(url="/dashboard/create?error=currency_invalid", status_code=303)

    # An offering may only be attached to a place its author belongs to.
    # Checked here and not only in the form, because a hand-crafted post
    # would otherwise attach work to any initiative.
    if initiative_id:
        from ..membership import member_at_least
        if not member_at_least(db, user, initiative_id, "member"):
            return RedirectResponse(url="/dashboard/create?error=not_a_member",
                                    status_code=303)
    delivery_language = [lang for lang in delivery_language if lang in valid_languages]
    if not delivery_language:
        delivery_language = ['de']  # Default fallback
    
    # Validate title lengths (security: prevent abuse)
    TITLE_MIN = 3
    TITLE_MAX = 255
    
    if len(title) < TITLE_MIN:
        return RedirectResponse(url=f"/dashboard/offering/{offering_id}/edit?error=title_too_short", status_code=303)
    if len(title) > TITLE_MAX:
        return RedirectResponse(url=f"/dashboard/offering/{offering_id}/edit?error=title_too_long", status_code=303)
    
    # Validate optional titles only if provided
    if title_de and (len(title_de) < TITLE_MIN or len(title_de) > TITLE_MAX):
        return RedirectResponse(url=f"/dashboard/offering/{offering_id}/edit?error=title_de_invalid", status_code=303)
    if title_pl and (len(title_pl) < TITLE_MIN or len(title_pl) > TITLE_MAX):
        return RedirectResponse(url=f"/dashboard/offering/{offering_id}/edit?error=title_pl_invalid", status_code=303)
    
    # Validate description lengths (security: prevent abuse)
    DESC_MIN = 50
    DESC_MAX = 5000
    
    if len(description) < DESC_MIN:
        return RedirectResponse(url=f"/dashboard/offering/{offering_id}/edit?error=description_too_short", status_code=303)
    if len(description) > DESC_MAX:
        return RedirectResponse(url=f"/dashboard/offering/{offering_id}/edit?error=description_too_long", status_code=303)
    
    # Validate optional descriptions only if provided
    if description_de and (len(description_de) < DESC_MIN or len(description_de) > DESC_MAX):
        return RedirectResponse(url=f"/dashboard/offering/{offering_id}/edit?error=description_de_invalid", status_code=303)
    if description_pl and (len(description_pl) < DESC_MIN or len(description_pl) > DESC_MAX):
        return RedirectResponse(url=f"/dashboard/offering/{offering_id}/edit?error=description_pl_invalid", status_code=303)
    
    # Calculate threshold
    threshold = (
        Decimal(str(facilitator_cost)) +
        Decimal(str(materials_cost)) +
        Decimal(str(catering_cost)) +
        Decimal(str(space_cost)) +
        Decimal(str(sustainability_contribution))
    )
    
    # Parse dates
    def parse_date(date_str):
        if not date_str or date_str.strip() == '':
            return None
        date_str = date_str.strip()
        formats = [
            '%Y-%m-%dT%H:%M:%S', '%Y-%m-%dT%H:%M', '%Y-%m-%d %H:%M:%S',
            '%Y-%m-%d %H:%M', '%Y-%m-%d', '%d.%m.%Y %H:%M', '%d.%m.%Y', '%d/%m/%Y',
        ]
        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue
        try:
            return datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        except:
            pass
        try:
            date_part = date_str.split('T')[0].split(' ')[0]
            return datetime.strptime(date_part, '%Y-%m-%d')
        except:
            pass
        return None
    
    def parse_datetime(date_str, time_str):
        if not date_str:
            return None
        combined = f"{date_str} {time_str or '23:59'}"
        try:
            return datetime.strptime(combined, '%Y-%m-%d %H:%M')
        except:
            return parse_date(date_str)
    
    parsed_event_date = parse_date(event_date)
    parsed_registration = parse_date(registration_deadline)
    parsed_contribution = parse_datetime(contribution_deadline_date, contribution_deadline_time)
    
    if not parsed_registration:
        return RedirectResponse(url=f"/dashboard/offering/{offering_id}/edit?error=invalid_registration_date", status_code=303)
    if not parsed_contribution:
        return RedirectResponse(url=f"/dashboard/offering/{offering_id}/edit?error=invalid_contribution_date", status_code=303)
    
    # Update offering
    offering.title = title
    offering.title_de = title_de or None
    offering.title_pl = title_pl or None
    offering.description = description
    offering.description_de = description_de or None
    offering.description_pl = description_pl or None
    offering.delivery_language = delivery_language
    offering.threshold_amount = threshold
    offering.facilitator_cost = Decimal(str(facilitator_cost))
    offering.materials_cost = Decimal(str(materials_cost))
    offering.catering_cost = Decimal(str(catering_cost))
    offering.space_cost = Decimal(str(space_cost))
    offering.sustainability_contribution = Decimal(str(sustainability_contribution))
    offering.event_date = parsed_event_date
    offering.registration_deadline = parsed_registration
    offering.contribution_deadline = parsed_contribution
    offering.max_participants = max_participants or None
    offering.organizer_name = organizer_name
    offering.organizer_email = organizer_email
    offering.organizer_phone = organizer_phone or None
    
    db.commit()
    
    return RedirectResponse(url=f"/dashboard/offering/{offering_id}?saved=1", status_code=303)


@router.post("/dashboard/offering/{offering_id}/delete")
def delete_offering(
    offering_id: str,
    request: Request,
    db: Session = Depends(get_db)
):
    """Delete an offering"""
    user = get_current_user_optional(request, db)
    
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    
    from ..models import Offering
    
    offering = db.query(Offering).filter(Offering.id == offering_id).first()
    if not offering:
        raise HTTPException(status_code=404, detail="Offering not found")
    
    # Check permission
    is_owner = offering.creator_id == user.id
    is_admin = user.role == UserRole.ADMIN.value
    
    if not is_owner and not is_admin:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Only draft can be deleted by regular creators, admins can delete any
    if offering.status != 'draft' and not is_admin:
        return RedirectResponse(url=f"/dashboard/offering/{offering_id}?error=cannot_delete", status_code=303)
    
    db.delete(offering)
    db.commit()
    
    return RedirectResponse(url="/dashboard?deleted=1", status_code=303)

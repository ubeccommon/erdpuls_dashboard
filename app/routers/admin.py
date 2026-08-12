"""
Erdpuls Collective Threshold Model - Admin Router
Comprehensive admin interface for managing users, participants, supporters, and system settings.
"""
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Optional
import logging

from fastapi import APIRouter, Depends, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, text

from ..database import get_db
from ..models import (
    User, Offering, Registration, Contribution, ContributionContact,
    RegenerationFund, TokenRate, HoursRate, Initiative
)
from ..initiatives import get_initiatives, create_data_dir
from ..auth import get_current_user_optional

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["admin"])
templates = Jinja2Templates(directory="templates")


def get_lang(request: Request) -> str:
    """Get language from query param or cookie"""
    lang = request.query_params.get('lang')
    if lang and lang in ['en', 'de', 'pl']:
        return lang
    return request.cookies.get('lang', 'en')


def require_admin(request: Request, db: Session):
    """Check if user has admin/moderator access, redirect if not"""
    user = get_current_user_optional(request, db)
    if not user:
        return None, RedirectResponse(url="/login?next=/admin", status_code=303)
    # Allow admin and moderator roles
    if user.role not in ['admin', 'moderator']:
        return None, RedirectResponse(url="/dashboard?error=admin_required", status_code=303)
    return user, None


def require_full_admin(request: Request, db: Session):
    """Check if user is full admin (for user management), redirect if not"""
    user = get_current_user_optional(request, db)
    if not user:
        return None, RedirectResponse(url="/login?next=/admin", status_code=303)
    if user.role != 'admin':
        return None, RedirectResponse(url="/admin?error=admin_only", status_code=303)
    return user, None


# ============================================
# ADMIN DASHBOARD
# ============================================

@router.get("", response_class=HTMLResponse)
@router.get("/", response_class=HTMLResponse)
def admin_dashboard(request: Request, db: Session = Depends(get_db)):
    """Admin dashboard with overview statistics"""
    lang = get_lang(request)
    user, redirect = require_admin(request, db)
    if redirect:
        return redirect
    
    # Gather statistics
    stats = {
        'total_users': db.query(User).count(),
        'active_users': db.query(User).filter(User.is_active == True).count(),
        'admin_users': db.query(User).filter(User.role == 'admin').count(),
        
        'total_offerings': db.query(Offering).count(),
        'open_offerings': db.query(Offering).filter(Offering.status == 'open').count(),
        'threshold_met': db.query(Offering).filter(Offering.status == 'threshold_met').count(),
        'draft_offerings': db.query(Offering).filter(Offering.status == 'draft').count(),
        
        'total_registrations': db.query(Registration).count(),
        'total_contributions': db.query(Contribution).count(),
        
        # Contributions are held in each offering's own currency, so a
        # single total across all offerings would add unlike things. The
        # EUR figure below counts EUR offerings only; other currencies
        # are reported beside it, never merged into it.
        'total_contributed': (
            db.query(func.sum(Contribution.amount_eur))
              .join(Offering, Offering.id == Contribution.offering_id)
              .filter(Offering.currency == 'EUR').scalar() or Decimal('0')),
        'fund_balance': RegenerationFund.get_balance(db),
    }

    # Contribution totals for offerings in other currencies, listed
    # separately. Nothing here is converted into euro.
    stats['contributed_by_currency'] = [
        {'currency': c, 'total': tot}
        for c, tot in db.query(Offering.currency, func.sum(Contribution.amount_eur))
                        .join(Contribution, Contribution.offering_id == Offering.id)
                        .filter(Offering.currency != 'EUR')
                        .group_by(Offering.currency).all()
    ]

    # Solidarity financing (internal module). Counts and sums only — no
    # token, household or per-pledge figure reaches this overview, exactly
    # as on the module's own screens. UAH is reported as UAH and never
    # added to the EUR totals above: the two are separate currencies and
    # nothing here converts between them.
    from sqlalchemy import text as _sql
    try:
        _s = db.execute(_sql("""
            SELECT
              (SELECT COUNT(*) FROM solidarity.camp_session)                       AS sessions,
              (SELECT COUNT(DISTINCT initiative_id) FROM solidarity.camp_session
                WHERE initiative_id IS NOT NULL)                                    AS initiatives,
              (SELECT COUNT(*) FROM solidarity.camp_session WHERE offering_id IS NOT NULL) AS linked,
              (SELECT COUNT(*) FROM solidarity.bidding_round WHERE state = 'open') AS open_rounds,
              (SELECT COALESCE(SUM(amount_uah), 0) FROM solidarity.pledge)         AS pledged_uah
        """)).mappings().first()
        stats['solidarity'] = dict(_s) if _s else None
    except Exception:
        # Module not migrated on this instance — show nothing rather than fail.
        db.rollback()
        stats['solidarity'] = None
    
    # Recent activity
    recent_registrations = db.query(Registration).order_by(
        desc(Registration.registered_at)
    ).limit(5).all()
    
    recent_contributions = db.query(Contribution).order_by(
        desc(Contribution.contributed_at)
    ).limit(5).all()
    
    # Pending items
    pending_offerings = db.query(Offering).filter(
        Offering.status == 'draft'
    ).order_by(desc(Offering.created_at)).all()
    
    return templates.TemplateResponse(
        "admin/dashboard.html",
        {
            "request": request,
            "lang": lang,
            "user": user,
            "stats": stats,
            "recent_registrations": recent_registrations,
            "recent_contributions": recent_contributions,
            "pending_offerings": pending_offerings
        }
    )


# ============================================
# USER MANAGEMENT
# ============================================

@router.get("/users", response_class=HTMLResponse)
def admin_users(
    request: Request,
    page: int = 1,
    search: str = None,
    role: str = None,
    db: Session = Depends(get_db)
):
    """List all users with search and filter"""
    lang = get_lang(request)
    user, redirect = require_admin(request, db)
    if redirect:
        return redirect
    
    per_page = 20
    query = db.query(User)
    
    # Apply filters
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            (User.email.ilike(search_term)) | 
            (User.name.ilike(search_term))
        )
    
    if role:
        query = query.filter(User.role == role)
    
    # Count and paginate
    total = query.count()
    users = query.order_by(desc(User.created_at)).offset((page - 1) * per_page).limit(per_page).all()
    
    total_pages = (total + per_page - 1) // per_page
    
    return templates.TemplateResponse(
        "admin/users.html",
        {
            "request": request,
            "lang": lang,
            "user": user,
            "users": users,
            "page": page,
            "total_pages": total_pages,
            "total": total,
            "search": search or "",
            "role_filter": role or ""
        }
    )


@router.get("/users/{user_id}", response_class=HTMLResponse)
def admin_user_detail(
    user_id: str,
    request: Request,
    db: Session = Depends(get_db)
):
    """View/edit a specific user"""
    lang = get_lang(request)
    admin_user, redirect = require_full_admin(request, db)
    if redirect:
        return redirect
    
    target_user = db.query(User).filter(User.id == user_id).first()
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Get user's activity
    user_offerings = db.query(Offering).filter(
        Offering.creator_id == user_id
    ).order_by(desc(Offering.created_at)).all()
    
    # Get registrations by this user's email
    user_registrations = db.query(Registration).filter(
        Registration.email == target_user.email
    ).order_by(desc(Registration.registered_at)).all()
    
    return templates.TemplateResponse(
        "admin/user_detail.html",
        {
            "request": request,
            "lang": lang,
            "user": admin_user,
            "target_user": target_user,
            "user_offerings": user_offerings,
            "user_registrations": user_registrations
        }
    )


@router.post("/users/{user_id}/role")
def admin_set_role(
    user_id: str,
    request: Request,
    role: str = Form(...),
    db: Session = Depends(get_db)
):
    """Set role for a user"""
    admin_user, redirect = require_full_admin(request, db)
    if redirect:
        return redirect
    
    target_user = db.query(User).filter(User.id == user_id).first()
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Validate role
    valid_roles = ['member', 'creator', 'facilitator', 'moderator', 'admin']
    if role not in valid_roles:
        raise HTTPException(status_code=400, detail="Invalid role")
    
    # Prevent self-demotion from admin
    if target_user.id == admin_user.id and role != 'admin':
        return RedirectResponse(
            url=f"/admin/users/{user_id}?error=cannot_self_demote",
            status_code=303
        )
    
    target_user.role = role
    db.commit()
    
    return RedirectResponse(
        url=f"/admin/users/{user_id}?success=role_updated",
        status_code=303
    )


@router.post("/users/{user_id}/toggle-active")
def admin_toggle_active(
    user_id: str,
    request: Request,
    db: Session = Depends(get_db)
):
    """Toggle active status for a user"""
    admin_user, redirect = require_full_admin(request, db)
    if redirect:
        return redirect
    
    target_user = db.query(User).filter(User.id == user_id).first()
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Prevent self-deactivation
    if target_user.id == admin_user.id:
        return RedirectResponse(
            url=f"/admin/users/{user_id}?error=cannot_self_deactivate",
            status_code=303
        )
    
    target_user.is_active = not target_user.is_active
    db.commit()
    
    return RedirectResponse(
        url=f"/admin/users/{user_id}?success=status_updated",
        status_code=303
    )


@router.post("/users/{user_id}/update")
def admin_update_user(
    user_id: str,
    request: Request,
    name: str = Form(None),
    email: str = Form(...),
    db: Session = Depends(get_db)
):
    """Update user details"""
    admin_user, redirect = require_full_admin(request, db)
    if redirect:
        return redirect
    
    target_user = db.query(User).filter(User.id == user_id).first()
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Check email uniqueness
    if email.lower() != target_user.email:
        existing = db.query(User).filter(User.email == email.lower()).first()
        if existing:
            return RedirectResponse(
                url=f"/admin/users/{user_id}?error=email_exists",
                status_code=303
            )
    
    target_user.name = name or None
    target_user.email = email.lower()
    db.commit()
    
    return RedirectResponse(
        url=f"/admin/users/{user_id}?success=updated",
        status_code=303
    )


# ============================================
# REGISTRATIONS / PARTICIPANTS
# ============================================

@router.get("/registrations", response_class=HTMLResponse)
def admin_registrations(
    request: Request,
    page: int = 1,
    offering_id: str = None,
    search: str = None,
    db: Session = Depends(get_db)
):
    """List all registrations across offerings"""
    lang = get_lang(request)
    user, redirect = require_admin(request, db)
    if redirect:
        return redirect
    
    per_page = 25
    query = db.query(Registration)
    
    # Apply filters
    if offering_id:
        query = query.filter(Registration.offering_id == offering_id)
    
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            (Registration.email.ilike(search_term)) |
            (Registration.name.ilike(search_term))
        )
    
    # Count and paginate
    total = query.count()
    registrations = query.order_by(desc(Registration.registered_at)).offset((page - 1) * per_page).limit(per_page).all()
    
    total_pages = (total + per_page - 1) // per_page
    
    # Get offerings for filter dropdown
    offerings = db.query(Offering).order_by(desc(Offering.created_at)).all()
    
    return templates.TemplateResponse(
        "admin/registrations.html",
        {
            "request": request,
            "lang": lang,
            "user": user,
            "registrations": registrations,
            "offerings": offerings,
            "page": page,
            "total_pages": total_pages,
            "total": total,
            "offering_filter": offering_id or "",
            "search": search or ""
        }
    )


@router.post("/registrations/{registration_id}/delete")
def admin_delete_registration(
    registration_id: str,
    request: Request,
    db: Session = Depends(get_db)
):
    """Delete a registration"""
    user, redirect = require_admin(request, db)
    if redirect:
        return redirect
    
    registration = db.query(Registration).filter(Registration.id == registration_id).first()
    if not registration:
        raise HTTPException(status_code=404, detail="Registration not found")
    
    db.delete(registration)
    db.commit()
    
    return RedirectResponse(
        url="/admin/registrations?success=deleted",
        status_code=303
    )


# ============================================
# CONTRIBUTIONS / SUPPORTERS
# ============================================

@router.get("/contributions", response_class=HTMLResponse)
def admin_contributions(
    request: Request,
    page: int = 1,
    offering_id: str = None,
    contribution_type: str = None,
    status: str = None,
    db: Session = Depends(get_db)
):
    """List all contributions across offerings"""
    lang = get_lang(request)
    user, redirect = require_admin(request, db)
    if redirect:
        return redirect
    
    per_page = 25
    query = db.query(Contribution)
    
    # Apply filters
    if offering_id:
        query = query.filter(Contribution.offering_id == offering_id)
    
    if contribution_type:
        query = query.filter(Contribution.contribution_type == contribution_type)
    
    if status:
        query = query.filter(Contribution.status == status)
    
    # Count and paginate
    total = query.count()
    contributions = query.order_by(desc(Contribution.contributed_at)).offset((page - 1) * per_page).limit(per_page).all()
    
    total_pages = (total + per_page - 1) // per_page
    
    # Get offerings for filter dropdown
    offerings = db.query(Offering).order_by(desc(Offering.created_at)).all()
    
    # Summary stats
    total_eur = db.query(func.sum(Contribution.amount_eur)).scalar() or Decimal('0')
    
    return templates.TemplateResponse(
        "admin/contributions.html",
        {
            "request": request,
            "lang": lang,
            "user": user,
            "contributions": contributions,
            "offerings": offerings,
            "page": page,
            "total_pages": total_pages,
            "total": total,
            "total_eur": total_eur,
            "offering_filter": offering_id or "",
            "type_filter": contribution_type or "",
            "status_filter": status or ""
        }
    )


@router.get("/contributions/{contribution_id}", response_class=HTMLResponse)
def admin_contribution_detail(
    contribution_id: str,
    request: Request,
    db: Session = Depends(get_db)
):
    """View contribution details"""
    lang = get_lang(request)
    user, redirect = require_admin(request, db)
    if redirect:
        return redirect
    
    contribution = db.query(Contribution).filter(Contribution.id == contribution_id).first()
    if not contribution:
        raise HTTPException(status_code=404, detail="Contribution not found")
    
    # Get contact info if exists
    contact = db.query(ContributionContact).filter(
        ContributionContact.contribution_id == contribution_id
    ).first()
    
    return templates.TemplateResponse(
        "admin/contribution_detail.html",
        {
            "request": request,
            "lang": lang,
            "user": user,
            "contribution": contribution,
            "contact": contact
        }
    )


@router.post("/contributions/{contribution_id}/status")
def admin_update_contribution_status(
    contribution_id: str,
    request: Request,
    status: str = Form(...),
    db: Session = Depends(get_db)
):
    """Update contribution status"""
    user, redirect = require_admin(request, db)
    if redirect:
        return redirect
    
    contribution = db.query(Contribution).filter(Contribution.id == contribution_id).first()
    if not contribution:
        raise HTTPException(status_code=404, detail="Contribution not found")
    
    valid_statuses = ['pending', 'confirmed', 'cancelled', 'refunded']
    if status not in valid_statuses:
        raise HTTPException(status_code=400, detail="Invalid status")
    
    contribution.status = status
    db.commit()
    
    return RedirectResponse(
        url=f"/admin/contributions/{contribution_id}?success=updated",
        status_code=303
    )


# ============================================
# OFFERINGS MANAGEMENT
# ============================================

@router.get("/offerings", response_class=HTMLResponse)
def admin_offerings(
    request: Request,
    page: int = 1,
    status: str = None,
    db: Session = Depends(get_db)
):
    """List all offerings with admin controls"""
    lang = get_lang(request)
    user, redirect = require_admin(request, db)
    if redirect:
        return redirect
    
    per_page = 20
    query = db.query(Offering)
    
    if status:
        query = query.filter(Offering.status == status)
    
    total = query.count()
    offerings = query.order_by(desc(Offering.created_at)).offset((page - 1) * per_page).limit(per_page).all()
    
    # Add computed properties
    for o in offerings:
        o._total = o.get_total_contributed(db)
        o._reg_count = o.get_registration_count(db)
        o._percent = round((float(o._total) / float(o.threshold_amount)) * 100, 1) if o.threshold_amount else 0
    
    total_pages = (total + per_page - 1) // per_page
    
    return templates.TemplateResponse(
        "admin/offerings.html",
        {
            "request": request,
            "lang": lang,
            "user": user,
            "offerings": offerings,
            "page": page,
            "total_pages": total_pages,
            "total": total,
            "status_filter": status or ""
        }
    )


# ============================================
# SYSTEM SETTINGS
# ============================================

@router.get("/settings", response_class=HTMLResponse)
def admin_settings(
    request: Request,
    db: Session = Depends(get_db)
):
    """System settings page"""
    lang = get_lang(request)
    user, redirect = require_admin(request, db)
    if redirect:
        return redirect
    
    token_rate = TokenRate.get_current_rate(db)
    hours_rates = db.query(HoursRate).all()
    fund_balance = RegenerationFund.get_balance(db)
    
    return templates.TemplateResponse(
        "admin/settings.html",
        {
            "request": request,
            "lang": lang,
            "user": user,
            "token_rate": token_rate,
            "hours_rates": hours_rates,
            "fund_balance": fund_balance
        }
    )


@router.post("/settings/token-rate")
def admin_update_token_rate(
    request: Request,
    tokens_per_eur: float = Form(...),
    db: Session = Depends(get_db)
):
    """Update token exchange rate"""
    user, redirect = require_admin(request, db)
    if redirect:
        return redirect
    
    # Create new rate (historical tracking)
    new_rate = TokenRate(
        tokens_per_eur=Decimal(str(tokens_per_eur))
    )
    db.add(new_rate)
    db.commit()
    
    return RedirectResponse(
        url="/admin/settings?success=token_rate_updated",
        status_code=303
    )


@router.post("/settings/hours-rate")
def admin_update_hours_rate(
    request: Request,
    category: str = Form(...),
    eur_per_hour: float = Form(...),
    description: str = Form(None),
    description_de: str = Form(None),
    description_pl: str = Form(None),
    db: Session = Depends(get_db)
):
    """Update or create hours rate"""
    user, redirect = require_admin(request, db)
    if redirect:
        return redirect
    
    # Find or create
    rate = db.query(HoursRate).filter(HoursRate.category == category).first()
    if rate:
        rate.eur_per_hour = Decimal(str(eur_per_hour))
        rate.description = description
        if hasattr(rate, 'description_de'):
            rate.description_de = description_de
        if hasattr(rate, 'description_pl'):
            rate.description_pl = description_pl
    else:
        rate = HoursRate(
            category=category,
            eur_per_hour=Decimal(str(eur_per_hour)),
            description=description
        )
        if hasattr(rate, 'description_de'):
            rate.description_de = description_de
        if hasattr(rate, 'description_pl'):
            rate.description_pl = description_pl
        db.add(rate)
    
    db.commit()
    
    return RedirectResponse(
        url="/admin/settings?success=hours_rate_updated",
        status_code=303
    )


@router.post("/settings/hours-rate/{rate_id}/delete")
def admin_delete_hours_rate(
    rate_id: str,
    request: Request,
    db: Session = Depends(get_db)
):
    """Delete an hours rate"""
    user, redirect = require_admin(request, db)
    if redirect:
        return redirect
    
    rate = db.query(HoursRate).filter(HoursRate.id == rate_id).first()
    if rate:
        db.delete(rate)
        db.commit()
    
    return RedirectResponse(
        url="/admin/settings?success=hours_rate_deleted",
        status_code=303
    )


# ============================================
# REGENERATION FUND
# ============================================

@router.get("/fund", response_class=HTMLResponse)
def admin_fund(
    request: Request,
    db: Session = Depends(get_db)
):
    """Regeneration Fund management"""
    lang = get_lang(request)
    user, redirect = require_admin(request, db)
    if redirect:
        return redirect
    
    balance = RegenerationFund.get_balance(db)
    
    # Get recent transactions (would need FundTransaction model)
    # For now, show fund entries
    fund_entries = db.query(RegenerationFund).order_by(
        desc(RegenerationFund.created_at)
    ).limit(50).all()
    
    return templates.TemplateResponse(
        "admin/fund.html",
        {
            "request": request,
            "lang": lang,
            "user": user,
            "balance": balance,
            "fund_entries": fund_entries
        }
    )


@router.post("/fund/add")
def admin_fund_add(
    request: Request,
    amount: float = Form(...),
    transaction_type: str = Form(...),
    description: str = Form(None),
    offering_id: str = Form(None),
    db: Session = Depends(get_db)
):
    """Add a fund transaction"""
    user, redirect = require_admin(request, db)
    if redirect:
        return redirect
    
    entry = RegenerationFund(
        amount=Decimal(str(amount)),
        transaction_type=transaction_type,
        description=description,
        offering_id=offering_id if offering_id else None
    )
    db.add(entry)
    db.commit()
    
    return RedirectResponse(
        url="/admin/fund?success=added",
        status_code=303
    )


# ============================================
# INITIATIVES (network directory)
# ============================================

@router.get("/initiatives", response_class=HTMLResponse)
def admin_initiatives(request: Request, db: Session = Depends(get_db)):
    """Review queue: pending proposals to approve/reject + published initiatives.

    Initiatives are authored publicly at /initiatives/start; admins review here.
    """
    lang = get_lang(request)
    user, redirect = require_admin(request, db)
    if redirect:
        return redirect

    all_inits = get_initiatives(db)
    pending = [i for i in all_inits if not i.is_published]
    published = [i for i in all_inits if i.is_published]

    return templates.TemplateResponse(
        "admin/initiatives.html",
        {
            "request": request,
            "lang": lang,
            "user": user,
            "pending": pending,
            "published": published,
        }
    )


@router.post("/initiatives/{initiative_id}/publish")
def admin_initiative_publish(
    initiative_id: str,
    request: Request,
    db: Session = Depends(get_db)
):
    """Approve a proposal: publish it (shows on `/`) and create its data folder."""
    user, redirect = require_admin(request, db)
    if redirect:
        return redirect

    initiative = db.query(Initiative).filter(Initiative.id == initiative_id).first()
    if not initiative:
        return RedirectResponse(url="/admin/initiatives?error=not_found", status_code=303)

    initiative.is_published = True
    initiative.has_page = True   # give the approved initiative its own /{slug} page
    db.commit()

    # Create the external per-initiative folder (outside the repo tree) on
    # approval — not at proposal time — so rejected/spam proposals never write
    # to the filesystem. A folder hiccup must not undo the publish.
    folder_ok = True
    try:
        create_data_dir(slug=initiative.slug, name=initiative.name, status=initiative.status)
    except Exception as e:
        folder_ok = False
        logger.warning("initiative folder creation failed for %s: %s", initiative.slug, e)

    # Notify the proposer with the link to their new page (best-effort: no-ops
    # if they gave no email or SMTP is unconfigured; never breaks the publish).
    if initiative.submitter_email:
        try:
            from ..email import send_initiative_published
            send_initiative_published(initiative.submitter_email, initiative.name, initiative.slug)
        except Exception as e:
            logger.warning("initiative published-email failed for %s: %s", initiative.slug, e)

    success = "published" if folder_ok else "published_no_folder"
    return RedirectResponse(url=f"/admin/initiatives?success={success}", status_code=303)


@router.post("/initiatives/{initiative_id}/unpublish")
def admin_initiative_unpublish(
    initiative_id: str,
    request: Request,
    db: Session = Depends(get_db)
):
    """Take a published initiative back off the public directory (keeps the row)."""
    user, redirect = require_admin(request, db)
    if redirect:
        return redirect

    initiative = db.query(Initiative).filter(Initiative.id == initiative_id).first()
    if initiative and initiative.flagship:
        # Never unpublish the flagship reference implementation from the UI.
        return RedirectResponse(url="/admin/initiatives?error=flagship_protected", status_code=303)
    if initiative:
        initiative.is_published = False
        db.commit()
    return RedirectResponse(url="/admin/initiatives?success=unpublished", status_code=303)


@router.post("/initiatives/{initiative_id}/delete")
def admin_initiative_delete(
    initiative_id: str,
    request: Request,
    db: Session = Depends(get_db)
):
    """Delete an initiative row. Leaves the external data folder untouched."""
    user, redirect = require_admin(request, db)
    if redirect:
        return redirect

    initiative = db.query(Initiative).filter(Initiative.id == initiative_id).first()
    if initiative and initiative.flagship:
        # Never delete the flagship reference implementation from the dashboard.
        return RedirectResponse(
            url="/admin/initiatives?error=flagship_protected",
            status_code=303
        )
    if initiative:
        db.delete(initiative)
        db.commit()

    return RedirectResponse(
        url="/admin/initiatives?success=deleted",
        status_code=303
    )


# ============================================
# INITIATIVE MEMBERSHIP
# ============================================

@router.get("/initiatives/{initiative_id}/members", response_class=HTMLResponse)
def admin_initiative_members(initiative_id: str, request: Request,
                             db: Session = Depends(get_db)):
    """Who belongs to this initiative, and in what role."""
    user, redirect = require_admin(request, db)
    if redirect:
        return redirect
    from ..membership import members_of, MEMBERSHIP_ROLES
    init = db.execute(text("""SELECT id, slug, name, location
                              FROM erdpuls_threshold.initiatives WHERE id = :i"""),
                      {"i": initiative_id}).mappings().first()
    if not init:
        raise HTTPException(404)
    candidates = db.query(User).order_by(User.name, User.email).all()
    return templates.TemplateResponse("admin/initiative_members.html", {
        "request": request, "lang": get_lang(request), "user": user,
        "initiative": init, "members": members_of(db, initiative_id),
        "candidates": candidates, "membership_roles": MEMBERSHIP_ROLES,
        "error": request.query_params.get("error", ""),
    })


@router.post("/initiatives/{initiative_id}/members")
def admin_add_member(initiative_id: str, request: Request,
                     user_id: str = Form(...), role: str = Form("member"),
                     note: str = Form(""), db: Session = Depends(get_db)):
    """Add or change someone's membership of this initiative."""
    actor, redirect = require_admin(request, db)
    if redirect:
        return redirect
    from ..membership import MEMBERSHIP_ROLES
    if role not in MEMBERSHIP_ROLES:
        raise HTTPException(400)
    db.execute(text("""
        INSERT INTO erdpuls_threshold.initiative_members
            (initiative_id, user_id, role, added_by, note)
        VALUES (:i, :u, :r, :a, :n)
        ON CONFLICT (initiative_id, user_id)
        DO UPDATE SET role = EXCLUDED.role, note = EXCLUDED.note
    """), {"i": initiative_id, "u": user_id, "r": role,
           "a": str(actor.id), "n": note})
    db.commit()
    return RedirectResponse(url=f"/admin/initiatives/{initiative_id}/members",
                            status_code=303)


@router.post("/initiatives/{initiative_id}/members/{member_id}/remove")
def admin_remove_member(initiative_id: str, member_id: str, request: Request,
                        db: Session = Depends(get_db)):
    """Remove someone from this initiative.

    Removing membership does not touch their global role, and does not
    touch any financing record they took part in: what happened, happened.
    """
    actor, redirect = require_admin(request, db)
    if redirect:
        return redirect
    db.execute(text("""DELETE FROM erdpuls_threshold.initiative_members
                       WHERE id = :m AND initiative_id = :i"""),
               {"m": member_id, "i": initiative_id})
    db.commit()
    return RedirectResponse(url=f"/admin/initiatives/{initiative_id}/members",
                            status_code=303)

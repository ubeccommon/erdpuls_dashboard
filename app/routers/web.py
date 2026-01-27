"""
Erdpuls Collective Threshold Model - Web Routes
Updated with Participation Pathways Architecture

Three engagement pathways:
1. /offering/{id}/participate - Participate Only
2. /offering/{id}/contribute?pathway=support_only - Support Only  
3. /offering/{id}/contribute?pathway=support_and_participate - Support & Participate
"""
from datetime import datetime
from decimal import Decimal
from fastapi import APIRouter, Request, Depends, HTTPException, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import (
    Offering, Registration, Contribution, ContributionContact,
    TokenRate, HoursRate, EngagementType, RegistrationType
)
from ..email import send_contribution_confirmation

router = APIRouter()
templates = Jinja2Templates(directory="templates")


def get_lang(request: Request) -> str:
    """Get language from cookie or default to 'en'."""
    return request.cookies.get('lang', 'en')


def get_current_user_optional(request: Request, db: Session):
    """Get current user from session if logged in."""
    from ..models import User
    user_id = request.cookies.get('user_id')
    if user_id:
        return db.query(User).filter(User.id == user_id).first()
    return None


# ============================================
# STATIC PAGES
# ============================================

@router.get("/", response_class=HTMLResponse)
def home(request: Request, db: Session = Depends(get_db)):
    """Home page"""
    lang = get_lang(request)
    user = get_current_user_optional(request, db)
    
    offerings = db.query(Offering).filter(
        Offering.status.in_(['open', 'threshold_met'])
    ).order_by(Offering.event_date).limit(3).all()
    
    # Add computed properties
    for o in offerings:
        o._total = o.get_total_contributed(db)
        o._reg_count = o.get_registration_count(db)
        o._percent = round((float(o._total) / float(o.threshold_amount)) * 100, 1) if o.threshold_amount else 0
        o._threshold_reached = float(o._total) >= float(o.threshold_amount)
    
    from ..models import RegenerationFund
    fund_balance = RegenerationFund.get_balance(db)
    
    response = templates.TemplateResponse(
        "index.html",
        {
            "request": request, 
            "lang": lang, 
            "user": user, 
            "offerings": offerings,
            "fund_balance": fund_balance
        }
    )
    response.set_cookie("lang", lang, max_age=31536000)  # 1 year
    return response


@router.get("/about", response_class=HTMLResponse)
def about(request: Request, db: Session = Depends(get_db)):
    """About page"""
    lang = get_lang(request)
    user = get_current_user_optional(request, db)
    return templates.TemplateResponse(
        "about.html",
        {"request": request, "lang": lang, "user": user}
    )


@router.get("/model", response_class=HTMLResponse)
def model(request: Request, db: Session = Depends(get_db)):
    """Model overview page"""
    lang = get_lang(request)
    user = get_current_user_optional(request, db)
    return templates.TemplateResponse(
        "model.html",
        {"request": request, "lang": lang, "user": user}
    )


@router.get("/model/threshold", response_class=HTMLResponse)
def model_threshold(request: Request, db: Session = Depends(get_db)):
    """Threshold model page"""
    lang = get_lang(request)
    user = get_current_user_optional(request, db)
    return templates.TemplateResponse(
        "model_threshold.html",
        {"request": request, "lang": lang, "user": user}
    )


@router.get("/model/pathways", response_class=HTMLResponse)
def model_pathways(request: Request, db: Session = Depends(get_db)):
    """Participation pathways page"""
    lang = get_lang(request)
    user = get_current_user_optional(request, db)
    return templates.TemplateResponse(
        "model_pathways.html",
        {"request": request, "lang": lang, "user": user}
    )


@router.get("/privacy", response_class=HTMLResponse)
def privacy(request: Request, db: Session = Depends(get_db)):
    """Privacy policy page"""
    lang = get_lang(request)
    user = get_current_user_optional(request, db)
    return templates.TemplateResponse(
        "legal_privacy.html",
        {"request": request, "lang": lang, "user": user}
    )


@router.get("/fund", response_class=HTMLResponse)
def fund(request: Request, db: Session = Depends(get_db)):
    """Regeneration Fund page"""
    lang = get_lang(request)
    user = get_current_user_optional(request, db)
    
    from ..models import RegenerationFund
    balance = RegenerationFund.get_balance(db)
    
    return templates.TemplateResponse(
        "fund.html",
        {"request": request, "lang": lang, "user": user, "balance": balance}
    )


@router.get("/create-offering", response_class=HTMLResponse)
def create_offering_info(request: Request, db: Session = Depends(get_db)):
    """Info page about creating offerings - explains the process and roles"""
    lang = get_lang(request)
    user = get_current_user_optional(request, db)
    
    return templates.TemplateResponse(
        "create_offering.html",
        {"request": request, "lang": lang, "user": user}
    )


# ============================================
# LEGAL PAGES
# ============================================

@router.get("/legal/imprint", response_class=HTMLResponse)
def legal_imprint(request: Request, db: Session = Depends(get_db)):
    """Imprint / Impressum page"""
    lang = get_lang(request)
    user = get_current_user_optional(request, db)
    return templates.TemplateResponse(
        "legal_imprint.html",
        {"request": request, "lang": lang, "user": user}
    )


@router.get("/legal/privacy", response_class=HTMLResponse)
def legal_privacy(request: Request, db: Session = Depends(get_db)):
    """Privacy Policy / Datenschutzerklärung page"""
    lang = get_lang(request)
    user = get_current_user_optional(request, db)
    return templates.TemplateResponse(
        "legal_privacy.html",
        {"request": request, "lang": lang, "user": user}
    )


@router.get("/legal/terms", response_class=HTMLResponse)
def legal_terms(request: Request, db: Session = Depends(get_db)):
    """Terms of Service / Nutzungsbedingungen page"""
    lang = get_lang(request)
    user = get_current_user_optional(request, db)
    return templates.TemplateResponse(
        "legal_terms.html",
        {"request": request, "lang": lang, "user": user}
    )


# ============================================
# MODEL PAGES (additional)
# ============================================

@router.get("/model/tokens", response_class=HTMLResponse)
def model_tokens(request: Request, db: Session = Depends(get_db)):
    """UBECrc tokens model page"""
    lang = get_lang(request)
    user = get_current_user_optional(request, db)
    return templates.TemplateResponse(
        "model_tokens.html",
        {"request": request, "lang": lang, "user": user}
    )


@router.get("/model/reciprocity", response_class=HTMLResponse)
def model_reciprocity(request: Request, db: Session = Depends(get_db)):
    """Reciprocal economics model page"""
    lang = get_lang(request)
    user = get_current_user_optional(request, db)
    return templates.TemplateResponse(
        "model_reciprocity.html",
        {"request": request, "lang": lang, "user": user}
    )


# ============================================
# LANGUAGE SWITCHING
# ============================================

@router.get("/set-lang/{lang}")
def set_language(lang: str, request: Request):
    """Set language preference via cookie"""
    if lang not in ['en', 'de', 'pl']:
        lang = 'en'
    
    referer = request.headers.get('referer', '/')
    response = RedirectResponse(url=referer, status_code=303)
    response.set_cookie(key='lang', value=lang, max_age=365*24*60*60)
    return response


# ============================================
# OFFERINGS
# ============================================

@router.get("/offerings", response_class=HTMLResponse)
def offerings_list(request: Request, db: Session = Depends(get_db)):
    """List all open offerings"""
    lang = get_lang(request)
    user = get_current_user_optional(request, db)
    
    offerings = db.query(Offering).filter(
        Offering.status.in_(['open', 'threshold_met', 'confirmed'])
    ).order_by(Offering.event_date).all()
    
    # Add computed properties
    for o in offerings:
        o._total = o.get_total_contributed(db)
        o._percent = round((float(o._total) / float(o.threshold_amount)) * 100, 1) if o.threshold_amount else 0
        o._reg_count = o.get_registration_count(db)
    
    return templates.TemplateResponse(
        "offerings.html",
        {"request": request, "lang": lang, "user": user, "offerings": offerings}
    )


@router.get("/offering/{offering_id}", response_class=HTMLResponse)
def offering_detail(offering_id: str, request: Request, db: Session = Depends(get_db)):
    """Single offering detail page"""
    lang = get_lang(request)
    user = get_current_user_optional(request, db)
    
    offering = db.query(Offering).filter(Offering.id == offering_id).first()
    if not offering:
        raise HTTPException(status_code=404, detail="Offering not found")
    
    # Add computed properties
    offering._total = offering.get_total_contributed(db)
    offering._percent = round((float(offering._total) / float(offering.threshold_amount)) * 100, 1) if offering.threshold_amount else 0
    offering._reg_count = offering.get_registration_count(db)
    offering._remaining = max(Decimal('0'), offering.threshold_amount - offering._total)
    offering._engagement = offering.get_engagement_summary(db)
    
    return templates.TemplateResponse(
        "offering.html",
        {"request": request, "lang": lang, "user": user, "offering": offering}
    )


# ============================================
# ENGAGEMENT PATHWAY SELECTION
# ============================================

@router.get("/offering/{offering_id}/engage", response_class=HTMLResponse)
def engage_selection(offering_id: str, request: Request, db: Session = Depends(get_db)):
    """Engagement pathway selection page"""
    lang = get_lang(request)
    user = get_current_user_optional(request, db)
    
    offering = db.query(Offering).filter(Offering.id == offering_id).first()
    if not offering:
        raise HTTPException(status_code=404, detail="Offering not found")
    
    # Check if engagement is open
    now = datetime.utcnow()
    if offering.status not in ['open', 'threshold_met']:
        return RedirectResponse(
            url=f"/offering/{offering_id}?error=engagement_closed",
            status_code=303
        )
    
    # Add computed properties
    offering._total = offering.get_total_contributed(db)
    offering._percent = round((float(offering._total) / float(offering.threshold_amount)) * 100, 1) if offering.threshold_amount else 0
    offering._reg_count = offering.get_registration_count(db)
    
    return templates.TemplateResponse(
        "engage.html",
        {"request": request, "lang": lang, "user": user, "offering": offering}
    )


# ============================================
# PATHWAY 1: PARTICIPATE ONLY
# ============================================

@router.get("/offering/{offering_id}/participate", response_class=HTMLResponse)
def participate_page(offering_id: str, request: Request, db: Session = Depends(get_db)):
    """Participate-only registration page"""
    lang = get_lang(request)
    user = get_current_user_optional(request, db)
    
    offering = db.query(Offering).filter(Offering.id == offering_id).first()
    if not offering:
        raise HTTPException(status_code=404, detail="Offering not found")
    
    # Check if registration is open
    now = datetime.utcnow()
    if now >= offering.registration_deadline:
        return RedirectResponse(
            url=f"/offering/{offering_id}?error=registration_closed",
            status_code=303
        )
    
    return templates.TemplateResponse(
        "participate.html",
        {"request": request, "lang": lang, "user": user, "offering": offering}
    )


@router.post("/offering/{offering_id}/participate")
def participate_submit(
    offering_id: str,
    request: Request,
    email: str = Form(...),
    name: str = Form(None),
    referral: str = Form(None),
    db: Session = Depends(get_db)
):
    """Process participate-only registration"""
    lang = get_lang(request)
    
    offering = db.query(Offering).filter(Offering.id == offering_id).first()
    if not offering:
        raise HTTPException(status_code=404, detail="Offering not found")
    
    # Check deadline
    now = datetime.utcnow()
    if now >= offering.registration_deadline:
        return RedirectResponse(
            url=f"/offering/{offering_id}?error=registration_closed",
            status_code=303
        )
    
    # Check capacity
    if offering.max_participants:
        count = offering.get_registration_count(db)
        if count >= offering.max_participants:
            return RedirectResponse(
                url=f"/offering/{offering_id}?error=offering_full",
                status_code=303
            )
    
    # Check for existing registration
    existing = db.query(Registration).filter(
        Registration.offering_id == offering_id,
        Registration.email == email.lower()
    ).first()
    
    if existing:
        return RedirectResponse(
            url=f"/offering/{offering_id}?info=already_registered",
            status_code=303
        )
    
    # Create registration
    registration = Registration(
        offering_id=offering_id,
        email=email.lower(),
        name=name,
        referral_source=referral,
        registration_type=RegistrationType.PARTICIPATE_ONLY,
        status='registered'
    )
    
    db.add(registration)
    db.commit()
    
    # TODO: Send confirmation email
    
    return RedirectResponse(
        url=f"/offering/{offering_id}?success=registered",
        status_code=303
    )


# ============================================
# PATHWAYS 2 & 3: CONTRIBUTE (with/without participation)
# ============================================

@router.get("/offering/{offering_id}/contribute", response_class=HTMLResponse)
def contribute_page(
    offering_id: str, 
    request: Request, 
    pathway: str = 'support_only',
    db: Session = Depends(get_db)
):
    """Contribution page (handles both support_only and support_and_participate)"""
    lang = get_lang(request)
    user = get_current_user_optional(request, db)
    
    # Validate pathway
    if pathway not in ['support_only', 'support_and_participate']:
        pathway = 'support_only'
    
    offering = db.query(Offering).filter(Offering.id == offering_id).first()
    if not offering:
        raise HTTPException(status_code=404, detail="Offering not found")
    
    # Check if contributions are open
    now = datetime.utcnow()
    if offering.status not in ['open', 'threshold_met'] or now > offering.contribution_deadline:
        return RedirectResponse(
            url=f"/offering/{offering_id}?error=contributions_closed",
            status_code=303
        )
    
    # For support_and_participate, also check registration deadline
    if pathway == 'support_and_participate' and now >= offering.registration_deadline:
        return RedirectResponse(
            url=f"/offering/{offering_id}/contribute?pathway=support_only&info=registration_closed",
            status_code=303
        )
    
    # Add computed properties
    offering._total = offering.get_total_contributed(db)
    offering._percent = round((float(offering._total) / float(offering.threshold_amount)) * 100, 1) if offering.threshold_amount else 0
    offering._remaining = max(Decimal('0'), offering.threshold_amount - offering._total)
    offering._reg_count = offering.get_registration_count(db)
    
    hours_rates = db.query(HoursRate).all()
    token_rate = TokenRate.get_current_rate(db)
    
    return templates.TemplateResponse(
        "contribute.html",
        {
            "request": request,
            "lang": lang,
            "user": user,
            "offering": offering,
            "pathway": pathway,
            "hours_rates": hours_rates,
            "token_rate": token_rate
        }
    )


@router.post("/offering/{offering_id}/contribute/submit")
def contribute_submit(
    offering_id: str,
    request: Request,
    pathway: str = Form(...),
    contribution_type: str = Form(...),
    # Euro
    amount_eur: float = Form(None),
    # Token
    token_amount: float = Form(None),
    # Hours
    hours_category: str = Form(None),
    hours_amount: float = Form(None),
    hours_description: str = Form(None),
    # Contact
    contact_name: str = Form(None),
    contact_email: str = Form(None),
    contact_phone: str = Form(None),
    contact_notes: str = Form(None),
    referral: str = Form(None),
    db: Session = Depends(get_db)
):
    """Process contribution submission"""
    lang = get_lang(request)
    
    offering = db.query(Offering).filter(Offering.id == offering_id).first()
    if not offering:
        raise HTTPException(status_code=404, detail="Offering not found")
    
    # Validate pathway
    if pathway not in ['support_only', 'support_and_participate']:
        pathway = 'support_only'
    
    wants_to_participate = (pathway == 'support_and_participate')
    
    # For support_and_participate, contact info is required
    if wants_to_participate and (not contact_name or not contact_email):
        return RedirectResponse(
            url=f"/offering/{offering_id}/contribute?pathway={pathway}&error=contact_required",
            status_code=303
        )
    
    # Calculate EUR equivalent
    final_amount_eur = Decimal('0')
    token_rate = TokenRate.get_current_rate(db)
    
    if contribution_type == 'euro':
        if not amount_eur or amount_eur <= 0:
            return RedirectResponse(
                url=f"/offering/{offering_id}/contribute?pathway={pathway}&error=invalid_amount",
                status_code=303
            )
        final_amount_eur = Decimal(str(amount_eur))
    
    elif contribution_type == 'token':
        if not token_amount or token_amount <= 0:
            return RedirectResponse(
                url=f"/offering/{offering_id}/contribute?pathway={pathway}&error=invalid_amount",
                status_code=303
            )
        # Convert tokens to EUR
        final_amount_eur = Decimal(str(token_amount)) / token_rate.tokens_per_eur
    
    elif contribution_type == 'hours':
        if not hours_category or not hours_amount or hours_amount <= 0:
            return RedirectResponse(
                url=f"/offering/{offering_id}/contribute?pathway={pathway}&error=invalid_hours",
                status_code=303
            )
        # Get rate for category
        hours_rate = db.query(HoursRate).filter(HoursRate.category == hours_category).first()
        if not hours_rate:
            return RedirectResponse(
                url=f"/offering/{offering_id}/contribute?pathway={pathway}&error=invalid_category",
                status_code=303
            )
        final_amount_eur = Decimal(str(hours_amount)) * hours_rate.eur_per_hour
    
    # Create contribution
    contribution = Contribution(
        offering_id=offering_id,
        amount_eur=final_amount_eur,
        contribution_type=contribution_type,
        engagement_type=EngagementType.SUPPORT_AND_PARTICIPATE if wants_to_participate else EngagementType.SUPPORT_ONLY,
        wants_to_participate=wants_to_participate,
        status='pending'
    )
    
    # Add type-specific fields
    if contribution_type == 'token':
        contribution.token_amount = Decimal(str(token_amount))
    elif contribution_type == 'hours':
        contribution.hours_category = hours_category
        contribution.hours_amount = Decimal(str(hours_amount))
        contribution.hours_description = hours_description
        contribution.hours_equivalent_eur = final_amount_eur
    
    db.add(contribution)
    db.flush()  # Get contribution ID
    
    # Create contact record if provided
    if contact_name or contact_email:
        contact = ContributionContact(
            contribution_id=contribution.id,
            name=contact_name,
            email=contact_email.lower() if contact_email else None,
            phone=contact_phone,
            notes=contact_notes
        )
        db.add(contact)
    
    # For support_and_participate, create registration
    registration = None
    if wants_to_participate and contact_email:
        # Check for existing registration
        existing_reg = db.query(Registration).filter(
            Registration.offering_id == offering_id,
            Registration.email == contact_email.lower()
        ).first()
        
        if existing_reg:
            # Update existing registration to link to contribution
            existing_reg.linked_contribution_id = contribution.id
            existing_reg.registration_type = RegistrationType.LINKED_TO_CONTRIBUTION
            registration = existing_reg
        else:
            # Create new registration
            registration = Registration(
                offering_id=offering_id,
                email=contact_email.lower(),
                name=contact_name,
                referral_source=referral,
                registration_type=RegistrationType.LINKED_TO_CONTRIBUTION,
                linked_contribution_id=contribution.id,
                status='registered'
            )
            db.add(registration)
    
    db.commit()
    db.refresh(contribution)
    
    # Send confirmation email
    if contact_email:
        contribution_data = {
            'amount_eur': float(final_amount_eur),
            'contribution_type': contribution_type,
            'wants_to_participate': wants_to_participate,
            'email': contact_email
        }
        if contribution_type == 'token':
            contribution_data['token_amount'] = token_amount
        elif contribution_type == 'hours':
            contribution_data['hours_category'] = hours_category
            contribution_data['hours_amount'] = hours_amount
        
        send_contribution_confirmation(
            to_email=contact_email,
            to_name=contact_name,
            offering_title=offering.get_title(lang),
            offering_id=offering_id,
            contribution_data=contribution_data,
            lang=lang
        )
    
    # Redirect to confirmation page
    return RedirectResponse(
        url=f"/offering/{offering_id}/contribute/confirm?id={contribution.id}",
        status_code=303
    )


@router.get("/offering/{offering_id}/contribute/confirm", response_class=HTMLResponse)
def contribute_confirm(
    offering_id: str,
    request: Request,
    id: str = None,
    db: Session = Depends(get_db)
):
    """Contribution confirmation page"""
    lang = get_lang(request)
    user = get_current_user_optional(request, db)
    
    offering = db.query(Offering).filter(Offering.id == offering_id).first()
    if not offering:
        raise HTTPException(status_code=404, detail="Offering not found")
    
    contribution = None
    if id:
        contribution = db.query(Contribution).filter(Contribution.id == id).first()
    
    # Add computed properties
    offering._total = offering.get_total_contributed(db)
    offering._percent = round((float(offering._total) / float(offering.threshold_amount)) * 100, 1) if offering.threshold_amount else 0
    
    return templates.TemplateResponse(
        "contribute_confirm.html",
        {
            "request": request,
            "lang": lang,
            "user": user,
            "offering": offering,
            "contribution": contribution
        }
    )


# ============================================
# LEGACY ROUTES (for backward compatibility)
# ============================================

@router.post("/offering/{offering_id}/register")
def register_legacy(
    offering_id: str,
    request: Request,
    email: str = Form(...),
    name: str = Form(None),
    referral: str = Form(None),
    db: Session = Depends(get_db)
):
    """Legacy registration route - redirects to new participate flow"""
    return participate_submit(
        offering_id=offering_id,
        request=request,
        email=email,
        name=name,
        referral=referral,
        db=db
    )

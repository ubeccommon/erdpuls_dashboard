"""
Erdpuls Collective Threshold Model - Web Router (HTML Pages)
"""
from datetime import datetime
from decimal import Decimal
from typing import Optional
import logging

from fastapi import APIRouter, Depends, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import (
    Offering, Registration, Contribution, ContributionContact,
    RegenerationFund, TokenRate, HoursRate
)
from ..auth import get_current_user_optional
from ..email import send_contribution_confirmation

logger = logging.getLogger(__name__)

router = APIRouter(tags=["web"])
templates = Jinja2Templates(directory="templates")


def get_lang(request: Request) -> str:
    """Get language from query param or cookie"""
    lang = request.query_params.get('lang')
    if lang and lang in ['en', 'de', 'pl']:
        return lang
    return request.cookies.get('lang', 'en')


# ============================================
# Pages
# ============================================

@router.get("/", response_class=HTMLResponse)
def index(request: Request, db: Session = Depends(get_db)):
    """Homepage - list all open offerings"""
    lang = get_lang(request)
    user = get_current_user_optional(request, db)
    
    offerings = db.query(Offering).filter(
        Offering.status.in_(['open', 'threshold_met'])
    ).order_by(Offering.event_date).all()
    
    # Add computed properties
    for o in offerings:
        o._total = o.get_total_contributed(db)
        o._reg_count = o.get_registration_count(db)
        o._percent = round((float(o._total) / float(o.threshold_amount)) * 100, 1) if o.threshold_amount else 0
        o._threshold_reached = float(o._total) >= float(o.threshold_amount)
    
    fund_balance = RegenerationFund.get_balance(db)
    
    response = templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "offerings": offerings,
            "fund_balance": fund_balance,
            "lang": lang,
            "user": user
        }
    )
    response.set_cookie("lang", lang, max_age=31536000)  # 1 year
    return response


@router.get("/offering/{offering_id}", response_class=HTMLResponse)
def offering_detail(offering_id: str, request: Request, db: Session = Depends(get_db)):
    """Offering detail page with contribution form"""
    lang = get_lang(request)
    user = get_current_user_optional(request, db)
    
    offering = db.query(Offering).filter(Offering.id == offering_id).first()
    if not offering:
        raise HTTPException(status_code=404, detail="Offering not found")
    
    # Add computed properties
    offering._total = offering.get_total_contributed(db)
    offering._reg_count = offering.get_registration_count(db)
    offering._percent = round((float(offering._total) / float(offering.threshold_amount)) * 100, 1)
    offering._threshold_reached = float(offering._total) >= float(offering.threshold_amount)
    offering._remaining = max(Decimal('0'), offering.threshold_amount - offering._total)
    
    now = datetime.utcnow()
    offering._registration_open = (
        offering.status in ['open', 'threshold_met'] and
        now < offering.registration_deadline and
        (offering.max_participants is None or offering._reg_count < offering.max_participants)
    )
    offering._contribution_open = (
        offering.status in ['open', 'threshold_met'] and
        now < offering.contribution_deadline
    )
    
    hours_rates = db.query(HoursRate).all()
    token_rate = TokenRate.get_current_rate(db)
    
    response = templates.TemplateResponse(
        "offering.html",
        {
            "request": request,
            "offering": offering,
            "hours_rates": hours_rates,
            "token_rate": token_rate,
            "lang": lang,
            "user": user
        }
    )
    response.set_cookie("lang", lang, max_age=31536000)
    return response


@router.get("/fund", response_class=HTMLResponse)
def regeneration_fund(request: Request, db: Session = Depends(get_db)):
    """Regeneration Fund page"""
    lang = get_lang(request)
    user = get_current_user_optional(request, db)
    
    balance = RegenerationFund.get_balance(db)
    transactions = db.query(RegenerationFund)\
        .order_by(RegenerationFund.created_at.desc())\
        .limit(50).all()
    
    return templates.TemplateResponse(
        "fund.html",
        {
            "request": request,
            "balance": balance,
            "transactions": transactions,
            "lang": lang,
            "user": user
        }
    )


@router.get("/about", response_class=HTMLResponse)
def about(request: Request, db: Session = Depends(get_db)):
    """About the Collective Threshold Model"""
    lang = get_lang(request)
    user = get_current_user_optional(request, db)
    return templates.TemplateResponse(
        "about.html", 
        {
            "request": request, 
            "lang": lang,
            "user": user
        }
    )


@router.get("/offerings", response_class=HTMLResponse)
def offerings_page(request: Request, db: Session = Depends(get_db)):
    """Offerings page - list all open offerings"""
    lang = get_lang(request)
    user = get_current_user_optional(request, db)
    
    offerings = db.query(Offering).filter(
        Offering.status.in_(['open', 'threshold_met'])
    ).order_by(Offering.event_date).all()
    
    # Add computed properties
    for o in offerings:
        o._total = o.get_total_contributed(db)
        o._reg_count = o.get_registration_count(db)
        o._percent = round((float(o._total) / float(o.threshold_amount)) * 100, 1) if o.threshold_amount else 0
        o._threshold_reached = float(o._total) >= float(o.threshold_amount)
    
    response = templates.TemplateResponse(
        "offerings.html",
        {
            "request": request,
            "offerings": offerings,
            "lang": lang,
            "user": user
        }
    )
    response.set_cookie("lang", lang, max_age=31536000)
    return response


@router.get("/model", response_class=HTMLResponse)
def model_redirect(request: Request):
    """Redirect /model to /model/reciprocity"""
    return RedirectResponse(url="/model/reciprocity", status_code=302)


@router.get("/model/threshold", response_class=HTMLResponse)
def model_threshold(request: Request, db: Session = Depends(get_db)):
    """Collective Threshold Model page"""
    lang = get_lang(request)
    user = get_current_user_optional(request, db)
    return templates.TemplateResponse(
        "model_threshold.html", 
        {
            "request": request, 
            "lang": lang,
            "user": user
        }
    )


@router.get("/model/pathways", response_class=HTMLResponse)
def model_pathways(request: Request, db: Session = Depends(get_db)):
    """Four Pathways page"""
    lang = get_lang(request)
    user = get_current_user_optional(request, db)
    return templates.TemplateResponse(
        "model_pathways.html", 
        {
            "request": request, 
            "lang": lang,
            "user": user
        }
    )


@router.get("/model/tokens", response_class=HTMLResponse)
def model_tokens(request: Request, db: Session = Depends(get_db)):
    """Token Economy page"""
    lang = get_lang(request)
    user = get_current_user_optional(request, db)
    return templates.TemplateResponse(
        "model_tokens.html", 
        {
            "request": request, 
            "lang": lang,
            "user": user
        }
    )


@router.get("/model/reciprocity", response_class=HTMLResponse)
def model_reciprocity(request: Request, db: Session = Depends(get_db)):
    """Reciprocal Economics philosophy page"""
    lang = get_lang(request)
    user = get_current_user_optional(request, db)
    return templates.TemplateResponse(
        "model_reciprocity.html", 
        {
            "request": request, 
            "lang": lang,
            "user": user
        }
    )


# ============================================
# Legal Pages
# ============================================

@router.get("/legal/imprint", response_class=HTMLResponse)
def legal_imprint(request: Request, db: Session = Depends(get_db)):
    """Imprint / Impressum page"""
    lang = get_lang(request)
    user = get_current_user_optional(request, db)
    return templates.TemplateResponse(
        "legal_imprint.html", 
        {
            "request": request, 
            "lang": lang,
            "user": user
        }
    )


@router.get("/legal/privacy", response_class=HTMLResponse)
def legal_privacy(request: Request, db: Session = Depends(get_db)):
    """Privacy Policy / Datenschutzerklärung page"""
    lang = get_lang(request)
    user = get_current_user_optional(request, db)
    return templates.TemplateResponse(
        "legal_privacy.html", 
        {
            "request": request, 
            "lang": lang,
            "user": user
        }
    )


@router.get("/legal/terms", response_class=HTMLResponse)
def legal_terms(request: Request, db: Session = Depends(get_db)):
    """Terms of Service / Nutzungsbedingungen page"""
    lang = get_lang(request)
    user = get_current_user_optional(request, db)
    return templates.TemplateResponse(
        "legal_terms.html", 
        {
            "request": request, 
            "lang": lang,
            "user": user
        }
    )


# ============================================
# Form Handlers
# ============================================

@router.post("/offering/{offering_id}/register")
def register(
    offering_id: str,
    request: Request,
    email: str = Form(...),
    name: str = Form(None),
    referral: str = Form(None),
    db: Session = Depends(get_db)
):
    """Register intention to participate"""
    offering = db.query(Offering).filter(Offering.id == offering_id).first()
    if not offering:
        raise HTTPException(status_code=404, detail="Offering not found")
    
    now = datetime.utcnow()
    if now >= offering.registration_deadline:
        return RedirectResponse(
            url=f"/offering/{offering_id}?error=registration_closed",
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
    
    registration = Registration(
        offering_id=offering_id,
        email=email.lower(),
        name=name,
        referral_source=referral
    )
    
    db.add(registration)
    db.commit()
    
    return RedirectResponse(
        url=f"/offering/{offering_id}?success=registered",
        status_code=303
    )


# ============================================
# NEW CONTRIBUTION FLOW (Multi-step)
# ============================================

@router.get("/offering/{offering_id}/contribute", response_class=HTMLResponse)
def contribute_page(offering_id: str, request: Request, db: Session = Depends(get_db)):
    """Contribution form page"""
    lang = get_lang(request)
    user = get_current_user_optional(request, db)
    
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
    
    # Add computed properties
    offering._total = offering.get_total_contributed(db)
    offering._percent = round((float(offering._total) / float(offering.threshold_amount)) * 100, 1) if offering.threshold_amount else 0
    offering._remaining = max(Decimal('0'), offering.threshold_amount - offering._total)
    
    hours_rates = db.query(HoursRate).all()
    token_rate = TokenRate.get_current_rate(db)
    
    return templates.TemplateResponse(
        "contribute.html",
        {
            "request": request,
            "offering": offering,
            "hours_rates": hours_rates,
            "token_rate": token_rate,
            "lang": lang,
            "user": user
        }
    )


@router.get("/offering/{offering_id}/contribute/confirm")
def contribute_confirm_get(offering_id: str, request: Request):
    """Redirect GET requests to the contribute page (confirmation requires POST data)"""
    return RedirectResponse(
        url=f"/offering/{offering_id}/contribute",
        status_code=303
    )


@router.post("/offering/{offering_id}/contribute/confirm", response_class=HTMLResponse)
def contribute_confirm(
    offering_id: str,
    request: Request,
    contact_name: Optional[str] = Form(None),
    contact_email: Optional[str] = Form(None),
    include_euro: Optional[str] = Form(None),
    euro_amount: Optional[str] = Form(None),
    include_tokens: Optional[str] = Form(None),
    token_amount: Optional[str] = Form(None),
    include_hours: Optional[str] = Form(None),
    hours_amount: Optional[str] = Form(None),
    hours_category: Optional[str] = Form(None),
    hours_description: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    """Confirmation page showing contribution summary"""
    lang = get_lang(request)
    user = get_current_user_optional(request, db)
    
    offering = db.query(Offering).filter(Offering.id == offering_id).first()
    if not offering:
        raise HTTPException(status_code=404, detail="Offering not found")
    
    # Helper to parse float from form
    def parse_float(val):
        if val and val.strip():
            try:
                return float(val)
            except ValueError:
                return None
        return None
    
    # Build contribution data
    contribution_data = {
        'name': contact_name.strip() if contact_name else None,
        'email': contact_email.strip() if contact_email else None,
        'euro': None,
        'tokens': None,
        'tokens_eur': None,
        'hours': None,
        'hours_category': None,
        'hours_description': None,
        'hours_eur': None,
        'total_eur': Decimal('0')
    }
    
    # Process Euro contribution
    euro_val = parse_float(euro_amount)
    if include_euro and euro_val and euro_val > 0:
        contribution_data['euro'] = euro_val
        contribution_data['total_eur'] += Decimal(str(euro_val))
    
    # Process Token contribution
    token_val = parse_float(token_amount)
    if include_tokens and token_val and token_val > 0:
        token_eur = TokenRate.tokens_to_eur(token_val, db)
        contribution_data['tokens'] = token_val
        contribution_data['tokens_eur'] = float(token_eur)
        contribution_data['total_eur'] += token_eur
    
    # Process Hours contribution
    hours_val = parse_float(hours_amount)
    if include_hours and hours_val and hours_val > 0 and hours_category:
        hours_eur = HoursRate.hours_to_eur(hours_val, hours_category, db)
        contribution_data['hours'] = hours_val
        contribution_data['hours_category'] = hours_category
        contribution_data['hours_description'] = hours_description.strip() if hours_description else None
        contribution_data['hours_eur'] = float(hours_eur)
        contribution_data['total_eur'] += hours_eur
    
    # Check if at least one contribution was made
    if contribution_data['total_eur'] <= 0:
        return RedirectResponse(
            url=f"/offering/{offering_id}/contribute?error=empty",
            status_code=303
        )
    
    return templates.TemplateResponse(
        "contribute_confirm.html",
        {
            "request": request,
            "offering": offering,
            "contribution_data": contribution_data,
            "lang": lang,
            "user": user
        }
    )


@router.get("/offering/{offering_id}/contribute/submit")
def contribute_submit_get(offering_id: str, request: Request):
    """Redirect GET requests to the contribute page"""
    return RedirectResponse(
        url=f"/offering/{offering_id}/contribute",
        status_code=303
    )


@router.post("/offering/{offering_id}/contribute/submit", response_class=HTMLResponse)
def contribute_submit(
    offering_id: str,
    request: Request,
    euro: Optional[str] = Form(None),
    tokens: Optional[str] = Form(None),
    hours: Optional[str] = Form(None),
    hours_category: Optional[str] = Form(None),
    hours_description: Optional[str] = Form(None),
    name: Optional[str] = Form(None),
    email: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    """Process the contribution and show thank you page"""
    lang = get_lang(request)
    user = get_current_user_optional(request, db)
    
    offering = db.query(Offering).filter(Offering.id == offering_id).first()
    if not offering:
        raise HTTPException(status_code=404, detail="Offering not found")
    
    # Check if contributions are still open
    now = datetime.utcnow()
    if offering.status not in ['open', 'threshold_met'] or now > offering.contribution_deadline:
        return RedirectResponse(
            url=f"/offering/{offering_id}?error=contributions_closed",
            status_code=303
        )
    
    # Track if threshold was already reached before this contribution
    old_total = offering.get_total_contributed(db)
    was_threshold_reached = float(old_total) >= float(offering.threshold_amount)
    
    contribution_data = {
        'euro': None,
        'tokens': None,
        'tokens_eur': None,
        'hours': None,
        'hours_category': None,
        'hours_description': None,
        'hours_eur': None,
        'total_eur': Decimal('0')
    }
    
    # Track created contributions for linking contact info
    created_contributions = []
    
    # Create Euro contribution
    if euro and euro.strip() and float(euro) > 0:
        try:
            amount = float(euro)
            contribution_data['euro'] = amount
            contribution_data['total_eur'] += Decimal(str(amount))
            
            contribution = Contribution(
                offering_id=offering_id,
                amount_eur=Decimal(str(amount)),
                contribution_type='euro',
                status='pending'
            )
            db.add(contribution)
            db.flush()  # Get ID
            created_contributions.append(contribution)
        except ValueError:
            pass
    
    # Create Token contribution
    if tokens and tokens.strip() and float(tokens) > 0:
        try:
            token_amount = float(tokens)
            token_eur = TokenRate.tokens_to_eur(token_amount, db)
            contribution_data['tokens'] = token_amount
            contribution_data['tokens_eur'] = float(token_eur)
            contribution_data['total_eur'] += token_eur
            
            contribution = Contribution(
                offering_id=offering_id,
                amount_eur=token_eur,
                contribution_type='token',
                token_amount=Decimal(str(token_amount)),
                status='pending'
            )
            db.add(contribution)
            db.flush()
            created_contributions.append(contribution)
        except ValueError:
            pass
    
    # Create Hours contribution
    if hours and hours.strip() and float(hours) > 0 and hours_category:
        try:
            hours_val = float(hours)
            hours_eur = HoursRate.hours_to_eur(hours_val, hours_category, db)
            contribution_data['hours'] = hours_val
            contribution_data['hours_category'] = hours_category
            contribution_data['hours_description'] = hours_description
            contribution_data['hours_eur'] = float(hours_eur)
            contribution_data['total_eur'] += hours_eur
            
            contribution = Contribution(
                offering_id=offering_id,
                amount_eur=hours_eur,
                contribution_type='hours',
                hours_category=hours_category,
                hours_amount=Decimal(str(hours_val)),
                hours_description=hours_description or '',
                hours_equivalent_eur=hours_eur,
                status='pending'
            )
            db.add(contribution)
            db.flush()
            created_contributions.append(contribution)
        except ValueError:
            pass
    
    # Create ContributionContact records if contact info provided
    # This links identity to contribution for operational purposes only
    contact_name = name.strip() if name else None
    contact_email = email.strip() if email else None
    
    # DEBUG - using print to ensure visibility
    print(f"DEBUG contribute_submit: name param = '{name}', email param = '{email}'")
    print(f"DEBUG contribute_submit: contact_name = '{contact_name}', contact_email = '{contact_email}'")
    
    if contact_name or contact_email:
        for contrib in created_contributions:
            contact = ContributionContact(
                contribution_id=contrib.id,
                name=contact_name,
                email=contact_email,
                notes=hours_description if contrib.contribution_type == 'hours' else None
            )
            db.add(contact)
    
    # Check if threshold is now met
    new_total = offering.get_total_contributed(db)
    threshold_reached = float(new_total) >= float(offering.threshold_amount)
    threshold_just_reached = threshold_reached and not was_threshold_reached
    
    if threshold_reached and offering.status == 'open':
        offering.status = 'threshold_met'
    
    db.commit()
    
    # Send confirmation email if contact email provided
    print(f"DEBUG: About to check if should send email. contact_email = '{contact_email}'")
    if contact_email:
        print(f"DEBUG: Sending email to {contact_email}")
        try:
            result = send_contribution_confirmation(
                to_email=contact_email,
                to_name=contact_name,
                offering_title=offering.get_title(lang),
                offering_id=offering.id,
                contribution_data=contribution_data,
                lang=lang
            )
            print(f"DEBUG: Email function returned: {result}")
        except Exception as e:
            # Log error but don't fail the contribution
            print(f"DEBUG: Failed to send confirmation email: {e}")
            logger.error(f"Failed to send confirmation email: {e}")
    else:
        print("DEBUG: No contact_email provided, skipping email")
    
    # Calculate new progress
    new_percent = round((float(new_total) / float(offering.threshold_amount)) * 100, 1) if offering.threshold_amount else 0
    new_remaining = max(Decimal('0'), offering.threshold_amount - new_total)
    
    return templates.TemplateResponse(
        "contribute_thankyou.html",
        {
            "request": request,
            "offering": offering,
            "contribution_data": contribution_data,
            "new_total": new_total,
            "new_percent": new_percent,
            "new_remaining": new_remaining,
            "threshold_reached": threshold_reached,
            "threshold_just_reached": threshold_just_reached,
            "lang": lang,
            "user": user
        }
    )


"""
Erdpuls Collective Threshold Model - API Router

© 2026 Michel Garand | Lizenz: CC BY-NC-SA 4.0 | https://creativecommons.org/licenses/by-nc-sa/4.0/deed.de
"""
from datetime import datetime
from decimal import Decimal
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import (
    Offering, Registration, Contribution, 
    RegenerationFund, TokenRate, HoursRate
)
from ..schemas import (
    OfferingCreate, OfferingResponse, OfferingProgress,
    RegistrationCreate, RegistrationResponse,
    ContributionEuro, ContributionToken, ContributionHours, ContributionResponse,
    FundBalance, FundTransaction,
    TokenRateResponse, HoursRateResponse
)
from ..auth import get_current_user_optional, refresh_session_cookie

router = APIRouter(prefix="/api", tags=["api"])


# ============================================
# Session Management
# ============================================

@router.post("/session/refresh")
def refresh_session(
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Refresh the user's session cookie.
    Called by the frontend session-timeout.js to extend session on user activity.
    """
    user = get_current_user_optional(request, db)
    
    if not user:
        return JSONResponse(
            status_code=401,
            content={"detail": "Not authenticated"}
        )
    
    response = JSONResponse(content={"status": "ok", "user_id": str(user.id)})
    refresh_session_cookie(response, user.id)
    return response


# ============================================
# Offerings
# ============================================

@router.get("/offerings", response_model=List[OfferingResponse])
def list_offerings(lang: str = "en", db: Session = Depends(get_db)):
    """Get all open offerings"""
    offerings = db.query(Offering).filter(
        Offering.status.in_(['open', 'threshold_met'])
    ).order_by(Offering.event_date).all()
    
    return [_offering_to_response(o, lang, db) for o in offerings]


@router.get("/offerings/{offering_id}", response_model=OfferingResponse)
def get_offering(offering_id: str, lang: str = "en", db: Session = Depends(get_db)):
    """Get offering details"""
    offering = db.query(Offering).filter(Offering.id == offering_id).first()
    if not offering:
        raise HTTPException(status_code=404, detail="Offering not found")
    
    return _offering_to_response(offering, lang, db)


@router.get("/offerings/{offering_id}/progress", response_model=OfferingProgress)
def get_offering_progress(offering_id: str, db: Session = Depends(get_db)):
    """Get offering progress (aggregate only - preserves anonymity)"""
    offering = db.query(Offering).filter(Offering.id == offering_id).first()
    if not offering:
        raise HTTPException(status_code=404, detail="Offering not found")
    
    total = offering.get_total_contributed(db)
    threshold = float(offering.threshold_amount)
    percent = round((float(total) / threshold) * 100, 1) if threshold > 0 else 0
    
    return OfferingProgress(
        total_contributed=float(total),
        threshold_amount=threshold,
        percent_funded=percent,
        threshold_reached=float(total) >= threshold,
        amount_remaining=max(0, threshold - float(total)),
        registration_count=offering.get_registration_count(db),
        status=offering.status
    )


@router.post("/offerings", response_model=OfferingResponse, status_code=status.HTTP_201_CREATED)
def create_offering(data: OfferingCreate, db: Session = Depends(get_db)):
    """Create a new offering"""
    offering = Offering(
        title=data.title,
        title_de=data.title_de,
        title_pl=data.title_pl,
        description=data.description,
        description_de=data.description_de,
        description_pl=data.description_pl,
        delivery_language=data.delivery_language or ['de'],
        threshold_amount=data.threshold_amount,
        facilitator_cost=data.facilitator_cost,
        materials_cost=data.materials_cost,
        meals_cost=data.meals_cost,
        space_cost=data.space_cost,
        sustainability_contribution=data.sustainability_contribution,
        event_date=data.event_date,
        registration_deadline=data.registration_deadline,
        contribution_deadline=data.contribution_deadline,
        min_participants=data.min_participants,
        max_participants=data.max_participants,
        status='open'
    )
    
    db.add(offering)
    db.commit()
    db.refresh(offering)
    
    return _offering_to_response(offering, "en", db)


# ============================================
# Registrations
# ============================================

@router.post("/offerings/{offering_id}/register", response_model=RegistrationResponse)
def register_for_offering(
    offering_id: str, 
    data: RegistrationCreate, 
    db: Session = Depends(get_db)
):
    """Register intention to participate"""
    offering = db.query(Offering).filter(Offering.id == offering_id).first()
    if not offering:
        raise HTTPException(status_code=404, detail="Offering not found")
    
    # Check if registration is open
    now = datetime.utcnow()
    if now >= offering.registration_deadline:
        raise HTTPException(status_code=400, detail="Registration is closed")
    
    if offering.max_participants:
        count = offering.get_registration_count(db)
        if count >= offering.max_participants:
            raise HTTPException(status_code=400, detail="Offering is full")
    
    # Check for existing registration
    existing = db.query(Registration).filter(
        Registration.offering_id == offering_id,
        Registration.email == data.email.lower()
    ).first()
    
    if existing:
        raise HTTPException(status_code=400, detail="Already registered")
    
    registration = Registration(
        offering_id=offering_id,
        email=data.email.lower(),
        name=data.name,
        referral_source=data.referral_source
    )
    
    db.add(registration)
    db.commit()
    db.refresh(registration)
    
    return registration


# ============================================
# Contributions (ANONYMOUS)
# ============================================

@router.post("/offerings/{offering_id}/contribute/euro", response_model=ContributionResponse)
def contribute_euro(
    offering_id: str,
    data: ContributionEuro,
    db: Session = Depends(get_db)
):
    """Make an anonymous euro contribution"""
    return _process_contribution(
        offering_id=offering_id,
        amount_eur=data.amount,
        contribution_type='euro',
        db=db
    )


@router.post("/offerings/{offering_id}/contribute/token", response_model=ContributionResponse)
def contribute_token(
    offering_id: str,
    data: ContributionToken,
    db: Session = Depends(get_db)
):
    """Make an anonymous token contribution"""
    amount_eur = TokenRate.tokens_to_eur(float(data.tokens), db)
    
    return _process_contribution(
        offering_id=offering_id,
        amount_eur=amount_eur,
        contribution_type='token',
        token_amount=data.tokens,
        db=db
    )


@router.post("/offerings/{offering_id}/contribute/hours", response_model=ContributionResponse)
def contribute_hours(
    offering_id: str,
    data: ContributionHours,
    db: Session = Depends(get_db)
):
    """Make an anonymous hours contribution"""
    amount_eur = HoursRate.hours_to_eur(float(data.hours), data.category, db)
    
    return _process_contribution(
        offering_id=offering_id,
        amount_eur=amount_eur,
        contribution_type='hours',
        hours_description=f"{data.category}: {data.description or ''}",
        db=db
    )


def _process_contribution(
    offering_id: str,
    amount_eur: Decimal,
    contribution_type: str,
    db: Session,
    token_amount: Decimal = None,
    hours_description: str = None
) -> ContributionResponse:
    """Process a contribution (internal helper)"""
    offering = db.query(Offering).filter(Offering.id == offering_id).first()
    if not offering:
        raise HTTPException(status_code=404, detail="Offering not found")
    
    if not offering.is_open:
        raise HTTPException(status_code=400, detail="Contributions are closed")
    
    contribution = Contribution(
        offering_id=offering_id,
        amount_eur=amount_eur,
        contribution_type=contribution_type,
        token_amount=token_amount,
        hours_description=hours_description
    )
    
    db.add(contribution)
    db.flush()
    
    # Check if threshold is now met
    total = offering.get_total_contributed(db)
    if total >= offering.threshold_amount and offering.status == 'open':
        offering.status = 'threshold_met'
    
    db.commit()
    
    return ContributionResponse(
        success=True,
        message="Thank you for your contribution to the collective pot!"
    )


# ============================================
# Regeneration Fund
# ============================================

@router.get("/fund/balance", response_model=FundBalance)
def get_fund_balance(db: Session = Depends(get_db)):
    """Get Regeneration Fund balance"""
    return FundBalance(balance=float(RegenerationFund.get_balance(db)))


@router.get("/fund/transactions", response_model=List[FundTransaction])
def get_fund_transactions(limit: int = 50, db: Session = Depends(get_db)):
    """Get recent fund transactions"""
    transactions = db.query(RegenerationFund)\
        .order_by(RegenerationFund.created_at.desc())\
        .limit(limit).all()
    return transactions


# ============================================
# Rates
# ============================================

@router.get("/rates/tokens", response_model=TokenRateResponse)
def get_token_rate(db: Session = Depends(get_db)):
    """Get current token exchange rate"""
    return TokenRateResponse(tokens_per_eur=TokenRate.get_current_rate(db))


@router.get("/rates/hours", response_model=List[HoursRateResponse])
def get_hours_rates(db: Session = Depends(get_db)):
    """Get hours contribution rates"""
    return db.query(HoursRate).all()


# ============================================
# Admin
# ============================================

@router.post("/admin/offerings/{offering_id}/confirm")
def confirm_offering(offering_id: str, db: Session = Depends(get_db)):
    """Confirm an offering and process any surplus"""
    offering = db.query(Offering).filter(Offering.id == offering_id).first()
    if not offering:
        raise HTTPException(status_code=404, detail="Offering not found")
    
    total = offering.get_total_contributed(db)
    if total < offering.threshold_amount:
        raise HTTPException(status_code=400, detail="Threshold not yet reached")
    
    # Process surplus to Regeneration Fund
    surplus = float(total) - float(offering.threshold_amount)
    if surplus > 0:
        fund_entry = RegenerationFund(
            amount=Decimal(str(surplus)),
            transaction_type='surplus_in',
            offering_id=offering_id,
            description=f'Surplus from "{offering.title}"'
        )
        db.add(fund_entry)
    
    offering.status = 'confirmed'
    db.commit()
    
    return {"status": "confirmed", "surplus_to_fund": surplus}


# ============================================
# Helper Functions
# ============================================

def _offering_to_response(offering: Offering, lang: str, db: Session) -> OfferingResponse:
    """Convert Offering model to response schema"""
    total = offering.get_total_contributed(db)
    threshold = float(offering.threshold_amount)
    percent = round((float(total) / threshold) * 100, 1) if threshold > 0 else 0
    now = datetime.utcnow()
    reg_count = offering.get_registration_count(db)
    
    return OfferingResponse(
        id=offering.id,
        title=offering.get_title(lang),
        description=offering.get_description(lang),
        delivery_language=offering.delivery_language or ['de'],
        threshold_amount=threshold,
        cost_breakdown=CostBreakdown(
            facilitator=float(offering.facilitator_cost or 0),
            materials=float(offering.materials_cost or 0),
            meals=float(offering.meals_cost or 0),
            space=float(offering.space_cost or 0),
            sustainability=float(offering.sustainability_contribution or 0)
        ),
        total_contributed=float(total),
        percent_funded=percent,
        threshold_reached=float(total) >= threshold,
        amount_remaining=max(0, threshold - float(total)),
        registration_count=reg_count,
        max_participants=offering.max_participants,
        event_date=offering.event_date,
        registration_deadline=offering.registration_deadline,
        contribution_deadline=offering.contribution_deadline,
        status=offering.status,
        is_open=offering.is_open,
        registration_open=(
            offering.status in ['open', 'threshold_met'] and
            now < offering.registration_deadline and
            (offering.max_participants is None or reg_count < offering.max_participants)
        )
    )


# Import CostBreakdown for helper function
from ..schemas import CostBreakdown

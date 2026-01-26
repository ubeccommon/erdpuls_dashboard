"""
Erdpuls Collective Threshold Model - Pydantic Schemas
"""
from datetime import datetime
from decimal import Decimal
from typing import Optional, List
from pydantic import BaseModel, EmailStr, Field


# ============================================
# Offering Schemas
# ============================================

class CostBreakdown(BaseModel):
    facilitator: float = 0
    materials: float = 0
    meals: float = 0
    space: float = 0
    sustainability: float = 0


class OfferingBase(BaseModel):
    title: str
    title_de: Optional[str] = None
    title_pl: Optional[str] = None
    description: str
    description_de: Optional[str] = None
    description_pl: Optional[str] = None
    threshold_amount: Decimal
    facilitator_cost: Decimal = Decimal('0')
    materials_cost: Decimal = Decimal('0')
    meals_cost: Decimal = Decimal('0')
    space_cost: Decimal = Decimal('0')
    sustainability_contribution: Decimal = Decimal('0')
    event_date: Optional[datetime] = None
    registration_deadline: datetime
    contribution_deadline: datetime
    min_participants: int = 1
    max_participants: Optional[int] = None


class OfferingCreate(OfferingBase):
    pass


class OfferingResponse(BaseModel):
    id: str
    title: str
    description: str
    threshold_amount: float
    cost_breakdown: CostBreakdown
    total_contributed: float
    percent_funded: float
    threshold_reached: bool
    amount_remaining: float
    registration_count: int
    max_participants: Optional[int]
    event_date: Optional[datetime]
    registration_deadline: datetime
    contribution_deadline: datetime
    status: str
    is_open: bool
    registration_open: bool

    class Config:
        from_attributes = True


class OfferingProgress(BaseModel):
    total_contributed: float
    threshold_amount: float
    percent_funded: float
    threshold_reached: bool
    amount_remaining: float
    registration_count: int
    status: str


# ============================================
# Registration Schemas
# ============================================

class RegistrationCreate(BaseModel):
    email: EmailStr
    name: Optional[str] = None
    referral_source: Optional[str] = None


class RegistrationResponse(BaseModel):
    id: str
    offering_id: str
    name: Optional[str]
    status: str
    registered_at: datetime

    class Config:
        from_attributes = True


# ============================================
# Contribution Schemas
# ============================================

class ContributionEuro(BaseModel):
    amount: Decimal = Field(gt=0)


class ContributionToken(BaseModel):
    tokens: Decimal = Field(gt=0)


class ContributionHours(BaseModel):
    hours: Decimal = Field(gt=0)
    category: str
    description: Optional[str] = None


class ContributionResponse(BaseModel):
    success: bool
    message: str


# ============================================
# Regeneration Fund Schemas
# ============================================

class FundBalance(BaseModel):
    balance: float


class FundTransaction(BaseModel):
    id: str
    amount: float
    transaction_type: str
    description: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


# ============================================
# Rate Schemas
# ============================================

class TokenRateResponse(BaseModel):
    tokens_per_eur: float
    description: str = "UBECrc tokens per 1 EUR"


class HoursRateResponse(BaseModel):
    category: str
    eur_per_hour: float
    description: Optional[str]

    class Config:
        from_attributes = True

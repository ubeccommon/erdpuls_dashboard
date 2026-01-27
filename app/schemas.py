"""
Erdpuls Collective Threshold Model - Pydantic Schemas
Complete schema file including:
- Original API schemas (for api.py router)
- New Participation Pathways schemas (for web.py router)
"""
from datetime import datetime
from decimal import Decimal
from typing import Optional, List, Literal
from pydantic import BaseModel, EmailStr, Field


# ============================================
# ENGAGEMENT TYPE LITERALS (New)
# ============================================

EngagementTypeLiteral = Literal['support_only', 'support_and_participate']
RegistrationTypeLiteral = Literal['participate_only', 'linked_to_contribution']
ContributionTypeLiteral = Literal['euro', 'token', 'hours']


# ============================================
# Offering Schemas (Original API)
# ============================================

class CostBreakdown(BaseModel):
    """Cost breakdown for offering transparency"""
    facilitator: float = 0
    materials: float = 0
    meals: float = 0
    space: float = 0
    sustainability: float = 0


class OfferingBase(BaseModel):
    """Base schema for offerings"""
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
    """Schema for creating a new offering"""
    pass


class OfferingResponse(BaseModel):
    """Response schema for offerings (API)"""
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
    """Schema for offering progress (public aggregates only)"""
    total_contributed: float
    threshold_amount: float
    percent_funded: float
    threshold_reached: bool
    amount_remaining: float
    registration_count: int
    status: str


class OfferingEngagementSummary(BaseModel):
    """Schema for detailed engagement summary (organizer view)"""
    offering_id: str
    participate_only: int
    support_only: int
    support_and_participate: int
    total_participants: int
    total_supporters: int
    total_engaged: int


# ============================================
# Registration Schemas
# ============================================

class RegistrationCreate(BaseModel):
    """Schema for creating a registration (participate-only or API)"""
    email: EmailStr
    name: Optional[str] = None
    referral_source: Optional[str] = None


class RegistrationResponse(BaseModel):
    """Response schema for registrations"""
    id: str
    offering_id: str
    email: str
    name: Optional[str]
    status: str
    registered_at: datetime
    # New fields for participation pathways
    registration_type: Optional[str] = None
    linked_contribution_id: Optional[str] = None

    class Config:
        from_attributes = True


# ============================================
# Contribution Schemas (Original API)
# ============================================

class ContributionEuro(BaseModel):
    """Schema for Euro contributions (API)"""
    amount: Decimal = Field(gt=0)


class ContributionToken(BaseModel):
    """Schema for token contributions (API)"""
    tokens: Decimal = Field(gt=0)


class ContributionHours(BaseModel):
    """Schema for hours contributions (API)"""
    hours: Decimal = Field(gt=0)
    category: str
    description: Optional[str] = None


class ContributionResponse(BaseModel):
    """Response schema for contributions (API)"""
    success: bool
    message: str


# ============================================
# Contribution Schemas (New Web Pathways)
# ============================================

class ContributionBase(BaseModel):
    """Base schema for web contribution forms"""
    wants_to_participate: bool = False
    
    # Contact info (optional for support_only, required for support_and_participate)
    contact_name: Optional[str] = None
    contact_email: Optional[EmailStr] = None
    contact_phone: Optional[str] = None
    contact_notes: Optional[str] = None


class ContributionEuroWeb(ContributionBase):
    """Schema for Euro contributions via web form"""
    amount: Decimal = Field(..., gt=0, description="Amount in EUR")


class ContributionTokenWeb(ContributionBase):
    """Schema for token contributions via web form"""
    token_amount: Decimal = Field(..., gt=0, description="Number of UBECrc tokens")


class ContributionHoursWeb(ContributionBase):
    """Schema for hours contributions via web form"""
    hours_amount: Decimal = Field(..., gt=0, le=100, description="Number of hours")
    hours_category: str = Field(..., description="Category of work")
    hours_description: Optional[str] = None


class ContributionWebResponse(BaseModel):
    """Response schema for web contributions"""
    id: str
    offering_id: str
    amount_eur: Decimal
    contribution_type: str
    engagement_type: str
    wants_to_participate: bool
    status: str
    contributed_at: datetime
    
    # Only included if contact was provided
    has_contact: bool = False
    
    # Only included if registration was created
    registration_created: bool = False
    registration_id: Optional[str] = None

    class Config:
        from_attributes = True


# ============================================
# Unified Engagement Schemas (New)
# ============================================

class EngagementChoice(BaseModel):
    """Schema for initial engagement pathway selection"""
    pathway: Literal['participate_only', 'contribute_only', 'contribute_and_participate']


class ParticipateOnlyRequest(BaseModel):
    """Schema for participate-only flow"""
    email: EmailStr
    name: Optional[str] = None
    referral_source: Optional[str] = None


class ContributeOnlyRequest(BaseModel):
    """Schema for contribute-only flow (support without participating)"""
    contribution_type: ContributionTypeLiteral
    
    # For euro contributions
    amount_eur: Optional[Decimal] = None
    
    # For token contributions
    token_amount: Optional[Decimal] = None
    
    # For hours contributions
    hours_amount: Optional[Decimal] = None
    hours_category: Optional[str] = None
    hours_description: Optional[str] = None
    
    # Optional contact info (for receipts, coordination)
    contact_name: Optional[str] = None
    contact_email: Optional[EmailStr] = None
    contact_phone: Optional[str] = None
    contact_notes: Optional[str] = None


class ContributeAndParticipateRequest(BaseModel):
    """Schema for contribute-and-participate flow (combined)"""
    contribution_type: ContributionTypeLiteral
    
    # For euro contributions
    amount_eur: Optional[Decimal] = None
    
    # For token contributions
    token_amount: Optional[Decimal] = None
    
    # For hours contributions
    hours_amount: Optional[Decimal] = None
    hours_category: Optional[str] = None
    hours_description: Optional[str] = None
    
    # Required contact info for participation
    name: str
    email: EmailStr
    phone: Optional[str] = None
    notes: Optional[str] = None
    referral_source: Optional[str] = None


# ============================================
# Regeneration Fund Schemas
# ============================================

class FundBalance(BaseModel):
    """Schema for Regeneration Fund balance"""
    balance: float
    last_updated: Optional[datetime] = None


class FundTransaction(BaseModel):
    """Schema for fund transactions"""
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
    """Schema for token exchange rate"""
    tokens_per_eur: float
    description: str = "UBECrc tokens per 1 EUR"
    effective_from: Optional[datetime] = None
    effective_until: Optional[datetime] = None

    class Config:
        from_attributes = True


class HoursRateResponse(BaseModel):
    """Schema for hours contribution rate"""
    category: str
    eur_per_hour: float
    description: Optional[str]

    class Config:
        from_attributes = True

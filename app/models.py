"""
Erdpuls Collective Threshold Model - Database Models
Updated with Participation Pathways Architecture

Three engagement pathways:
1. Participate Only - Register intention without contributing
2. Contribute Only - Support financially without participating  
3. Contribute & Participate - Both contribute and participate (linked)
"""
from datetime import datetime
from decimal import Decimal
from sqlalchemy import (
    Column, String, Boolean, Integer, DateTime, Text, 
    Numeric, ForeignKey, UniqueConstraint, func
)
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.orm import relationship, Session
import uuid

from .database import Base

# Schema name
SCHEMA = "erdpuls_threshold"


def generate_uuid():
    return str(uuid.uuid4())


# ============================================
# ENGAGEMENT TYPE CONSTANTS
# ============================================

class EngagementType:
    """Constants for engagement pathway types"""
    SUPPORT_ONLY = 'support_only'
    SUPPORT_AND_PARTICIPATE = 'support_and_participate'
    
    @classmethod
    def choices(cls):
        return [cls.SUPPORT_ONLY, cls.SUPPORT_AND_PARTICIPATE]


class RegistrationType:
    """Constants for registration pathway types"""
    PARTICIPATE_ONLY = 'participate_only'
    LINKED_TO_CONTRIBUTION = 'linked_to_contribution'
    
    @classmethod
    def choices(cls):
        return [cls.PARTICIPATE_ONLY, cls.LINKED_TO_CONTRIBUTION]


# ============================================
# USER MODEL
# ============================================

class User(Base):
    """User accounts for authentication."""
    __tablename__ = 'users'
    __table_args__ = {'schema': SCHEMA}
    
    id = Column(UUID(as_uuid=False), primary_key=True, default=generate_uuid)
    email = Column(String(255), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    name = Column(String(255))
    role = Column(String(50), default='user')  # 'user' or 'admin'
    is_active = Column(Boolean, default=True)
    email_verified = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_login = Column(DateTime)
    
    # Relationships
    offerings = relationship("Offering", back_populates="creator")
    
    @property
    def is_admin(self) -> bool:
        return self.role == 'admin'


# ============================================
# OFFERING MODEL
# ============================================

class Offering(Base):
    """Workshops, courses, events with threshold-based funding."""
    __tablename__ = 'offerings'
    __table_args__ = {'schema': SCHEMA}
    
    id = Column(UUID(as_uuid=False), primary_key=True, default=generate_uuid)
    
    # Multilingual content
    title = Column(String(255), nullable=False)
    title_de = Column(String(255))
    title_pl = Column(String(255))
    description = Column(Text, nullable=False)
    description_de = Column(Text)
    description_pl = Column(Text)
    
    # Delivery language(s) - which language(s) the offering is conducted in
    delivery_language = Column(ARRAY(String(50)), default=['de'])
    
    # Threshold and financial breakdown
    threshold_amount = Column(Numeric(10, 2), nullable=False)
    facilitator_cost = Column(Numeric(10, 2), default=0)
    materials_cost = Column(Numeric(10, 2), default=0)
    meals_cost = Column(Numeric(10, 2), default=0)
    space_cost = Column(Numeric(10, 2), default=0)
    sustainability_contribution = Column(Numeric(10, 2), default=0)
    
    # Dates
    event_date = Column(DateTime)
    registration_deadline = Column(DateTime, nullable=False)
    contribution_deadline = Column(DateTime, nullable=False)
    
    # Status: draft, open, threshold_met, confirmed, completed, cancelled
    status = Column(String(50), default='open')
    
    # Capacity
    min_participants = Column(Integer, default=1)
    max_participants = Column(Integer)
    
    # Organizer contact information
    organizer_name = Column(String(255))
    organizer_email = Column(String(255))
    organizer_phone = Column(String(50))
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = Column(String(255))
    creator_id = Column(UUID(as_uuid=False), ForeignKey(f'{SCHEMA}.users.id'))
    
    # Relationships
    creator = relationship("User", back_populates="offerings")
    registrations = relationship("Registration", back_populates="offering", lazy="dynamic")
    contributions = relationship("Contribution", back_populates="offering", lazy="dynamic")
    
    def get_title(self, lang: str = 'en') -> str:
        if lang == 'de' and self.title_de:
            return self.title_de
        elif lang == 'pl' and self.title_pl:
            return self.title_pl
        return self.title
    
    def get_description(self, lang: str = 'en') -> str:
        if lang == 'de' and self.description_de:
            return self.description_de
        elif lang == 'pl' and self.description_pl:
            return self.description_pl
        return self.description
    
    def get_delivery_language_display(self, lang: str = 'en') -> str:
        """Get formatted delivery language(s) for display."""
        lang_names = {
            'de': {'en': 'German', 'de': 'Deutsch', 'pl': 'Niemiecki'},
            'en': {'en': 'English', 'de': 'Englisch', 'pl': 'Angielski'},
            'pl': {'en': 'Polish', 'de': 'Polnisch', 'pl': 'Polski'}
        }
        
        if not self.delivery_language:
            return lang_names['de'].get(lang, 'German')
        
        display_names = []
        for dl in self.delivery_language:
            if dl in lang_names:
                display_names.append(lang_names[dl].get(lang, dl))
        
        return ', '.join(display_names) if display_names else lang_names['de'].get(lang, 'German')
    
    def get_total_contributed(self, db: Session) -> Decimal:
        result = db.query(func.coalesce(func.sum(Contribution.amount_eur), 0))\
            .filter(Contribution.offering_id == self.id).scalar()
        return Decimal(str(result)) if result else Decimal('0')
    
    def get_registration_count(self, db: Session) -> int:
        """Count all registrations (both participate-only and linked)."""
        return db.query(Registration)\
            .filter(Registration.offering_id == self.id)\
            .filter(Registration.status != 'cancelled').count()
    
    def get_participant_count(self, db: Session) -> int:
        """Count unique participants (registrations + contributors who want to participate)."""
        # Get direct registrations
        reg_count = db.query(Registration)\
            .filter(Registration.offering_id == self.id)\
            .filter(Registration.status != 'cancelled').count()
        return reg_count
    
    def get_supporter_only_count(self, db: Session) -> int:
        """Count contributors who only support (don't participate)."""
        return db.query(Contribution)\
            .filter(Contribution.offering_id == self.id)\
            .filter(Contribution.engagement_type == EngagementType.SUPPORT_ONLY).count()
    
    def get_engagement_summary(self, db: Session) -> dict:
        """Get summary of all engagement types."""
        participate_only = db.query(Registration)\
            .filter(Registration.offering_id == self.id)\
            .filter(Registration.registration_type == RegistrationType.PARTICIPATE_ONLY)\
            .filter(Registration.status != 'cancelled').count()
        
        support_only = db.query(Contribution)\
            .filter(Contribution.offering_id == self.id)\
            .filter(Contribution.engagement_type == EngagementType.SUPPORT_ONLY).count()
        
        support_and_participate = db.query(Contribution)\
            .filter(Contribution.offering_id == self.id)\
            .filter(Contribution.engagement_type == EngagementType.SUPPORT_AND_PARTICIPATE).count()
        
        return {
            'participate_only': participate_only,
            'support_only': support_only,
            'support_and_participate': support_and_participate,
            'total_participants': participate_only + support_and_participate,
            'total_supporters': support_only + support_and_participate,
            'total_engaged': participate_only + support_only + support_and_participate
        }
    
    @property
    def is_open(self) -> bool:
        now = datetime.utcnow()
        return self.status == 'open' and now < self.contribution_deadline


# ============================================
# REGISTRATION MODEL (Participation Intent)
# ============================================

class Registration(Base):
    """
    Registration of intention to participate.
    
    Registration Types:
    - participate_only: Register without contributing
    - linked_to_contribution: Registration created from "Contribute & Participate" flow
    """
    __tablename__ = 'registrations'
    __table_args__ = (
        UniqueConstraint('offering_id', 'email', name='unique_registration'),
        {'schema': SCHEMA}
    )
    
    id = Column(UUID(as_uuid=False), primary_key=True, default=generate_uuid)
    offering_id = Column(UUID(as_uuid=False), ForeignKey(f'{SCHEMA}.offerings.id'), nullable=False)
    
    # Contact info
    email = Column(String(255), nullable=False)
    name = Column(String(255))
    referral_source = Column(String(255))
    
    # Registration pathway
    registration_type = Column(String(50), default=RegistrationType.PARTICIPATE_ONLY)
    linked_contribution_id = Column(UUID(as_uuid=False), ForeignKey(f'{SCHEMA}.contributions.id', ondelete='SET NULL'))
    
    # Status: registered, confirmed, cancelled, attended
    status = Column(String(50), default='registered')
    registered_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    offering = relationship("Offering", back_populates="registrations")
    linked_contribution = relationship("Contribution", back_populates="linked_registration", foreign_keys=[linked_contribution_id])
    
    @property
    def is_participate_only(self) -> bool:
        return self.registration_type == RegistrationType.PARTICIPATE_ONLY
    
    @property
    def is_linked_to_contribution(self) -> bool:
        return self.registration_type == RegistrationType.LINKED_TO_CONTRIBUTION


# ============================================
# CONTRIBUTION MODEL
# ============================================

class Contribution(Base):
    """
    Contributions to offerings with engagement pathway tracking.
    
    Engagement Types:
    - support_only: Contribute financially without participating
    - support_and_participate: Contribute AND register for participation
    
    Identity stored SEPARATELY in ContributionContact for operational needs.
    Public visibility: aggregates only. Organizer visibility: linked for coordination.
    """
    __tablename__ = 'contributions'
    __table_args__ = {'schema': SCHEMA}
    
    id = Column(UUID(as_uuid=False), primary_key=True, default=generate_uuid)
    offering_id = Column(UUID(as_uuid=False), ForeignKey(f'{SCHEMA}.offerings.id'), nullable=False)
    
    # Financial details
    amount_eur = Column(Numeric(10, 2), nullable=False)
    contribution_type = Column(String(50), default='euro')  # euro, token, hours
    token_amount = Column(Numeric(15, 2))
    hours_category = Column(String(100))
    hours_amount = Column(Numeric(5, 2))
    hours_description = Column(Text)
    hours_equivalent_eur = Column(Numeric(10, 2))
    
    # Engagement pathway
    engagement_type = Column(String(50), default=EngagementType.SUPPORT_ONLY)
    wants_to_participate = Column(Boolean, default=False)
    
    # Status tracking
    # euro: pending -> confirmed (payment received)
    # token: pending -> confirmed (tokens transferred)
    # hours: pending -> scheduled -> completed
    status = Column(String(50), default='pending')
    
    contributed_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    offering = relationship("Offering", back_populates="contributions")
    contact = relationship("ContributionContact", back_populates="contribution", uselist=False)
    linked_registration = relationship("Registration", back_populates="linked_contribution", 
                                       foreign_keys="Registration.linked_contribution_id", uselist=False)
    
    @property
    def is_support_only(self) -> bool:
        return self.engagement_type == EngagementType.SUPPORT_ONLY
    
    @property
    def is_support_and_participate(self) -> bool:
        return self.engagement_type == EngagementType.SUPPORT_AND_PARTICIPATE


# ============================================
# CONTRIBUTION CONTACT MODEL
# ============================================

class ContributionContact(Base):
    """
    Contact information for contribution coordination.
    SEPARATED from contribution record to maintain conceptual anonymity.
    Only visible to organizers for operational purposes.
    """
    __tablename__ = 'contribution_contacts'
    __table_args__ = {'schema': SCHEMA}
    
    id = Column(UUID(as_uuid=False), primary_key=True, default=generate_uuid)
    contribution_id = Column(UUID(as_uuid=False), ForeignKey(f'{SCHEMA}.contributions.id'), nullable=False)
    
    name = Column(String(255))
    email = Column(String(255))
    phone = Column(String(50))
    notes = Column(Text)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationship
    contribution = relationship("Contribution", back_populates="contact")


# ============================================
# REGENERATION FUND MODEL
# ============================================

class RegenerationFund(Base):
    """Community reserve from surplus contributions."""
    __tablename__ = 'regeneration_fund'
    __table_args__ = {'schema': SCHEMA}
    
    id = Column(UUID(as_uuid=False), primary_key=True, default=generate_uuid)
    amount = Column(Numeric(10, 2), nullable=False)
    transaction_type = Column(String(50), nullable=False)  # surplus_in, shortfall_cover, seed_offering, adjustment
    offering_id = Column(UUID(as_uuid=False), ForeignKey(f'{SCHEMA}.offerings.id'))
    description = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    @classmethod
    def get_balance(cls, db: Session) -> Decimal:
        result = db.query(func.coalesce(func.sum(cls.amount), 0)).scalar()
        return Decimal(str(result)) if result else Decimal('0')


# ============================================
# TOKEN RATE MODEL
# ============================================

class TokenRate(Base):
    """Exchange rates for UBECrc tokens to EUR."""
    __tablename__ = 'token_rates'
    __table_args__ = {'schema': SCHEMA}
    
    id = Column(UUID(as_uuid=False), primary_key=True, default=generate_uuid)
    tokens_per_eur = Column(Numeric(15, 4), default=70.0, nullable=False)
    effective_from = Column(DateTime, default=datetime.utcnow)
    effective_until = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    @classmethod
    def get_current_rate(cls, db: Session) -> 'TokenRate':
        now = datetime.utcnow()
        rate = db.query(cls).filter(
            cls.effective_from <= now,
            (cls.effective_until.is_(None)) | (cls.effective_until > now)
        ).order_by(cls.effective_from.desc()).first()
        
        if not rate:
            # Return default rate
            return cls(tokens_per_eur=Decimal('70.0'))
        return rate
    
    @classmethod
    def tokens_to_eur(cls, tokens: float, db: Session) -> Decimal:
        """Convert tokens to EUR equivalent."""
        rate = cls.get_current_rate(db)
        return Decimal(str(tokens)) / rate.tokens_per_eur


# ============================================
# HOURS RATE MODEL
# ============================================

class HoursRate(Base):
    """Valuation rates for different types of contribution hours."""
    __tablename__ = 'hours_rates'
    __table_args__ = {'schema': SCHEMA}
    
    id = Column(UUID(as_uuid=False), primary_key=True, default=generate_uuid)
    category = Column(String(100), unique=True, nullable=False)
    eur_per_hour = Column(Numeric(10, 2), nullable=False)
    description = Column(Text)
    description_de = Column(Text)
    description_pl = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    def get_description(self, lang: str = 'en') -> str:
        if lang == 'de' and self.description_de:
            return self.description_de
        elif lang == 'pl' and self.description_pl:
            return self.description_pl
        return self.description or ''
    
    @classmethod
    def hours_to_eur(cls, hours: float, category: str, db: Session) -> Decimal:
        """Convert hours to EUR equivalent based on category rate."""
        rate = db.query(cls).filter(cls.category == category).first()
        if not rate:
            # Default to garden_labor rate if category not found
            rate = db.query(cls).filter(cls.category == 'garden_labor').first()
        if not rate:
            # Fallback default
            return Decimal(str(hours)) * Decimal('10.0')
        return Decimal(str(hours)) * rate.eur_per_hour

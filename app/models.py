"""
Erdpuls Collective Threshold Model - Database Models
"""
from datetime import datetime
from decimal import Decimal
from typing import Optional
import uuid

from sqlalchemy import (
    Column, String, Text, Numeric, Integer, DateTime, Boolean,
    ForeignKey, UniqueConstraint, func, case
)
from sqlalchemy.orm import relationship, Session
from sqlalchemy.dialects.postgresql import UUID

from .database import Base
from .config import get_settings

settings = get_settings()
SCHEMA = settings.db_schema


def generate_uuid():
    return str(uuid.uuid4())


class User(Base):
    """User account for authentication."""
    __tablename__ = 'users'
    __table_args__ = {'schema': SCHEMA}
    
    id = Column(UUID(as_uuid=False), primary_key=True, default=generate_uuid)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    name = Column(String(255))
    
    # Role: 'user' can create offerings, 'admin' can manage everything
    role = Column(String(50), default='user')
    
    # Status
    is_active = Column(Boolean, default=True)
    email_verified = Column(Boolean, default=False)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    last_login = Column(DateTime)
    
    # Relationships
    offerings = relationship("Offering", back_populates="creator", lazy="dynamic")
    
    @property
    def is_admin(self) -> bool:
        return self.role == 'admin'
    
    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'email': self.email,
            'name': self.name,
            'role': self.role,
            'is_admin': self.is_admin,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class Offering(Base):
    """An offering (workshop, course, event) with its threshold."""
    __tablename__ = 'offerings'
    __table_args__ = {'schema': SCHEMA}
    
    id = Column(UUID(as_uuid=False), primary_key=True, default=generate_uuid)
    
    # Multilingual titles
    title = Column(String(255), nullable=False)
    title_de = Column(String(255))
    title_pl = Column(String(255))
    
    # Multilingual descriptions
    description = Column(Text, nullable=False)
    description_de = Column(Text)
    description_pl = Column(Text)
    
    # Threshold and cost breakdown
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
    
    # Status
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
    
    def get_total_contributed(self, db: Session) -> Decimal:
        result = db.query(func.coalesce(func.sum(Contribution.amount_eur), 0))\
            .filter(Contribution.offering_id == self.id).scalar()
        return Decimal(str(result)) if result else Decimal('0')
    
    def get_registration_count(self, db: Session) -> int:
        return db.query(Registration)\
            .filter(Registration.offering_id == self.id)\
            .filter(Registration.status != 'cancelled').count()
    
    @property
    def is_open(self) -> bool:
        now = datetime.utcnow()
        return self.status == 'open' and now < self.contribution_deadline


class Registration(Base):
    """Registration of intention to participate (separate from contributions)."""
    __tablename__ = 'registrations'
    __table_args__ = (
        UniqueConstraint('offering_id', 'email', name='unique_registration'),
        {'schema': SCHEMA}
    )
    
    id = Column(UUID(as_uuid=False), primary_key=True, default=generate_uuid)
    offering_id = Column(UUID(as_uuid=False), ForeignKey(f'{SCHEMA}.offerings.id'), nullable=False)
    
    email = Column(String(255), nullable=False)
    name = Column(String(255))
    referral_source = Column(String(255))
    status = Column(String(50), default='registered')
    registered_at = Column(DateTime, default=datetime.utcnow)
    
    offering = relationship("Offering", back_populates="registrations")


class Contribution(Base):
    """
    Contributions to offerings.
    Identity stored SEPARATELY in ContributionContact for operational needs.
    Public visibility: aggregates only. Organizer visibility: linked for coordination.
    """
    __tablename__ = 'contributions'
    __table_args__ = {'schema': SCHEMA}
    
    id = Column(UUID(as_uuid=False), primary_key=True, default=generate_uuid)
    offering_id = Column(UUID(as_uuid=False), ForeignKey(f'{SCHEMA}.offerings.id'), nullable=False)
    
    amount_eur = Column(Numeric(10, 2), nullable=False)
    contribution_type = Column(String(50), default='euro')  # euro, token, hours
    token_amount = Column(Numeric(15, 2))
    hours_category = Column(String(100))  # garden_labor, technical, knowledge_sharing, etc.
    hours_amount = Column(Numeric(5, 2))  # Number of hours pledged
    hours_description = Column(Text)
    hours_equivalent_eur = Column(Numeric(10, 2))
    
    # Status tracking for operational needs
    # euro: pending -> confirmed (payment received)
    # token: pending -> confirmed (tokens transferred)
    # hours: pending -> scheduled -> completed
    status = Column(String(50), default='pending')
    
    contributed_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    offering = relationship("Offering", back_populates="contributions")
    contact = relationship("ContributionContact", back_populates="contribution", uselist=False)


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
    phone = Column(String(50))  # Optional, useful for hours coordination
    notes = Column(Text)  # Contributor's notes about their contribution
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationship
    contribution = relationship("Contribution", back_populates="contact")


class RegenerationFund(Base):
    """Community reserve from surplus contributions."""
    __tablename__ = 'regeneration_fund'
    __table_args__ = {'schema': SCHEMA}
    
    id = Column(UUID(as_uuid=False), primary_key=True, default=generate_uuid)
    amount = Column(Numeric(10, 2), nullable=False)
    transaction_type = Column(String(50), nullable=False)
    offering_id = Column(UUID(as_uuid=False), ForeignKey(f'{SCHEMA}.offerings.id'))
    description = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    @staticmethod
    def get_balance(db: Session) -> Decimal:
        result = db.query(
            func.coalesce(func.sum(
                case(
                    (RegenerationFund.transaction_type == 'surplus_in', RegenerationFund.amount),
                    (RegenerationFund.transaction_type.in_(['shortfall_cover', 'seed_offering']), -RegenerationFund.amount),
                    (RegenerationFund.transaction_type == 'adjustment', RegenerationFund.amount),
                    else_=0
                )
            ), 0)
        ).scalar()
        return Decimal(str(result)) if result else Decimal('0')


class TokenRate(Base):
    """Exchange rate for UBECrc tokens to EUR."""
    __tablename__ = 'token_rates'
    __table_args__ = {'schema': SCHEMA}
    
    id = Column(UUID(as_uuid=False), primary_key=True, default=generate_uuid)
    tokens_per_eur = Column(Numeric(15, 4), nullable=False, default=70.0)
    effective_from = Column(DateTime, default=datetime.utcnow)
    effective_until = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    @staticmethod
    def get_current_rate(db: Session) -> float:
        now = datetime.utcnow()
        rate = db.query(TokenRate).filter(
            TokenRate.effective_from <= now,
            (TokenRate.effective_until.is_(None)) | (TokenRate.effective_until > now)
        ).order_by(TokenRate.effective_from.desc()).first()
        return float(rate.tokens_per_eur) if rate else 70.0
    
    @staticmethod
    def tokens_to_eur(tokens: float, db: Session) -> Decimal:
        rate = TokenRate.get_current_rate(db)
        return Decimal(str(tokens)) / Decimal(str(rate))


class HoursRate(Base):
    """Rates for valuing different types of contribution hours."""
    __tablename__ = 'hours_rates'
    __table_args__ = {'schema': SCHEMA}
    
    id = Column(UUID(as_uuid=False), primary_key=True, default=generate_uuid)
    category = Column(String(100), unique=True, nullable=False)
    eur_per_hour = Column(Numeric(10, 2), nullable=False)
    description = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    @staticmethod
    def get_rate(category: str, db: Session) -> float:
        rate = db.query(HoursRate).filter_by(category=category).first()
        return float(rate.eur_per_hour) if rate else 10.0
    
    @staticmethod
    def hours_to_eur(hours: float, category: str, db: Session) -> Decimal:
        rate = HoursRate.get_rate(category, db)
        return Decimal(str(hours)) * Decimal(str(rate))

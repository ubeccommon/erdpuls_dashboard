#!/usr/bin/env python3
"""
Erdpuls Collective Threshold Model - Seed Data
Run with: python seed_data.py
"""
from datetime import datetime, timedelta
from decimal import Decimal

from app.database import SessionLocal, engine
from app.models import Base, Offering, Registration, Contribution, RegenerationFund


def seed():
    """Seed the database with sample data"""
    db = SessionLocal()
    
    try:
        # Create sample offering 1
        offering1 = Offering(
            title="Thinking Like a Plant",
            title_de="Wie eine Pflanze denken",
            title_pl="Myśleć jak roślina",
            description="A weekend workshop exploring phenomenological observation, plant perception, and ecological consciousness. Learn to observe with all your senses and develop deep relationship with living systems.",
            description_de="Ein Wochenend-Workshop zur Erforschung phänomenologischer Beobachtung, Pflanzenwahrnehmung und ökologischem Bewusstsein. Lernen Sie, mit allen Sinnen zu beobachten und eine tiefe Beziehung zu lebenden Systemen zu entwickeln.",
            description_pl="Weekendowe warsztaty poświęcone obserwacji fenomenologicznej, percepcji roślin i świadomości ekologicznej. Naucz się obserwować wszystkimi zmysłami i rozwijać głęboką relację z żywymi systemami.",
            threshold_amount=Decimal("700.00"),
            facilitator_cost=Decimal("400.00"),
            materials_cost=Decimal("80.00"),
            meals_cost=Decimal("120.00"),
            space_cost=Decimal("0.00"),
            sustainability_contribution=Decimal("100.00"),
            event_date=datetime.now() + timedelta(days=30),
            registration_deadline=datetime.now() + timedelta(days=25),
            contribution_deadline=datetime.now() + timedelta(days=28),
            max_participants=15,
            status="open"
        )
        db.add(offering1)
        db.flush()
        
        # Add some registrations
        for i, (email, name) in enumerate([
            ("student1@example.com", "Maria Schmidt"),
            ("student2@example.com", "Jan Kowalski"),
            ("student3@example.com", None),
        ]):
            reg = Registration(
                offering_id=offering1.id,
                email=email,
                name=name,
                status="registered"
            )
            db.add(reg)
        
        # Add some anonymous contributions
        contributions = [
            Decimal("150.00"),
            Decimal("50.00"),
            Decimal("75.00"),
            Decimal("25.00"),
        ]
        for amount in contributions:
            contrib = Contribution(
                offering_id=offering1.id,
                amount_eur=amount,
                contribution_type="euro"
            )
            db.add(contrib)
        
        # Create sample offering 2
        offering2 = Offering(
            title="Introduction to Permaculture Design",
            title_de="Einführung in Permakultur-Design",
            title_pl="Wprowadzenie do projektowania permakultury",
            description="A full-day introduction to permaculture principles and design patterns. Hands-on work in the Living Laboratory combined with theoretical foundations.",
            description_de="Eine ganztägige Einführung in Permakultur-Prinzipien und Designmuster. Praktische Arbeit im Lebenden Labor kombiniert mit theoretischen Grundlagen.",
            description_pl="Całodniowe wprowadzenie do zasad permakultury i wzorców projektowych. Praktyczna praca w Żywym Laboratorium połączona z podstawami teoretycznymi.",
            threshold_amount=Decimal("450.00"),
            facilitator_cost=Decimal("250.00"),
            materials_cost=Decimal("100.00"),
            meals_cost=Decimal("50.00"),
            space_cost=Decimal("0.00"),
            sustainability_contribution=Decimal("50.00"),
            event_date=datetime.now() + timedelta(days=45),
            registration_deadline=datetime.now() + timedelta(days=40),
            contribution_deadline=datetime.now() + timedelta(days=43),
            max_participants=20,
            status="open"
        )
        db.add(offering2)
        db.flush()
        
        # Add a registration
        reg = Registration(
            offering_id=offering2.id,
            email="interested@example.com",
            name="Alex Meyer",
            status="registered"
        )
        db.add(reg)
        
        # Add a contribution
        contrib = Contribution(
            offering_id=offering2.id,
            amount_eur=Decimal("100.00"),
            contribution_type="euro"
        )
        db.add(contrib)
        
        # Add initial Regeneration Fund balance
        fund_entry = RegenerationFund(
            amount=Decimal("150.00"),
            transaction_type="surplus_in",
            description="Initial seed from previous workshop surplus"
        )
        db.add(fund_entry)
        
        db.commit()
        print("✅ Sample data seeded successfully!")
        print(f"   - Created 2 offerings")
        print(f"   - Created 4 registrations")
        print(f"   - Created 5 anonymous contributions")
        print(f"   - Created 1 Regeneration Fund entry")
        
    except Exception as e:
        db.rollback()
        print(f"❌ Error seeding data: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed()

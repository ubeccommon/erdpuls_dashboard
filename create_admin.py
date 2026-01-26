#!/usr/bin/env python3
"""
Erdpuls Collective Threshold Model - Create Admin User
Run with: python create_admin.py <email> <password> [name]
"""
import sys
from app.database import SessionLocal
from app.auth import create_user


def main():
    if len(sys.argv) < 3:
        print("Usage: python create_admin.py <email> <password> [name]")
        print("Example: python create_admin.py admin@erdpuls.org mysecurepassword 'Admin User'")
        sys.exit(1)
    
    email = sys.argv[1]
    password = sys.argv[2]
    name = sys.argv[3] if len(sys.argv) > 3 else None
    
    if len(password) < 8:
        print("Error: Password must be at least 8 characters")
        sys.exit(1)
    
    db = SessionLocal()
    
    try:
        user = create_user(
            email=email,
            password=password,
            name=name,
            role="admin",
            db=db
        )
        print(f"✅ Admin user created successfully!")
        print(f"   Email: {user.email}")
        print(f"   Name: {user.name or '(not set)'}")
        print(f"   Role: {user.role}")
        print(f"   ID: {user.id}")
    except ValueError as e:
        print(f"❌ Error: {e}")
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()

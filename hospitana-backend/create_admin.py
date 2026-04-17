"""
Run once to seed default admin, doctor, and receptionist accounts.

    cd hospitana-backend
    python create_admin.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from app.database import SessionLocal, engine, Base
from app.models.user import User, UserRole
from app.models.doctor import DoctorProfile
from app.models.patient import PatientProfile
from app.utils.auth import hash_password

Base.metadata.create_all(bind=engine)

SEED_USERS = [
    {
        "first_name": "Admin",
        "last_name": "Sahara",
        "email": "admin@saharahospital.com",
        "phone": "9000000001",
        "password": "Admin@1234",
        "role": UserRole.admin,
        "is_active": True,
        "is_verified": True,
    },
    {
        "first_name": "Dr. Ramesh",
        "last_name": "Sharma",
        "email": "doctor@saharahospital.com",
        "phone": "9000000002",
        "password": "Doctor@1234",
        "role": UserRole.doctor,
        "is_active": True,
        "is_verified": True,
    },
    {
        "first_name": "Priya",
        "last_name": "Singh",
        "email": "reception@saharahospital.com",
        "phone": "9000000003",
        "password": "Staff@1234",
        "role": UserRole.receptionist,
        "is_active": True,
        "is_verified": True,
    },
    {
        "first_name": "Suresh",
        "last_name": "Gupta",
        "email": "accounts@saharahospital.com",
        "phone": "9000000004",
        "password": "Staff@1234",
        "role": UserRole.accountant,
        "is_active": True,
        "is_verified": True,
    },
]


def seed():
    db = SessionLocal()
    try:
        for data in SEED_USERS:
            existing = db.query(User).filter(User.email == data["email"]).first()
            if existing:
                print(f"  SKIP  {data['email']} (already exists)")
                continue

            user = User(
                first_name=data["first_name"],
                last_name=data["last_name"],
                email=data["email"],
                phone=data["phone"],
                password=hash_password(data["password"]),
                role=data["role"],
                is_active=data["is_active"],
                is_verified=data["is_verified"],
            )
            db.add(user)
            db.flush()

            # Doctor profile
            if user.role == UserRole.doctor:
                dp = DoctorProfile(
                    user_id=user.id,
                    specialization="General Medicine",
                    qualification="MBBS, MD",
                    experience_years=10,
                    consultation_fee=500,
                    is_available=True,
                )
                db.add(dp)

            db.commit()
            print(f"  CREATED  {user.role.value}: {user.email}  /  pwd: {data['password']}")

    finally:
        db.close()


if __name__ == "__main__":
    print("\n🏥  Hospitana HMS — Seeding default accounts\n")
    seed()
    print("\n✅  Done. Change ALL passwords before going live!\n")

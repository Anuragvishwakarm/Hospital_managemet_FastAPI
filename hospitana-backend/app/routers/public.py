""

import random
import string
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session
from app.models.media import WardPhoto, HospitalPhoto
from app.database import get_db
from app.models.user import User, UserRole
from app.models.patient import PatientProfile
from app.models.doctor import DoctorProfile
from app.models.bed import Ward, Bed
from app.utils.auth import hash_password, verify_password, create_access_token  # type: ignore
from app.config import settings  # type: ignore

router = APIRouter(prefix="/public", tags=["public"])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/public/auth/login", auto_error=False)


def _get_current_patient(
    token: Optional[str] = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    if not token:
        raise HTTPException(status_code=401, detail="Login required",
                            headers={"WWW-Authenticate": "Bearer"})
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY,
            algorithms=[getattr(settings, "ALGORITHM", "HS256")],
        )
        user_id = int(payload.get("sub"))
    except (JWTError, TypeError, ValueError):
        raise HTTPException(status_code=401, detail="Invalid token")
    user = db.query(User).filter(User.id == user_id, User.is_active.is_(True)).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user


# ─── Response / request schemas ─────────────────────────────────────────────
class PublicDoctor(BaseModel):
    id: int
    name: str
    specialization: str
    department: str
    qualification: str
    experience_years: int
    consultation_fee: float
    bio: Optional[str] = None
    languages: list[str]
    available_days: list[str]
    photo_url: str
    rating: float = 4.8
    consultations: int = 0
    model_config = {"from_attributes": True}


class PublicBed(BaseModel):
    id: int
    bed_number: str
    is_occupied: bool


class PublicWard(BaseModel):
    id: int
    name: str
    type: str
    description: Optional[str] = None
    daily_charge: float = 0
    amenities: list[str] = []
    total_beds: int
    available_beds: int
    beds: list[PublicBed]
    photos: list[str] = []


class PatientRegisterRequest(BaseModel):
    first_name: str = Field(min_length=1, max_length=80)
    last_name: str = Field(min_length=1, max_length=80)
    email: Optional[EmailStr] = None
    phone: str = Field(min_length=7, max_length=20)
    password: str = Field(min_length=6, max_length=100)
    # Optional at signup — patient can fill rest from the profile page
    dob: Optional[date] = None
    gender: Optional[str] = None
    blood_group: Optional[str] = None
    address: Optional[str] = None


class PatientLoginRequest(BaseModel):
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    password: str


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict


# ─── Doctor serialiser ──────────────────────────────────────────────────────
def _serialise_doctor(user: User, profile: DoctorProfile) -> PublicDoctor:
    full_name = f"{user.first_name or ''} {user.last_name or ''}".strip() or "Doctor"
    spec = (profile.specialization if profile else None) or "General Practitioner"
    qual = (profile.qualification if profile else None) or "MBBS"
    exp = (profile.experience_years if profile else 0) or 0
    fee = float((profile.consultation_fee if profile else 0) or 0)
    bio = (profile.bio if profile else None) or (
        f"Experienced specialist at Sahara Hospital with {exp}+ years of practice."
    )
    return PublicDoctor(
        id=user.id, name=full_name, specialization=spec, department=spec,
        qualification=qual, experience_years=exp, consultation_fee=fee, bio=bio,
        languages=["Hindi", "English"],
        available_days=["Mon", "Tue", "Wed", "Thu", "Fri", "Sat"],
        photo_url=(
            profile.photo_url
            or f"https://ui-avatars.com/api/?name={full_name.replace(' ', '+')}"
                f"&background=0F4C4A&color=FAF6EF&size=512&bold=true&format=png"
        ),
        rating=4.8, consultations=0,
    )


# ─── DOCTORS ────────────────────────────────────────────────────────────────
@router.get("/doctors", response_model=list[PublicDoctor])
def list_doctors(
    department: Optional[str] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db),
):
    rows = (
        db.query(DoctorProfile, User)
        .join(User, User.id == DoctorProfile.user_id)
        .filter(User.is_active.is_(True)).all()
    )
    doctors = [_serialise_doctor(u, p) for p, u in rows]
    if department and department.lower() != "all":
        doctors = [d for d in doctors if d.department.lower() == department.lower()]
    if search:
        s = search.lower()
        doctors = [d for d in doctors if s in d.name.lower() or s in d.specialization.lower()]
    return doctors


@router.get("/doctors/{doctor_id}", response_model=PublicDoctor)
def get_doctor(doctor_id: int, db: Session = Depends(get_db)):
    row = (
        db.query(DoctorProfile, User)
        .join(User, User.id == DoctorProfile.user_id)
        .filter(User.id == doctor_id).first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="Doctor not found")
    p, u = row
    return _serialise_doctor(u, p)


# ─── WARDS / STATS ──────────────────────────────────────────────────────────
@router.get("/wards", response_model=list[PublicWard])
def list_wards(db: Session = Depends(get_db)):
        wards = db.query(Ward).all()
        result = []
        for w in wards:
            beds = db.query(Bed).filter(Bed.ward_id == w.id).all()
 
            # NEW — fetch ward photos, sorted
            photos = (
                db.query(WardPhoto)
                .filter(WardPhoto.ward_id == w.id)
                .order_by(WardPhoto.sort_order, WardPhoto.id)
                .all()
            )
 
            result.append(PublicWard(
                id=w.id,
                name=getattr(w, "name", f"Ward {w.id}"),
                type=str(getattr(w, "ward_type", None) or getattr(w, "type", None) or "general"),
                description=getattr(w, "description", None),
                daily_charge=float(getattr(w, "daily_charge", 0) or 0),
                amenities=(getattr(w, "amenities", None) or []),
                total_beds=len(beds),
                available_beds=sum(1 for b in beds if not bool(getattr(b, "is_occupied", False))),
                beds=[PublicBed(
                    id=b.id,
                    bed_number=getattr(b, "bed_number", f"B-{b.id:02d}"),
                    is_occupied=bool(getattr(b, "is_occupied", False)),
                ) for b in beds],
                photos=[p.photo_url for p in photos],     # ← ADD THIS LINE
            ))
        return result





@router.get("/stats")
def stats(db: Session = Depends(get_db)):
    doctor_count = (
        db.query(DoctorProfile).join(User, User.id == DoctorProfile.user_id)
        .filter(User.is_active.is_(True)).count()
    )
    return {
        "doctors": doctor_count,
        "beds": db.query(Bed).count(),
        "departments": db.query(Ward).count() or 14,
        "years_serving": 17,
        "patients_served_yearly": 48000,
        "surgeries_yearly": 3200,
    }


# ─── UHID generator (same algorithm as your patients.py) ────────────────────
def _generate_uhid(db: Session) -> str:
    while True:
        uid = "SAH-" + "".join(random.choices(string.digits, k=5))
        if not db.query(PatientProfile).filter(PatientProfile.uhid == uid).first():
            return uid


# ─── AUTH — patient self-signup + login ─────────────────────────────────────
@router.post("/auth/register", response_model=AuthResponse)
def register_patient(payload: PatientRegisterRequest, db: Session = Depends(get_db)):
    """
    Mirrors the internals of your staff POST /patients endpoint so the DB row
    looks identical. Uses phone as the unique identifier (your pattern).
    """
    # Phone uniqueness
    if db.query(User).filter(User.phone == payload.phone).first():
        raise HTTPException(status_code=400, detail="Phone number already registered")
    # Email uniqueness (if provided)
    if payload.email and db.query(User).filter(User.email == payload.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")

    user = User(
        first_name=payload.first_name,
        last_name=payload.last_name,
        email=payload.email or f"{payload.phone}@hospitana.local",
        phone=payload.phone,
        password=hash_password(payload.password),    # ← matches your column name
        role=UserRole.patient,
        is_active=True,
        is_verified=True,
    )
    db.add(user)
    db.flush()

    profile = PatientProfile(
        user_id=user.id,
        uhid=_generate_uhid(db),
        dob=payload.dob,
        gender=payload.gender,
        blood_group=payload.blood_group,
        address=payload.address,
    )
    db.add(profile)
    db.commit()
    db.refresh(user)

    token = create_access_token(data={"sub": str(user.id)})
    return AuthResponse(
        access_token=token,
        user={
            "id": user.id,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "email": user.email,
            "phone": user.phone,
            "role": "patient",
            "uhid": profile.uhid,
        },
    )


@router.post("/auth/login", response_model=AuthResponse)
def login_patient(payload: PatientLoginRequest, db: Session = Depends(get_db)):
    """
    Accepts either email or phone + password.
    """
    if not payload.email and not payload.phone:
        raise HTTPException(status_code=400, detail="Provide email or phone.")

    q = db.query(User)
    user = (
        q.filter(User.email == payload.email).first() if payload.email
        else q.filter(User.phone == payload.phone).first()
    )
    if not user or not verify_password(payload.password, user.password):
        raise HTTPException(status_code=401, detail="Email/phone or password is incorrect.")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account is disabled.")

    uhid = None
    if getattr(user, "patient_profile", None):
        uhid = user.patient_profile.uhid

    token = create_access_token(data={"sub": str(user.id)})
    return AuthResponse(
        access_token=token,
        user={
            "id": user.id,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "email": user.email,
            "phone": user.phone,
            "role": str(getattr(user, "role", "patient")),
            "uhid": uhid,
        },
    )


# ─── PASSWORD CHANGE ────────────────────────────────────────────────────────
class PasswordChangeRequest(BaseModel):
    current_password: str = Field(min_length=1)
    new_password: str = Field(min_length=6, max_length=100)


@router.put("/auth/password")
def change_password(
    payload: PasswordChangeRequest,
    db: Session = Depends(get_db),
    me: User = Depends(_get_current_patient),
):
    """
    Change the logged-in patient's password. Useful for walk-in patients who
    got a default password set by reception — they log in once, then change it.
    """
    if not verify_password(payload.current_password, me.password):
        raise HTTPException(status_code=400, detail="Current password is incorrect.")
    if payload.current_password == payload.new_password:
        raise HTTPException(status_code=400, detail="New password must be different.")

    me.password = hash_password(payload.new_password)
    db.commit()
    return {"ok": True, "message": "Password updated successfully."}


@router.get("/auth/me")
def who_am_i(me: User = Depends(_get_current_patient)):
    uhid = None
    if getattr(me, "patient_profile", None):
        uhid = me.patient_profile.uhid
    return {
        "id": me.id,
        "first_name": me.first_name,
        "last_name": me.last_name,
        "email": me.email,
        "phone": me.phone,
        "uhid": uhid,
    }


@router.get("/hospital-photos")
def list_public_hospital_photos(
        category: Optional[str] = None,
        db: Session = Depends(get_db),
    ):
        q = db.query(HospitalPhoto)
        if category:
            q = q.filter(HospitalPhoto.category == category)
        rows = q.order_by(HospitalPhoto.sort_order, HospitalPhoto.id).all()
        return [
            {
                "id": r.id,
                "photo_url": r.photo_url,
                "caption": r.caption,
                "category": r.category,
            }
            for r in rows
        ]
 
 

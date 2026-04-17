from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime

from app.database import get_db
from app.models.user import User, UserRole
from app.models.doctor import DoctorProfile
from app.schemas.doctor import DoctorProfileCreate, DoctorProfileUpdate, DoctorProfileResponse, DoctorResponse
from app.utils.permissions import get_current_user, admin_only, admin_or_doctor

router = APIRouter(prefix="/doctors", tags=["Doctors"])


# ── List all doctors (any authenticated user) ─────────────────────────────────

@router.get("", response_model=List[DoctorResponse])
def list_doctors(
    available_only: bool = Query(False),
    specialization: Optional[str] = Query(None),
    skip:  int = Query(0, ge=0),
    limit: int = Query(20, le=100),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    q = db.query(User).filter(User.role == UserRole.doctor, User.is_active == True)

    if available_only:
        q = q.join(DoctorProfile).filter(DoctorProfile.is_available == True)
    if specialization:
        q = q.join(DoctorProfile).filter(DoctorProfile.specialization.ilike(f"%{specialization}%"))

    doctors = q.offset(skip).limit(limit).all()
    return [_build_doctor_response(d) for d in doctors]


# ── Get my own profile (doctor) ───────────────────────────────────────────────

@router.get("/me", response_model=DoctorResponse)
def get_my_profile(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != UserRole.doctor:
        raise HTTPException(403, "Only doctors can access this endpoint")
    return _build_doctor_response(current_user)


# ── Get doctor by ID ──────────────────────────────────────────────────────────

@router.get("/{doctor_id}", response_model=DoctorResponse)
def get_doctor(doctor_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    doctor = _get_doctor_or_404(doctor_id, db)
    return _build_doctor_response(doctor)


# ── Create doctor profile (admin or the doctor themselves) ────────────────────

@router.post("/{doctor_id}/profile", status_code=201, response_model=DoctorProfileResponse)
def create_doctor_profile(
    doctor_id: int,
    payload: DoctorProfileCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Only admin or the doctor themselves
    if current_user.role != UserRole.admin and current_user.id != doctor_id:
        raise HTTPException(403, "Permission denied")

    doctor = _get_doctor_or_404(doctor_id, db)

    existing = db.query(DoctorProfile).filter(DoctorProfile.user_id == doctor_id).first()
    if existing:
        raise HTTPException(400, "Doctor profile already exists. Use PUT to update.")

    profile = DoctorProfile(user_id=doctor_id, **payload.model_dump())
    db.add(profile)
    db.commit()
    db.refresh(profile)
    return profile


# ── Update doctor profile ─────────────────────────────────────────────────────

@router.put("/{doctor_id}/profile", response_model=DoctorProfileResponse)
def update_doctor_profile(
    doctor_id: int,
    payload: DoctorProfileUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != UserRole.admin and current_user.id != doctor_id:
        raise HTTPException(403, "Permission denied")

    profile = db.query(DoctorProfile).filter(DoctorProfile.user_id == doctor_id).first()
    if not profile:
        raise HTTPException(404, "Doctor profile not found. Create one first.")

    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(profile, field, value)
    profile.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(profile)
    return profile


# ── Toggle availability ───────────────────────────────────────────────────────

@router.put("/{doctor_id}/toggle-availability")
def toggle_availability(
    doctor_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != UserRole.admin and current_user.id != doctor_id:
        raise HTTPException(403, "Permission denied")

    profile = db.query(DoctorProfile).filter(DoctorProfile.user_id == doctor_id).first()
    if not profile:
        raise HTTPException(404, "Doctor profile not found")

    profile.is_available = not profile.is_available
    profile.updated_at = datetime.utcnow()
    db.commit()
    return {"doctor_id": doctor_id, "is_available": profile.is_available}


# ── List specializations ──────────────────────────────────────────────────────

@router.get("/meta/specializations")
def list_specializations(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    rows = (
        db.query(DoctorProfile.specialization)
        .join(User)
        .filter(User.is_active == True)
        .distinct()
        .all()
    )
    return {"specializations": [r[0] for r in rows]}


# ── Helpers ───────────────────────────────────────────────────────────────────

def _get_doctor_or_404(doctor_id: int, db: Session) -> User:
    doctor = db.query(User).filter(User.id == doctor_id, User.role == UserRole.doctor).first()
    if not doctor:
        raise HTTPException(404, "Doctor not found")
    return doctor


def _build_doctor_response(user: User) -> DoctorResponse:
    return DoctorResponse(
        id=user.id,
        first_name=user.first_name,
        last_name=user.last_name,
        email=user.email,
        phone=user.phone,
        is_active=user.is_active,
        profile=DoctorProfileResponse.model_validate(user.doctor_profile) if user.doctor_profile else None,
    )

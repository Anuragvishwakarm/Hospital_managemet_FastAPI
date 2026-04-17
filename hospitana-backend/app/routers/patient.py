from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
import random, string

from app.database import get_db
from app.models.user import User, UserRole
from app.models.patient import PatientProfile
from app.schemas.patient import (
    PatientRegisterFull,
    PatientProfileUpdate,
    PatientResponse,
    PatientProfileResponse,
)
from app.utils.auth import hash_password
from app.utils.permissions import get_current_user, admin_or_receptionist

router = APIRouter(prefix="/patients", tags=["Patients"])


# ── List patients (admin / receptionist) ─────────────────────────────────────

@router.get("", response_model=List[PatientResponse])
def list_patients(
    search: Optional[str] = Query(None, description="Search by name / phone / UHID"),
    skip:   int = Query(0, ge=0),
    limit:  int = Query(20, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(admin_or_receptionist),
):
    q = db.query(User).filter(User.role == UserRole.patient)
    if search:
        like = f"%{search}%"
        q = q.filter(
            (User.first_name.ilike(like))
            | (User.last_name.ilike(like))
            | (User.phone.ilike(like))
            | (User.email.ilike(like))
        )
    patients = q.order_by(User.created_at.desc()).offset(skip).limit(limit).all()
    return [_build_patient_response(p) for p in patients]


# ── My own record (patient) ───────────────────────────────────────────────────

@router.get("/me", response_model=PatientResponse)
def get_my_record(current_user: User = Depends(get_current_user)):
    if current_user.role != UserRole.patient:
        raise HTTPException(403, "Only patients can access this endpoint")
    return _build_patient_response(current_user)


# ── Get patient by ID (staff) ─────────────────────────────────────────────────

@router.get("/{patient_id}", response_model=PatientResponse)
def get_patient(
    patient_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Patient can only see their own record; staff can see any
    if current_user.role == UserRole.patient and current_user.id != patient_id:
        raise HTTPException(403, "Access denied")

    patient = _get_patient_or_404(patient_id, db)
    return _build_patient_response(patient)


# ── Register patient by receptionist / admin ─────────────────────────────────

@router.post("", status_code=201, response_model=PatientResponse)
def register_patient(
    payload: PatientRegisterFull,
    db: Session = Depends(get_db),
    _: User = Depends(admin_or_receptionist),
):
    # Use phone as unique identifier; email is optional
    if db.query(User).filter(User.phone == payload.phone).first():
        raise HTTPException(400, "Phone number already registered")
    if payload.email and db.query(User).filter(User.email == payload.email).first():
        raise HTTPException(400, "Email already registered")

    user = User(
        first_name=payload.first_name,
        last_name=payload.last_name,
        email=payload.email or f"{payload.phone}@hospitana.local",
        phone=payload.phone,
        password=hash_password(payload.password),
        role=UserRole.patient,
        is_active=True,
        is_verified=True,
    )
    db.add(user)
    db.flush()

    uhid = _generate_uhid(db)
    profile = PatientProfile(
        user_id=user.id,
        uhid=uhid,
        dob=payload.dob,
        gender=payload.gender,
        blood_group=payload.blood_group,
        address=payload.address,
        city=payload.city,
        state=payload.state,
        pincode=payload.pincode,
        emergency_contact_name=payload.emergency_contact_name,
        emergency_contact_phone=payload.emergency_contact_phone,
        allergies=payload.allergies,
        existing_conditions=payload.existing_conditions,
    )
    db.add(profile)
    db.commit()
    db.refresh(user)
    return _build_patient_response(user)


# ── Update patient profile (admin / receptionist / self) ─────────────────────

@router.put("/{patient_id}/profile", response_model=PatientProfileResponse)
def update_patient_profile(
    patient_id: int,
    payload: PatientProfileUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role == UserRole.patient and current_user.id != patient_id:
        raise HTTPException(403, "Access denied")
    if current_user.role == UserRole.doctor:
        raise HTTPException(403, "Doctors cannot edit patient profiles directly")

    patient = _get_patient_or_404(patient_id, db)
    profile = patient.patient_profile
    if not profile:
        raise HTTPException(404, "Patient profile not found")

    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(profile, field, value)
    profile.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(profile)
    return profile


# ── Update basic user info ────────────────────────────────────────────────────

@router.put("/{patient_id}")
def update_patient_info(
    patient_id: int,
    first_name: Optional[str] = None,
    last_name:  Optional[str] = None,
    phone:      Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role == UserRole.patient and current_user.id != patient_id:
        raise HTTPException(403, "Access denied")

    patient = _get_patient_or_404(patient_id, db)
    if first_name: patient.first_name = first_name
    if last_name:  patient.last_name  = last_name
    if phone:
        if db.query(User).filter(User.phone == phone, User.id != patient_id).first():
            raise HTTPException(400, "Phone already in use")
        patient.phone = phone

    patient.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(patient)
    return _build_patient_response(patient)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _get_patient_or_404(patient_id: int, db: Session) -> User:
    patient = db.query(User).filter(User.id == patient_id, User.role == UserRole.patient).first()
    if not patient:
        raise HTTPException(404, "Patient not found")
    return patient


def _build_patient_response(user: User) -> PatientResponse:
    return PatientResponse(
        id=user.id,
        first_name=user.first_name,
        last_name=user.last_name,
        email=user.email,
        phone=user.phone,
        is_active=user.is_active,
        profile=PatientProfileResponse.model_validate(user.patient_profile) if user.patient_profile else None,
    )


def _generate_uhid(db: Session) -> str:
    """Generate unique UHID like SAH-00001"""
    while True:
        uid = "SAH-" + "".join(random.choices(string.digits, k=5))
        if not db.query(PatientProfile).filter(PatientProfile.uhid == uid).first():
            return uid

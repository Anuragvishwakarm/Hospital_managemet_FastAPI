from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app.models.user import User, UserRole
from app.models.doctor import DoctorProfile
from app.schemas.doctor import DoctorResponse, DoctorProfileResponse
from app.schemas.patient import PatientResponse
from app.utils.permissions import get_current_user, receptionist_only

router = APIRouter(prefix="/receptionist", tags=["Receptionist"])


# ── Receptionist dashboard summary ───────────────────────────────────────────

@router.get("/dashboard")
def receptionist_dashboard(
    db: Session = Depends(get_db),
    current_user: User = Depends(receptionist_only),
):
    total_patients     = db.query(User).filter(User.role == UserRole.patient).count()
    available_doctors  = (
        db.query(User)
        .join(DoctorProfile)
        .filter(User.role == UserRole.doctor, User.is_active == True, DoctorProfile.is_available == True)
        .count()
    )
    return {
        "receptionist": f"{current_user.first_name} {current_user.last_name}",
        "total_patients": total_patients,
        "available_doctors": available_doctors,
    }


# ── Quick view: available doctors ────────────────────────────────────────────

@router.get("/available-doctors", response_model=List[DoctorResponse])
def available_doctors(
    db: Session = Depends(get_db),
    _: User = Depends(receptionist_only),
):
    doctors = (
        db.query(User)
        .join(DoctorProfile)
        .filter(
            User.role == UserRole.doctor,
            User.is_active == True,
            DoctorProfile.is_available == True,
        )
        .all()
    )
    return [
        DoctorResponse(
            id=d.id,
            first_name=d.first_name,
            last_name=d.last_name,
            email=d.email,
            phone=d.phone,
            is_active=d.is_active,
            profile=DoctorProfileResponse.model_validate(d.doctor_profile) if d.doctor_profile else None,
        )
        for d in doctors
    ]

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from datetime import datetime
from typing import List, Optional

from app.database import get_db
from app.models.user import User, UserRole
from app.models.doctor import DoctorProfile
from app.models.patient import PatientProfile
from app.schemas.admin import StaffCreateByAdmin, StaffUpdateByAdmin, StaffResponse, DashboardStats
from app.schemas.auth import UserResponse
from app.utils.auth import hash_password
from app.utils.permissions import admin_only

router = APIRouter(prefix="/admin", tags=["Admin"])


# ── Dashboard stats ──────────────────────────────────────────────────────────

@router.get("/dashboard-stats", response_model=DashboardStats)
def dashboard_stats(db: Session = Depends(get_db), _: User = Depends(admin_only)):
    total_patients   = db.query(User).filter(User.role == UserRole.patient).count()
    total_doctors    = db.query(User).filter(User.role == UserRole.doctor).count()
    pending          = db.query(User).filter(User.is_active == False, User.role != UserRole.patient).count()
    active_doctors   = db.query(User).filter(User.role == UserRole.doctor, User.is_active == True).count()
    total_staff      = db.query(User).filter(
        User.role.in_([UserRole.doctor, UserRole.receptionist, UserRole.accountant])
    ).count()

    return DashboardStats(
        total_patients=total_patients,
        total_doctors=total_doctors,
        total_staff=total_staff,
        pending_approvals=pending,
        active_doctors=active_doctors,
    )


# ── List all staff ────────────────────────────────────────────────────────────

@router.get("/staff", response_model=List[StaffResponse])
def list_staff(
    role:   Optional[UserRole] = Query(None),
    active: Optional[bool]     = Query(None),
    skip:   int = Query(0, ge=0),
    limit:  int = Query(20, le=100),
    db: Session = Depends(get_db),
    _: User = Depends(admin_only),
):
    q = db.query(User).filter(User.role != UserRole.patient)
    if role:
        q = q.filter(User.role == role)
    if active is not None:
        q = q.filter(User.is_active == active)
    return q.order_by(User.created_at.desc()).offset(skip).limit(limit).all()


# ── Pending approvals ─────────────────────────────────────────────────────────

@router.get("/staff/pending", response_model=List[StaffResponse])
def pending_approvals(db: Session = Depends(get_db), _: User = Depends(admin_only)):
    return (
        db.query(User)
        .filter(User.is_active == False, User.role != UserRole.patient)
        .order_by(User.created_at.asc())
        .all()
    )


# ── Get single staff member ───────────────────────────────────────────────────

@router.get("/staff/{user_id}", response_model=StaffResponse)
def get_staff(user_id: int, db: Session = Depends(get_db), _: User = Depends(admin_only)):
    user = _get_staff_or_404(user_id, db)
    return user


# ── Admin creates staff directly (active immediately) ────────────────────────

@router.post("/staff", status_code=201, response_model=StaffResponse)
def create_staff(
    payload: StaffCreateByAdmin,
    db: Session = Depends(get_db),
    _: User = Depends(admin_only),
):
    if payload.role == UserRole.patient:
        raise HTTPException(400, "Use /auth/register to create patients")
    if db.query(User).filter(User.email == payload.email).first():
        raise HTTPException(400, "Email already registered")
    if db.query(User).filter(User.phone == payload.phone).first():
        raise HTTPException(400, "Phone already registered")

    user = User(
        first_name=payload.first_name,
        last_name=payload.last_name,
        email=payload.email,
        phone=payload.phone,
        password=hash_password(payload.password),
        role=payload.role,
        is_active=True,     # admin-created staff are active immediately
        is_verified=True,
    )
    db.add(user)
    db.flush()

    # If doctor role, create profile
    if payload.role == UserRole.doctor and payload.doctor_profile:
        dp = DoctorProfile(user_id=user.id, **payload.doctor_profile.model_dump())
        db.add(dp)

    db.commit()
    db.refresh(user)
    return user


# ── Update staff ──────────────────────────────────────────────────────────────

@router.put("/staff/{user_id}", response_model=StaffResponse)
def update_staff(
    user_id: int,
    payload: StaffUpdateByAdmin,
    db: Session = Depends(get_db),
    _: User = Depends(admin_only),
):
    user = _get_staff_or_404(user_id, db)
    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(user, field, value)
    user.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(user)
    return user


# ── Approve pending staff ─────────────────────────────────────────────────────

@router.put("/staff/{user_id}/approve", response_model=StaffResponse)
def approve_staff(user_id: int, db: Session = Depends(get_db), _: User = Depends(admin_only)):
    user = _get_staff_or_404(user_id, db)
    if user.is_active:
        raise HTTPException(400, "Staff is already active")
    user.is_active = True
    user.is_verified = True
    user.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(user)
    return user


# ── Reject / deactivate staff ─────────────────────────────────────────────────

@router.put("/staff/{user_id}/reject")
def reject_staff(user_id: int, db: Session = Depends(get_db), _: User = Depends(admin_only)):
    user = _get_staff_or_404(user_id, db)
    db.delete(user)
    db.commit()
    return {"message": f"Staff account for {user.email} has been rejected and removed"}


@router.put("/staff/{user_id}/deactivate", response_model=StaffResponse)
def deactivate_staff(user_id: int, db: Session = Depends(get_db), _: User = Depends(admin_only)):
    user = _get_staff_or_404(user_id, db)
    user.is_active = False
    user.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(user)
    return user


# ── Reset staff password ──────────────────────────────────────────────────────

@router.put("/staff/{user_id}/reset-password")
def reset_password(
    user_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(admin_only),
):
    user = _get_staff_or_404(user_id, db)
    default_pwd = "Hospitana@123"
    user.password = hash_password(default_pwd)
    user.updated_at = datetime.utcnow()
    db.commit()
    return {"message": f"Password reset. New temporary password: {default_pwd}"}


# ── List all users (admin overview) ──────────────────────────────────────────

@router.get("/users", response_model=List[UserResponse])
def list_all_users(
    role:  Optional[UserRole] = Query(None),
    skip:  int = Query(0, ge=0),
    limit: int = Query(20, le=100),
    db: Session = Depends(get_db),
    _: User = Depends(admin_only),
):
    q = db.query(User)
    if role:
        q = q.filter(User.role == role)
    return q.order_by(User.created_at.desc()).offset(skip).limit(limit).all()


# ── Helper ────────────────────────────────────────────────────────────────────

def _get_staff_or_404(user_id: int, db: Session) -> User:
    user = db.query(User).filter(User.id == user_id, User.role != UserRole.patient).first()
    if not user:
        raise HTTPException(404, "Staff member not found")
    return user

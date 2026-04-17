from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime

from app.database import get_db
from app.models.user import User, UserRole
from app.models.patient import PatientProfile
from app.schemas.auth import (
    PatientRegisterRequest,
    StaffRegisterRequest,
    LoginRequest,
    TokenResponse,
    RefreshRequest,
    ChangePasswordRequest,
    UserResponse,
)
from app.utils.auth import hash_password, verify_password, create_access_token, create_refresh_token, decode_token
from app.utils.permissions import get_current_user

router = APIRouter(prefix="/auth", tags=["Auth"])


# ── Patient self-registration ────────────────────────────────────────────────

@router.post("/register", status_code=201)
def register_patient(payload: PatientRegisterRequest, db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == payload.email).first():
        raise HTTPException(400, "Email already registered")
    if db.query(User).filter(User.phone == payload.phone).first():
        raise HTTPException(400, "Phone number already registered")

    user = User(
        first_name=payload.first_name,
        last_name=payload.last_name,
        email=payload.email,
        phone=payload.phone,
        password=hash_password(payload.password),
        role=UserRole.patient,
        is_active=True,    # patients are active immediately
        is_verified=False,
    )
    db.add(user)
    db.flush()

    profile = PatientProfile(user_id=user.id)
    db.add(profile)
    db.commit()
    db.refresh(user)

    tokens = _make_tokens(user)
    return {"message": "Registration successful", "user": UserResponse.model_validate(user), "tokens": tokens}


# ── Staff self-registration (pending admin approval) ─────────────────────────

@router.post("/staff-register", status_code=201)
def staff_register(payload: StaffRegisterRequest, db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == payload.email).first():
        raise HTTPException(400, "Email already registered")
    if db.query(User).filter(User.phone == payload.phone).first():
        raise HTTPException(400, "Phone number already registered")

    user = User(
        first_name=payload.first_name,
        last_name=payload.last_name,
        email=payload.email,
        phone=payload.phone,
        password=hash_password(payload.password),
        role=payload.role,
        is_active=False,    # blocked until admin approves
        is_verified=False,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    return {
        "status": "pending_approval",
        "message": "Registration submitted. Please wait for admin approval before logging in.",
        "user_id": user.id,
    }


# ── Login ─────────────────────────────────────────────────────────────────────

@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email).first()
    if not user or not verify_password(payload.password, user.password):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    if not user.is_active:
        raise HTTPException(
            status_code=403,
            detail="Account not yet activated. Contact admin for approval."
        )

    return _make_tokens(user)


# ── Refresh token ─────────────────────────────────────────────────────────────

@router.post("/token/refresh", response_model=TokenResponse)
def refresh_token(payload: RefreshRequest, db: Session = Depends(get_db)):
    data = decode_token(payload.refresh_token)
    if data.get("type") != "refresh":
        raise HTTPException(401, "Invalid token type")

    user = db.query(User).filter(User.id == int(data["sub"])).first()
    if not user or not user.is_active:
        raise HTTPException(401, "User not found or inactive")

    return _make_tokens(user)


# ── Get profile ───────────────────────────────────────────────────────────────

@router.get("/profile", response_model=UserResponse)
def get_profile(current_user: User = Depends(get_current_user)):
    return current_user


# ── Change password ───────────────────────────────────────────────────────────

@router.put("/change-password")
def change_password(
    payload: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not verify_password(payload.old_password, current_user.password):
        raise HTTPException(400, "Incorrect current password")

    current_user.password = hash_password(payload.new_password)
    current_user.updated_at = datetime.utcnow()
    db.commit()
    return {"message": "Password changed successfully"}


# ── Helper ────────────────────────────────────────────────────────────────────

def _make_tokens(user: User) -> dict:
    data = {"sub": str(user.id), "role": user.role.value}
    return {
        "access_token":  create_access_token(data),
        "refresh_token": create_refresh_token(data),
        "token_type":    "bearer",
    }

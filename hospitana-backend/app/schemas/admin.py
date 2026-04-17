from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime
from app.models.user import UserRole
from app.schemas.doctor import DoctorProfileCreate


class StaffCreateByAdmin(BaseModel):
    """Admin directly creates a staff member — account is active immediately."""
    first_name:    str
    last_name:     str
    email:         EmailStr
    phone:         str
    password:      str
    role:          UserRole
    # Optional doctor profile (filled only if role == doctor)
    doctor_profile: Optional[DoctorProfileCreate] = None


class StaffUpdateByAdmin(BaseModel):
    first_name: Optional[str] = None
    last_name:  Optional[str] = None
    phone:      Optional[str] = None
    is_active:  Optional[bool] = None
    role:       Optional[UserRole] = None


class StaffResponse(BaseModel):
    id:         int
    first_name: str
    last_name:  str
    email:      str
    phone:      str
    role:       UserRole
    is_active:  bool
    created_at: datetime

    model_config = {"from_attributes": True}


class DashboardStats(BaseModel):
    total_patients:  int
    total_doctors:   int
    total_staff:     int
    pending_approvals: int
    active_doctors:  int

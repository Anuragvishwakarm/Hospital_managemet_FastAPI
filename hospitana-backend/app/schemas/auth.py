from pydantic import BaseModel, EmailStr, field_validator
from typing import Optional
from app.models.user import UserRole
from datetime import datetime
import re


class PatientRegisterRequest(BaseModel):
    first_name:       str
    last_name:        str
    email:            EmailStr
    phone:            str
    password:         str
    confirm_password: str

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v):
        if not re.match(r"^[6-9]\d{9}$", v):
            raise ValueError("Enter a valid 10-digit Indian mobile number")
        return v

    @field_validator("password")
    @classmethod
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        if not re.search(r"[A-Z]", v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not re.search(r"\d", v):
            raise ValueError("Password must contain at least one digit")
        return v

    @field_validator("confirm_password")
    @classmethod
    def passwords_match(cls, v, info):
        if "password" in info.data and v != info.data["password"]:
            raise ValueError("Passwords do not match")
        return v


class StaffRegisterRequest(BaseModel):
    first_name: str
    last_name:  str
    email:      EmailStr
    phone:      str
    password:   str
    confirm_password: str
    role: UserRole  # doctor / receptionist / accountant

    @field_validator("role")
    @classmethod
    def validate_staff_role(cls, v):
        allowed = [UserRole.doctor, UserRole.receptionist, UserRole.accountant]
        if v not in allowed:
            raise ValueError(f"Staff role must be one of: {[r.value for r in allowed]}")
        return v

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v):
        if not re.match(r"^[6-9]\d{9}$", v):
            raise ValueError("Enter a valid 10-digit Indian mobile number")
        return v

    @field_validator("confirm_password")
    @classmethod
    def passwords_match(cls, v, info):
        if "password" in info.data and v != info.data["password"]:
            raise ValueError("Passwords do not match")
        return v


class LoginRequest(BaseModel):
    email:    EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token:  str
    refresh_token: str
    token_type:    str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str
    confirm_new_password: str

    @field_validator("confirm_new_password")
    @classmethod
    def passwords_match(cls, v, info):
        if "new_password" in info.data and v != info.data["new_password"]:
            raise ValueError("New passwords do not match")
        return v


class UserResponse(BaseModel):
    id:         int
    first_name: str
    last_name:  str
    email:      str
    phone:      str
    role:       UserRole
    is_active:  bool
    is_verified: bool
    created_at:  datetime 

    model_config = {"from_attributes": True}

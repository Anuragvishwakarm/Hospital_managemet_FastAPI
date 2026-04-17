from pydantic import BaseModel, EmailStr, field_validator
from typing import Optional
from datetime import date, datetime
from app.models.patient import BloodGroup
import re


class PatientProfileCreate(BaseModel):
    dob:                    Optional[date] = None
    gender:                 Optional[str] = None
    blood_group:            Optional[BloodGroup] = None
    address:                Optional[str] = None
    city:                   Optional[str] = None
    state:                  Optional[str] = None
    pincode:                Optional[str] = None
    emergency_contact_name:  Optional[str] = None
    emergency_contact_phone: Optional[str] = None
    allergies:              Optional[str] = None
    existing_conditions:    Optional[str] = None


class PatientRegisterFull(BaseModel):
    """Used by receptionist to register patient with full details."""
    first_name: str
    last_name:  str
    email:      Optional[EmailStr] = None
    phone:      str
    password:   str = "Patient@1234"   # default, patient can change later
    dob:        Optional[date] = None
    gender:     Optional[str] = None
    blood_group: Optional[BloodGroup] = None
    address:    Optional[str] = None
    city:       Optional[str] = None
    state:      Optional[str] = None
    pincode:    Optional[str] = None
    emergency_contact_name:  Optional[str] = None
    emergency_contact_phone: Optional[str] = None
    allergies:          Optional[str] = None
    existing_conditions: Optional[str] = None

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v):
        if not re.match(r"^[6-9]\d{9}$", v):
            raise ValueError("Enter a valid 10-digit Indian mobile number")
        return v


class PatientProfileUpdate(BaseModel):
    dob:            Optional[date] = None
    gender:         Optional[str] = None
    blood_group:    Optional[BloodGroup] = None
    address:        Optional[str] = None
    city:           Optional[str] = None
    state:          Optional[str] = None
    pincode:        Optional[str] = None
    emergency_contact_name:  Optional[str] = None
    emergency_contact_phone: Optional[str] = None
    allergies:          Optional[str] = None
    existing_conditions: Optional[str] = None


class PatientProfileResponse(BaseModel):
    id:          int
    user_id:     int
    uhid:        Optional[str]
    dob:         Optional[date]
    gender:      Optional[str]
    blood_group: Optional[BloodGroup]
    address:     Optional[str]
    city:        Optional[str]
    state:       Optional[str]
    pincode:     Optional[str]
    emergency_contact_name:  Optional[str]
    emergency_contact_phone: Optional[str]
    allergies:          Optional[str]
    existing_conditions: Optional[str]

    model_config = {"from_attributes": True}


class PatientResponse(BaseModel):
    id:         int
    first_name: str
    last_name:  str
    email:      Optional[str]
    phone:      str
    is_active:  bool
    profile:    Optional[PatientProfileResponse] = None

    model_config = {"from_attributes": True}

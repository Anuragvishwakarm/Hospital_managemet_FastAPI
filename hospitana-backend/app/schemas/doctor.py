from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class DoctorProfileCreate(BaseModel):
    specialization:   str
    qualification:    Optional[str] = None
    registration_no:  Optional[str] = None
    experience_years: Optional[int] = 0
    bio:              Optional[str] = None
    consultation_fee: Optional[int] = 0


class DoctorProfileUpdate(BaseModel):
    specialization:   Optional[str] = None
    qualification:    Optional[str] = None
    registration_no:  Optional[str] = None
    experience_years: Optional[int] = None
    bio:              Optional[str] = None
    consultation_fee: Optional[int] = None
    is_available:     Optional[bool] = None


class DoctorProfileResponse(BaseModel):
    id:               int
    user_id:          int
    specialization:   str
    qualification:    Optional[str]
    registration_no:  Optional[str]
    experience_years: int
    bio:              Optional[str]
    consultation_fee: int
    is_available:     bool
    photo_url: Optional[str] = None    
    created_at:       datetime

    model_config = {"from_attributes": True}


class DoctorResponse(BaseModel):
    id:         int
    first_name: str
    last_name:  str
    email:      str
    phone:      str
    is_active:  bool
    profile:    Optional[DoctorProfileResponse] = None

    model_config = {"from_attributes": True}

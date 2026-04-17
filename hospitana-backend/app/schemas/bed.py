from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from decimal import Decimal
from app.models.bed import BedStatus


class WardCreate(BaseModel):
    name:      str
    ward_type: Optional[str] = None
    floor:     Optional[int] = 1


class WardUpdate(BaseModel):
    name:      Optional[str] = None
    ward_type: Optional[str] = None
    floor:     Optional[int] = None
    is_active: Optional[bool] = None


class BedCreate(BaseModel):
    ward_id:    int
    bed_number: str


class BedUpdate(BaseModel):
    status:    Optional[BedStatus] = None
    is_active: Optional[bool] = None


class AdmissionCreate(BaseModel):
    patient_id:       int
    bed_id:           int
    doctor_id:        Optional[int] = None
    admission_reason: Optional[str] = None
    daily_charge:     Optional[Decimal] = Decimal("0")


class DischargeInput(BaseModel):
    discharge_notes: Optional[str] = None


class BedResponse(BaseModel):
    id:         int
    ward_id:    int
    bed_number: str
    status:     BedStatus
    is_active:  bool

    model_config = {"from_attributes": True}


class WardResponse(BaseModel):
    id:          int
    name:        str
    ward_type:   Optional[str]
    floor:       int
    total_beds:  int
    is_active:   bool
    beds:        List[BedResponse] = []
    occupied:    int = 0
    available:   int = 0

    model_config = {"from_attributes": True}


class AdmissionResponse(BaseModel):
    id:               int
    patient_id:       int
    bed_id:           int
    doctor_id:        Optional[int]
    admitted_at:      datetime
    discharged_at:    Optional[datetime]
    admission_reason: Optional[str]
    discharge_notes:  Optional[str]
    daily_charge:     Decimal
    is_active:        bool
    patient_name:     Optional[str] = None
    bed_number:       Optional[str] = None
    ward_name:        Optional[str] = None

    model_config = {"from_attributes": True}

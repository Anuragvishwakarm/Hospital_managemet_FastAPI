from pydantic import BaseModel
from typing import Optional, List
from datetime import date, time, datetime
from app.models.appointment import AppointmentStatus


class MedicineItem(BaseModel):
    medicine_name: str
    dosage:        Optional[str] = None
    frequency:     Optional[str] = None
    duration:      Optional[str] = None
    instructions:  Optional[str] = None


class PrescriptionCreate(BaseModel):
    diagnosis:      Optional[str] = None
    notes:          Optional[str] = None
    follow_up_date: Optional[date] = None
    medicines:      List[MedicineItem] = []


class PrescriptionResponse(BaseModel):
    id:             int
    appointment_id: int
    diagnosis:      Optional[str]
    notes:          Optional[str]
    follow_up_date: Optional[date]
    medicines:      List[MedicineItem] = []
    created_at:     datetime

    model_config = {"from_attributes": True}


class AppointmentCreate(BaseModel):
    patient_id:       int
    doctor_id:        int
    appointment_date: date
    appointment_time: time
    reason:           Optional[str] = None


class AppointmentUpdate(BaseModel):
    appointment_date: Optional[date] = None
    appointment_time: Optional[time] = None
    reason:           Optional[str] = None
    notes:            Optional[str] = None
    status:           Optional[AppointmentStatus] = None


class AppointmentResponse(BaseModel):
    id:               int
    patient_id:       int
    doctor_id:        int
    appointment_date: date
    appointment_time: time
    status:           AppointmentStatus
    reason:           Optional[str]
    notes:            Optional[str]
    token_number:     Optional[int]
    created_at:       datetime

    # nested name fields
    patient_name: Optional[str] = None
    doctor_name:  Optional[str] = None

    model_config = {"from_attributes": True}

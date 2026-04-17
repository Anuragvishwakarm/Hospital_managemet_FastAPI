from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import date, datetime, time

from app.database import get_db
from app.models.user import User, UserRole
from app.models.appointment import Appointment, AppointmentStatus, Prescription, PrescriptionMedicine
from app.models.doctor import DoctorProfile
from app.schemas.appointment import (
    AppointmentCreate, AppointmentUpdate, AppointmentResponse,
    PrescriptionCreate, PrescriptionResponse,
)
from app.utils.permissions import get_current_user, admin_or_receptionist, admin_or_doctor

router = APIRouter(prefix="/appointments", tags=["Appointments"])


# ── List appointments ─────────────────────────────────────────────────────────

@router.get("", response_model=List[AppointmentResponse])
def list_appointments(
    status:     Optional[AppointmentStatus] = Query(None),
    doctor_id:  Optional[int] = Query(None),
    patient_id: Optional[int] = Query(None),
    apt_date:   Optional[date] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = db.query(Appointment)

    # Scope by role
    if current_user.role == UserRole.patient:
        q = q.filter(Appointment.patient_id == current_user.id)
    elif current_user.role == UserRole.doctor:
        q = q.filter(Appointment.doctor_id == current_user.id)
    else:
        if doctor_id:
            q = q.filter(Appointment.doctor_id == doctor_id)
        if patient_id:
            q = q.filter(Appointment.patient_id == patient_id)

    if status:
        q = q.filter(Appointment.status == status)
    if apt_date:
        q = q.filter(Appointment.appointment_date == apt_date)

    apts = q.order_by(Appointment.appointment_date.desc(), Appointment.appointment_time).offset(skip).limit(limit).all()
    return [_build_response(a) for a in apts]


# ── Today's appointments ──────────────────────────────────────────────────────

@router.get("/today", response_model=List[AppointmentResponse])
def today_appointments(
    doctor_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    today = date.today()
    q = db.query(Appointment).filter(Appointment.appointment_date == today)

    if current_user.role == UserRole.doctor:
        q = q.filter(Appointment.doctor_id == current_user.id)
    elif doctor_id:
        q = q.filter(Appointment.doctor_id == doctor_id)

    apts = q.order_by(Appointment.appointment_time).all()
    return [_build_response(a) for a in apts]


# ── Available time slots ──────────────────────────────────────────────────────

@router.get("/available-slots")
def available_slots(
    doctor_id:  int  = Query(...),
    apt_date:   date = Query(...),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    # Fixed working slots: 09:00–13:00 and 17:00–20:00, every 30 min
    all_slots = []
    for h in range(9, 13):
        all_slots.append(time(h, 0))
        all_slots.append(time(h, 30))
    for h in range(17, 20):
        all_slots.append(time(h, 0))
        all_slots.append(time(h, 30))

    booked = db.query(Appointment.appointment_time).filter(
        Appointment.doctor_id == doctor_id,
        Appointment.appointment_date == apt_date,
        Appointment.status.notin_([AppointmentStatus.cancelled, AppointmentStatus.no_show]),
    ).all()
    booked_times = {r[0] for r in booked}

    return {
        "doctor_id": doctor_id,
        "date": apt_date,
        "slots": [
            {"time": s.strftime("%H:%M"), "available": s not in booked_times}
            for s in all_slots
        ],
    }


# ── Create appointment ────────────────────────────────────────────────────────

@router.post("", status_code=201, response_model=AppointmentResponse)
def create_appointment(
    payload: AppointmentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Validate doctor exists
    doctor = db.query(User).filter(User.id == payload.doctor_id, User.role == UserRole.doctor).first()
    if not doctor:
        raise HTTPException(404, "Doctor not found")

    # Validate patient exists
    patient = db.query(User).filter(User.id == payload.patient_id, User.role == UserRole.patient).first()
    if not patient:
        raise HTTPException(404, "Patient not found")

    # Check slot conflict
    conflict = db.query(Appointment).filter(
        Appointment.doctor_id == payload.doctor_id,
        Appointment.appointment_date == payload.appointment_date,
        Appointment.appointment_time == payload.appointment_time,
        Appointment.status.notin_([AppointmentStatus.cancelled, AppointmentStatus.no_show]),
    ).first()
    if conflict:
        raise HTTPException(409, "This time slot is already booked")

    # Assign token number for the day
    token = (
        db.query(Appointment)
        .filter(
            Appointment.doctor_id == payload.doctor_id,
            Appointment.appointment_date == payload.appointment_date,
        )
        .count()
    ) + 1

    apt = Appointment(
        patient_id=payload.patient_id,
        doctor_id=payload.doctor_id,
        appointment_date=payload.appointment_date,
        appointment_time=payload.appointment_time,
        reason=payload.reason,
        token_number=token,
        created_by=current_user.id,
    )
    db.add(apt)
    db.commit()
    db.refresh(apt)
    return _build_response(apt)


# ── Get single appointment ────────────────────────────────────────────────────

@router.get("/{apt_id}", response_model=AppointmentResponse)
def get_appointment(apt_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    apt = _get_or_404(apt_id, db)
    _check_access(apt, current_user)
    return _build_response(apt)


# ── Update appointment ────────────────────────────────────────────────────────

@router.put("/{apt_id}", response_model=AppointmentResponse)
def update_appointment(
    apt_id: int,
    payload: AppointmentUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    apt = _get_or_404(apt_id, db)
    _check_access(apt, current_user)

    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(apt, field, value)
    apt.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(apt)
    return _build_response(apt)


# ── Cancel appointment ────────────────────────────────────────────────────────

@router.put("/{apt_id}/cancel", response_model=AppointmentResponse)
def cancel_appointment(apt_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    apt = _get_or_404(apt_id, db)
    _check_access(apt, current_user)
    if apt.status == AppointmentStatus.completed:
        raise HTTPException(400, "Cannot cancel a completed appointment")
    apt.status = AppointmentStatus.cancelled
    apt.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(apt)
    return _build_response(apt)


# ── Complete appointment ──────────────────────────────────────────────────────

@router.put("/{apt_id}/complete", response_model=AppointmentResponse)
def complete_appointment(
    apt_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(admin_or_doctor),
):
    apt = _get_or_404(apt_id, db)
    if current_user.role == UserRole.doctor and apt.doctor_id != current_user.id:
        raise HTTPException(403, "Not your appointment")
    apt.status = AppointmentStatus.completed
    apt.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(apt)
    return _build_response(apt)


# ── Add / update prescription ─────────────────────────────────────────────────

@router.post("/{apt_id}/prescription", status_code=201, response_model=PrescriptionResponse)
def add_prescription(
    apt_id: int,
    payload: PrescriptionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(admin_or_doctor),
):
    apt = _get_or_404(apt_id, db)
    if current_user.role == UserRole.doctor and apt.doctor_id != current_user.id:
        raise HTTPException(403, "Not your appointment")

    if apt.prescription:
        raise HTTPException(400, "Prescription already exists. Use PUT to update.")

    rx = Prescription(
        appointment_id=apt_id,
        diagnosis=payload.diagnosis,
        notes=payload.notes,
        follow_up_date=payload.follow_up_date,
    )
    db.add(rx)
    db.flush()

    for med in payload.medicines:
        db.add(PrescriptionMedicine(prescription_id=rx.id, **med.model_dump()))

    db.commit()
    db.refresh(rx)
    return _build_rx_response(rx)


@router.get("/{apt_id}/prescription", response_model=PrescriptionResponse)
def get_prescription(apt_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    apt = _get_or_404(apt_id, db)
    _check_access(apt, current_user)
    if not apt.prescription:
        raise HTTPException(404, "No prescription found for this appointment")
    return _build_rx_response(apt.prescription)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _get_or_404(apt_id: int, db: Session) -> Appointment:
    apt = db.query(Appointment).filter(Appointment.id == apt_id).first()
    if not apt:
        raise HTTPException(404, "Appointment not found")
    return apt


def _check_access(apt: Appointment, user: User):
    if user.role == UserRole.patient and apt.patient_id != user.id:
        raise HTTPException(403, "Access denied")
    if user.role == UserRole.doctor and apt.doctor_id != user.id:
        raise HTTPException(403, "Access denied")


def _build_response(apt: Appointment) -> AppointmentResponse:
    return AppointmentResponse(
        id=apt.id,
        patient_id=apt.patient_id,
        doctor_id=apt.doctor_id,
        appointment_date=apt.appointment_date,
        appointment_time=apt.appointment_time,
        status=apt.status,
        reason=apt.reason,
        notes=apt.notes,
        token_number=apt.token_number,
        created_at=apt.created_at,
        patient_name=apt.patient.full_name if apt.patient else None,
        doctor_name=apt.doctor.full_name if apt.doctor else None,
    )


def _build_rx_response(rx: Prescription) -> PrescriptionResponse:
    from app.schemas.appointment import MedicineItem
    return PrescriptionResponse(
        id=rx.id,
        appointment_id=rx.appointment_id,
        diagnosis=rx.diagnosis,
        notes=rx.notes,
        follow_up_date=rx.follow_up_date,
        created_at=rx.created_at,
        medicines=[MedicineItem(**{
            "medicine_name": m.medicine_name,
            "dosage": m.dosage,
            "frequency": m.frequency,
            "duration": m.duration,
            "instructions": m.instructions,
        }) for m in rx.medicines],
    )

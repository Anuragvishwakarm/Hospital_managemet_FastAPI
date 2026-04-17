from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime

from app.database import get_db
from app.models.user import User, UserRole
from app.models.bed import Ward, Bed, Admission, BedStatus
from app.schemas.bed import (
    WardCreate, WardUpdate, WardResponse,
    BedCreate, BedUpdate, BedResponse,
    AdmissionCreate, DischargeInput, AdmissionResponse,
)
from app.utils.permissions import get_current_user, admin_only

router = APIRouter(prefix="/beds", tags=["Beds & Wards"])


def bed_access(current_user: User = Depends(get_current_user)) -> User:
    allowed = [UserRole.admin, UserRole.doctor, UserRole.receptionist]
    if current_user.role not in allowed:
        raise HTTPException(403, "Access denied")
    return current_user


# ── Wards ─────────────────────────────────────────────────────────────────────

@router.get("/wards", response_model=List[WardResponse])
def list_wards(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    wards = db.query(Ward).filter(Ward.is_active == True).all()
    return [_build_ward_response(w) for w in wards]


@router.post("/wards", status_code=201, response_model=WardResponse)
def create_ward(payload: WardCreate, db: Session = Depends(get_db), _: User = Depends(admin_only)):
    if db.query(Ward).filter(Ward.name == payload.name).first():
        raise HTTPException(400, "Ward with this name already exists")
    ward = Ward(**payload.model_dump())
    db.add(ward)
    db.commit()
    db.refresh(ward)
    return _build_ward_response(ward)


@router.put("/wards/{ward_id}", response_model=WardResponse)
def update_ward(ward_id: int, payload: WardUpdate, db: Session = Depends(get_db), _: User = Depends(admin_only)):
    ward = _get_ward_or_404(ward_id, db)
    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(ward, field, value)
    db.commit()
    db.refresh(ward)
    return _build_ward_response(ward)


# ── Beds ──────────────────────────────────────────────────────────────────────

@router.get("/", response_model=List[BedResponse])
def list_beds(
    ward_id: Optional[int] = Query(None),
    status:  Optional[BedStatus] = Query(None),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    q = db.query(Bed).filter(Bed.is_active == True)
    if ward_id:
        q = q.filter(Bed.ward_id == ward_id)
    if status:
        q = q.filter(Bed.status == status)
    return q.all()


@router.post("/", status_code=201, response_model=BedResponse)
def create_bed(payload: BedCreate, db: Session = Depends(get_db), _: User = Depends(admin_only)):
    _get_ward_or_404(payload.ward_id, db)
    if db.query(Bed).filter(Bed.ward_id == payload.ward_id, Bed.bed_number == payload.bed_number).first():
        raise HTTPException(400, "Bed number already exists in this ward")

    bed = Bed(ward_id=payload.ward_id, bed_number=payload.bed_number)
    db.add(bed)

    # Update ward total_beds count
    ward = _get_ward_or_404(payload.ward_id, db)
    ward.total_beds += 1

    db.commit()
    db.refresh(bed)
    return bed


@router.put("/{bed_id}", response_model=BedResponse)
def update_bed(bed_id: int, payload: BedUpdate, db: Session = Depends(get_db), _: User = Depends(bed_access)):
    bed = _get_bed_or_404(bed_id, db)
    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(bed, field, value)
    bed.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(bed)
    return bed


# ── Admissions ────────────────────────────────────────────────────────────────

@router.get("/admissions", response_model=List[AdmissionResponse])
def list_admissions(
    active_only: bool = Query(True),
    patient_id:  Optional[int] = Query(None),
    ward_id:     Optional[int] = Query(None),
    skip:  int = Query(0, ge=0),
    limit: int = Query(20, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role == UserRole.patient:
        patient_id = current_user.id

    q = db.query(Admission)
    if active_only:
        q = q.filter(Admission.is_active == True)
    if patient_id:
        q = q.filter(Admission.patient_id == patient_id)
    if ward_id:
        q = q.join(Bed).filter(Bed.ward_id == ward_id)

    admissions = q.order_by(Admission.admitted_at.desc()).offset(skip).limit(limit).all()
    return [_build_admission_response(a) for a in admissions]


@router.post("/admissions", status_code=201, response_model=AdmissionResponse)
def admit_patient(
    payload: AdmissionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(bed_access),
):
    # Validate patient
    patient = db.query(User).filter(User.id == payload.patient_id, User.role == UserRole.patient).first()
    if not patient:
        raise HTTPException(404, "Patient not found")

    # Validate bed availability
    bed = _get_bed_or_404(payload.bed_id, db)
    if bed.status != BedStatus.available:
        raise HTTPException(400, f"Bed is not available (status: {bed.status})")

    # Check patient not already admitted
    active = db.query(Admission).filter(
        Admission.patient_id == payload.patient_id,
        Admission.is_active == True,
    ).first()
    if active:
        raise HTTPException(400, "Patient is already admitted")

    admission = Admission(
        patient_id=payload.patient_id,
        bed_id=payload.bed_id,
        doctor_id=payload.doctor_id,
        admission_reason=payload.admission_reason,
        daily_charge=payload.daily_charge,
        created_by=current_user.id,
    )
    db.add(admission)

    bed.status = BedStatus.occupied
    bed.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(admission)
    return _build_admission_response(admission)


@router.put("/admissions/{admission_id}/discharge", response_model=AdmissionResponse)
def discharge_patient(
    admission_id: int,
    payload: DischargeInput,
    db: Session = Depends(get_db),
    _: User = Depends(bed_access),
):
    admission = db.query(Admission).filter(Admission.id == admission_id).first()
    if not admission:
        raise HTTPException(404, "Admission not found")
    if not admission.is_active:
        raise HTTPException(400, "Patient already discharged")

    admission.is_active      = False
    admission.discharged_at  = datetime.utcnow()
    admission.discharge_notes = payload.discharge_notes

    bed = admission.bed
    bed.status = BedStatus.available
    bed.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(admission)
    return _build_admission_response(admission)


# ── Occupancy summary ─────────────────────────────────────────────────────────

@router.get("/occupancy")
def bed_occupancy(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    total     = db.query(Bed).filter(Bed.is_active == True).count()
    occupied  = db.query(Bed).filter(Bed.status == BedStatus.occupied).count()
    available = db.query(Bed).filter(Bed.status == BedStatus.available).count()
    return {
        "total": total,
        "occupied": occupied,
        "available": available,
        "occupancy_percent": round((occupied / total * 100) if total else 0, 1),
    }


# ── Helpers ───────────────────────────────────────────────────────────────────

def _get_ward_or_404(ward_id: int, db: Session) -> Ward:
    w = db.query(Ward).filter(Ward.id == ward_id).first()
    if not w:
        raise HTTPException(404, "Ward not found")
    return w


def _get_bed_or_404(bed_id: int, db: Session) -> Bed:
    b = db.query(Bed).filter(Bed.id == bed_id).first()
    if not b:
        raise HTTPException(404, "Bed not found")
    return b


def _build_ward_response(w: Ward) -> WardResponse:
    occupied  = sum(1 for b in w.beds if b.status == BedStatus.occupied)
    available = sum(1 for b in w.beds if b.status == BedStatus.available)
    return WardResponse(
        id=w.id, name=w.name, ward_type=w.ward_type, floor=w.floor,
        total_beds=w.total_beds, is_active=w.is_active,
        beds=[BedResponse.model_validate(b) for b in w.beds],
        occupied=occupied, available=available,
    )


def _build_admission_response(a: Admission) -> AdmissionResponse:
    return AdmissionResponse(
        id=a.id, patient_id=a.patient_id, bed_id=a.bed_id, doctor_id=a.doctor_id,
        admitted_at=a.admitted_at, discharged_at=a.discharged_at,
        admission_reason=a.admission_reason, discharge_notes=a.discharge_notes,
        daily_charge=a.daily_charge, is_active=a.is_active,
        patient_name=a.patient.full_name if a.patient else None,
        bed_number=a.bed.bed_number if a.bed else None,
        ward_name=a.bed.ward.name if a.bed and a.bed.ward else None,
    )

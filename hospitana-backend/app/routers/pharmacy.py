from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
from decimal import Decimal

from app.database import get_db
from app.models.user import User, UserRole
from app.models.pharmacy import Medicine, MedicineBatch, DispenseOrder, DispenseItem
from app.schemas.pharmacy import (
    MedicineCreate, MedicineUpdate, MedicineResponse,
    BatchCreate, BatchResponse,
    DispenseCreate, DispenseResponse, DispenseItemResponse,
)
from app.utils.permissions import get_current_user

router = APIRouter(prefix="/pharmacy", tags=["Pharmacy"])


def pharmacy_access(current_user: User = Depends(get_current_user)) -> User:
    allowed = [UserRole.admin, UserRole.receptionist, UserRole.accountant, UserRole.doctor]
    if current_user.role not in allowed:
        raise HTTPException(403, "Access denied")
    return current_user


# ── Medicines CRUD ────────────────────────────────────────────────────────────

@router.get("/medicines", response_model=List[MedicineResponse])
def list_medicines(
    search:     Optional[str]  = Query(None),
    category:   Optional[str]  = Query(None),
    low_stock:  Optional[bool] = Query(None),
    skip:  int = Query(0, ge=0),
    limit: int = Query(50, le=200),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    q = db.query(Medicine).filter(Medicine.is_active == True)
    if search:
        q = q.filter(
            (Medicine.name.ilike(f"%{search}%")) | (Medicine.generic_name.ilike(f"%{search}%"))
        )
    if category:
        q = q.filter(Medicine.category.ilike(f"%{category}%"))

    meds = q.order_by(Medicine.name).offset(skip).limit(limit).all()

    if low_stock:
        meds = [m for m in meds if m.stock_quantity <= m.low_stock_threshold]

    return [_build_med_response(m) for m in meds]


@router.get("/medicines/low-stock", response_model=List[MedicineResponse])
def low_stock_medicines(db: Session = Depends(get_db), _: User = Depends(pharmacy_access)):
    meds = db.query(Medicine).filter(Medicine.is_active == True).all()
    return [_build_med_response(m) for m in meds if m.stock_quantity <= m.low_stock_threshold]


@router.get("/medicines/{med_id}", response_model=MedicineResponse)
def get_medicine(med_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    med = _get_med_or_404(med_id, db)
    return _build_med_response(med)


@router.post("/medicines", status_code=201, response_model=MedicineResponse)
def create_medicine(
    payload: MedicineCreate,
    db: Session = Depends(get_db),
    _: User = Depends(pharmacy_access),
):
    med = Medicine(**payload.model_dump())
    db.add(med)
    db.commit()
    db.refresh(med)
    return _build_med_response(med)


@router.put("/medicines/{med_id}", response_model=MedicineResponse)
def update_medicine(
    med_id: int,
    payload: MedicineUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(pharmacy_access),
):
    med = _get_med_or_404(med_id, db)
    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(med, field, value)
    med.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(med)
    return _build_med_response(med)


# ── Stock management ──────────────────────────────────────────────────────────

@router.post("/medicines/{med_id}/add-stock")
def add_stock(
    med_id: int,
    batch: BatchCreate,
    db: Session = Depends(get_db),
    _: User = Depends(pharmacy_access),
):
    med = _get_med_or_404(med_id, db)
    new_batch = MedicineBatch(medicine_id=med_id, **batch.model_dump())
    db.add(new_batch)
    med.stock_quantity += batch.quantity
    med.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(new_batch)
    return {"message": "Stock added", "new_total": med.stock_quantity, "batch_id": new_batch.id}


@router.get("/medicines/{med_id}/batches", response_model=List[BatchResponse])
def list_batches(med_id: int, db: Session = Depends(get_db), _: User = Depends(pharmacy_access)):
    _get_med_or_404(med_id, db)
    return db.query(MedicineBatch).filter(MedicineBatch.medicine_id == med_id).all()


# ── Dispense orders ───────────────────────────────────────────────────────────

@router.get("/dispense", response_model=List[DispenseResponse])
def list_dispense_orders(
    patient_id: Optional[int] = Query(None),
    skip:  int = Query(0, ge=0),
    limit: int = Query(20, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role == UserRole.patient:
        patient_id = current_user.id

    q = db.query(DispenseOrder)
    if patient_id:
        q = q.filter(DispenseOrder.patient_id == patient_id)

    orders = q.order_by(DispenseOrder.dispensed_at.desc()).offset(skip).limit(limit).all()
    return [_build_dispense_response(o) for o in orders]


@router.post("/dispense", status_code=201, response_model=DispenseResponse)
def dispense_medicines(
    payload: DispenseCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(pharmacy_access),
):
    total = Decimal("0")
    items_data = []

    for item in payload.items:
        med = _get_med_or_404(item.medicine_id, db)
        if med.stock_quantity < item.quantity:
            raise HTTPException(400, f"Insufficient stock for '{med.name}'. Available: {med.stock_quantity}")
        line_total = med.price_per_unit * item.quantity
        total += line_total
        items_data.append((med, item.quantity, med.price_per_unit, line_total))

    order = DispenseOrder(
        patient_id=payload.patient_id,
        prescription_id=payload.prescription_id,
        dispensed_by=current_user.id,
        total_amount=total,
        notes=payload.notes,
    )
    db.add(order)
    db.flush()

    for med, qty, price, line_total in items_data:
        db.add(DispenseItem(
            order_id=order.id,
            medicine_id=med.id,
            quantity=qty,
            unit_price=price,
            total_price=line_total,
        ))
        med.stock_quantity -= qty
        med.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(order)
    return _build_dispense_response(order)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _get_med_or_404(med_id: int, db: Session) -> Medicine:
    med = db.query(Medicine).filter(Medicine.id == med_id).first()
    if not med:
        raise HTTPException(404, "Medicine not found")
    return med


def _build_med_response(m: Medicine) -> MedicineResponse:
    return MedicineResponse(
        id=m.id,
        name=m.name,
        generic_name=m.generic_name,
        category=m.category,
        manufacturer=m.manufacturer,
        unit=m.unit,
        price_per_unit=m.price_per_unit,
        stock_quantity=m.stock_quantity,
        low_stock_threshold=m.low_stock_threshold,
        is_active=m.is_active,
        gst_percent=m.gst_percent,
        is_low_stock=m.stock_quantity <= m.low_stock_threshold,
    )


def _build_dispense_response(o: DispenseOrder) -> DispenseResponse:
    return DispenseResponse(
        id=o.id,
        patient_id=o.patient_id,
        total_amount=o.total_amount,
        dispensed_at=o.dispensed_at,
        items=[
            DispenseItemResponse(
                id=i.id,
                medicine_id=i.medicine_id,
                quantity=i.quantity,
                unit_price=i.unit_price,
                total_price=i.total_price,
                medicine_name=i.medicine.name if i.medicine else None,
            )
            for i in o.items
        ],
    )

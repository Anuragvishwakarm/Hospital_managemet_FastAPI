from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime

from app.database import get_db
from app.models.user import User, UserRole
from app.models.laboratory import LabTest, LabOrder, LabOrderItem, LabOrderStatus
from app.schemas.laboratory import (
    LabTestCreate, LabTestUpdate, LabTestResponse,
    LabOrderCreate, LabResultInput,
    LabOrderResponse, LabOrderItemResponse,
)
from app.utils.permissions import get_current_user

router = APIRouter(prefix="/laboratory", tags=["Laboratory"])


def lab_access(current_user: User = Depends(get_current_user)) -> User:
    allowed = [UserRole.admin, UserRole.doctor, UserRole.receptionist]
    if current_user.role not in allowed:
        raise HTTPException(403, "Access denied")
    return current_user


# ── Lab tests catalog ─────────────────────────────────────────────────────────

@router.get("/tests", response_model=List[LabTestResponse])
def list_tests(
    category: Optional[str] = Query(None),
    search:   Optional[str] = Query(None),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    q = db.query(LabTest).filter(LabTest.is_active == True)
    if category:
        q = q.filter(LabTest.category.ilike(f"%{category}%"))
    if search:
        q = q.filter(LabTest.name.ilike(f"%{search}%"))
    return q.order_by(LabTest.name).all()


@router.post("/tests", status_code=201, response_model=LabTestResponse)
def create_test(
    payload: LabTestCreate,
    db: Session = Depends(get_db),
    _: User = Depends(lab_access),
):
    if payload.code and db.query(LabTest).filter(LabTest.code == payload.code).first():
        raise HTTPException(400, "Test code already exists")
    test = LabTest(**payload.model_dump())
    db.add(test)
    db.commit()
    db.refresh(test)
    return test


@router.put("/tests/{test_id}", response_model=LabTestResponse)
def update_test(
    test_id: int,
    payload: LabTestUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(lab_access),
):
    test = db.query(LabTest).filter(LabTest.id == test_id).first()
    if not test:
        raise HTTPException(404, "Lab test not found")
    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(test, field, value)
    db.commit()
    db.refresh(test)
    return test


@router.get("/tests/categories")
def list_categories(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    rows = db.query(LabTest.category).filter(LabTest.is_active == True).distinct().all()
    return {"categories": [r[0] for r in rows if r[0]]}


# ── Lab orders ────────────────────────────────────────────────────────────────

@router.get("/orders", response_model=List[LabOrderResponse])
def list_orders(
    status:     Optional[LabOrderStatus] = Query(None),
    patient_id: Optional[int] = Query(None),
    skip:  int = Query(0, ge=0),
    limit: int = Query(20, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role == UserRole.patient:
        patient_id = current_user.id

    q = db.query(LabOrder)
    if patient_id:
        q = q.filter(LabOrder.patient_id == patient_id)
    if status:
        q = q.filter(LabOrder.status == status)

    orders = q.order_by(LabOrder.created_at.desc()).offset(skip).limit(limit).all()
    return [_build_order_response(o) for o in orders]


@router.post("/orders", status_code=201, response_model=LabOrderResponse)
def create_order(
    payload: LabOrderCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(lab_access),
):
    patient = db.query(User).filter(User.id == payload.patient_id, User.role == UserRole.patient).first()
    if not patient:
        raise HTTPException(404, "Patient not found")

    order = LabOrder(
        patient_id=payload.patient_id,
        doctor_id=payload.doctor_id,
        appointment_id=payload.appointment_id,
        notes=payload.notes,
        created_by=current_user.id,
    )
    db.add(order)
    db.flush()

    for test_id in payload.test_ids:
        test = db.query(LabTest).filter(LabTest.id == test_id).first()
        if not test:
            raise HTTPException(404, f"Lab test {test_id} not found")
        db.add(LabOrderItem(order_id=order.id, test_id=test_id))

    db.commit()
    db.refresh(order)
    return _build_order_response(order)


@router.get("/orders/{order_id}", response_model=LabOrderResponse)
def get_order(order_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    order = _get_order_or_404(order_id, db)
    if current_user.role == UserRole.patient and order.patient_id != current_user.id:
        raise HTTPException(403, "Access denied")
    return _build_order_response(order)


# ── Status transitions ────────────────────────────────────────────────────────

@router.put("/orders/{order_id}/collect-sample")
def collect_sample(order_id: int, db: Session = Depends(get_db), _: User = Depends(lab_access)):
    order = _get_order_or_404(order_id, db)
    if order.status != LabOrderStatus.ordered:
        raise HTTPException(400, f"Cannot collect sample — current status: {order.status}")
    order.status = LabOrderStatus.sample_collected
    order.sample_collected_at = datetime.utcnow()
    order.updated_at = datetime.utcnow()
    db.commit()
    return {"message": "Sample collected", "order_id": order_id}


@router.put("/orders/{order_id}/start-processing")
def start_processing(order_id: int, db: Session = Depends(get_db), _: User = Depends(lab_access)):
    order = _get_order_or_404(order_id, db)
    if order.status != LabOrderStatus.sample_collected:
        raise HTTPException(400, "Collect sample first")
    order.status = LabOrderStatus.processing
    order.updated_at = datetime.utcnow()
    db.commit()
    return {"message": "Processing started", "order_id": order_id}


@router.put("/orders/{order_id}/results", response_model=LabOrderResponse)
def enter_results(
    order_id: int,
    results: List[LabResultInput],
    db: Session = Depends(get_db),
    _: User = Depends(lab_access),
):
    order = _get_order_or_404(order_id, db)
    if order.status not in [LabOrderStatus.processing, LabOrderStatus.sample_collected]:
        raise HTTPException(400, "Order must be in processing or sample_collected state")

    result_map = {r.test_id: r for r in results}
    for item in order.items:
        if item.test_id in result_map:
            r = result_map[item.test_id]
            item.result      = r.result
            item.is_abnormal = r.is_abnormal or False
            item.remarks     = r.remarks
            item.tested_at   = datetime.utcnow()

    order.status = LabOrderStatus.completed
    order.completed_at = datetime.utcnow()
    order.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(order)
    return _build_order_response(order)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _get_order_or_404(order_id: int, db: Session) -> LabOrder:
    order = db.query(LabOrder).filter(LabOrder.id == order_id).first()
    if not order:
        raise HTTPException(404, "Lab order not found")
    return order


def _build_order_response(o: LabOrder) -> LabOrderResponse:
    return LabOrderResponse(
        id=o.id,
        patient_id=o.patient_id,
        doctor_id=o.doctor_id,
        appointment_id=o.appointment_id,
        status=o.status,
        sample_collected_at=o.sample_collected_at,
        completed_at=o.completed_at,
        notes=o.notes,
        created_at=o.created_at,
        patient_name=o.patient.full_name if o.patient else None,
        items=[
            LabOrderItemResponse(
                id=i.id,
                test_id=i.test_id,
                result=i.result,
                is_abnormal=i.is_abnormal,
                remarks=i.remarks,
                tested_at=i.tested_at,
                test_name=i.test.name if i.test else None,
            )
            for i in o.items
        ],
    )

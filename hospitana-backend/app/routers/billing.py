from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional
from datetime import datetime, date
from decimal import Decimal
import random, string

from app.database import get_db
from app.models.user import User, UserRole
from app.models.billing import Bill, BillItem, Payment, BillStatus
from app.schemas.billing import (
    BillCreate, PaymentCreate,
    BillResponse, BillSummary, PaymentResponse,
)
from app.utils.permissions import get_current_user, admin_only, accountant_only

router = APIRouter(prefix="/billing", tags=["Billing"])

# Both admin and accountant can access billing
def billing_access(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role not in [UserRole.admin, UserRole.accountant, UserRole.receptionist]:
        raise HTTPException(403, "Access denied")
    return current_user


# ── Stats ─────────────────────────────────────────────────────────────────────

@router.get("/stats")
def billing_stats(db: Session = Depends(get_db), _: User = Depends(billing_access)):
    today = date.today()
    total_bills    = db.query(Bill).count()
    pending_amount = db.query(func.sum(Bill.due_amount)).filter(
        Bill.status.in_([BillStatus.pending, BillStatus.partial])
    ).scalar() or 0
    today_collection = db.query(func.sum(Payment.amount)).filter(
        func.date(Payment.paid_at) == today
    ).scalar() or 0
    total_revenue = db.query(func.sum(Payment.amount)).scalar() or 0

    return {
        "total_bills":       total_bills,
        "pending_amount":    float(pending_amount),
        "today_collection":  float(today_collection),
        "total_revenue":     float(total_revenue),
    }


# ── List bills ────────────────────────────────────────────────────────────────

@router.get("", response_model=List[BillSummary])
def list_bills(
    status:     Optional[BillStatus] = Query(None),
    patient_id: Optional[int] = Query(None),
    skip:  int = Query(0, ge=0),
    limit: int = Query(20, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Patients can only see their own bills
    if current_user.role == UserRole.patient:
        patient_id = current_user.id

    q = db.query(Bill)
    if patient_id:
        q = q.filter(Bill.patient_id == patient_id)
    if status:
        q = q.filter(Bill.status == status)

    bills = q.order_by(Bill.created_at.desc()).offset(skip).limit(limit).all()
    return [_bill_summary(b) for b in bills]


# ── Get single bill ───────────────────────────────────────────────────────────

@router.get("/{bill_id}", response_model=BillResponse)
def get_bill(bill_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    bill = _get_or_404(bill_id, db)
    if current_user.role == UserRole.patient and bill.patient_id != current_user.id:
        raise HTTPException(403, "Access denied")
    return _build_response(bill)


# ── Create bill ───────────────────────────────────────────────────────────────

@router.post("", status_code=201, response_model=BillResponse)
def create_bill(
    payload: BillCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(billing_access),
):
    patient = db.query(User).filter(User.id == payload.patient_id, User.role == UserRole.patient).first()
    if not patient:
        raise HTTPException(404, "Patient not found")

    # Calculate totals
    subtotal = sum(item.unit_price * item.quantity for item in payload.items)
    discount = payload.discount or Decimal("0")
    taxable  = subtotal - discount
    gst_pct  = payload.gst_percent or Decimal("18")
    gst_amt  = (taxable * gst_pct / 100).quantize(Decimal("0.01"))
    total    = taxable + gst_amt

    bill = Bill(
        bill_number=_generate_bill_number(db),
        patient_id=payload.patient_id,
        appointment_id=payload.appointment_id,
        subtotal=subtotal,
        discount=discount,
        gst_percent=gst_pct,
        gst_amount=gst_amt,
        total_amount=total,
        paid_amount=Decimal("0"),
        due_amount=total,
        notes=payload.notes,
        created_by=current_user.id,
    )
    db.add(bill)
    db.flush()

    for item in payload.items:
        db.add(BillItem(
            bill_id=bill.id,
            description=item.description,
            category=item.category,
            quantity=item.quantity,
            unit_price=item.unit_price,
            total_price=item.unit_price * item.quantity,
        ))

    db.commit()
    db.refresh(bill)
    return _build_response(bill)


# ── Record payment ────────────────────────────────────────────────────────────

@router.post("/{bill_id}/pay", response_model=BillResponse)
def record_payment(
    bill_id: int,
    payload: PaymentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(billing_access),
):
    bill = _get_or_404(bill_id, db)
    if bill.status == BillStatus.paid:
        raise HTTPException(400, "Bill is already fully paid")
    if bill.status == BillStatus.cancelled:
        raise HTTPException(400, "Cannot pay a cancelled bill")
    if payload.amount > bill.due_amount:
        raise HTTPException(400, f"Payment amount exceeds due amount ({bill.due_amount})")

    payment = Payment(
        bill_id=bill.id,
        amount=payload.amount,
        payment_mode=payload.payment_mode,
        reference_no=payload.reference_no,
        notes=payload.notes,
        received_by=current_user.id,
    )
    db.add(payment)

    bill.paid_amount += payload.amount
    bill.due_amount  -= payload.amount
    bill.status = BillStatus.paid if bill.due_amount <= 0 else BillStatus.partial
    bill.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(bill)
    return _build_response(bill)


# ── Cancel bill ───────────────────────────────────────────────────────────────

@router.put("/{bill_id}/cancel", response_model=BillResponse)
def cancel_bill(
    bill_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(billing_access),
):
    bill = _get_or_404(bill_id, db)
    if bill.status == BillStatus.paid:
        raise HTTPException(400, "Cannot cancel a paid bill")
    bill.status = BillStatus.cancelled
    bill.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(bill)
    return _build_response(bill)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _get_or_404(bill_id: int, db: Session) -> Bill:
    bill = db.query(Bill).filter(Bill.id == bill_id).first()
    if not bill:
        raise HTTPException(404, "Bill not found")
    return bill


def _generate_bill_number(db: Session) -> str:
    prefix = f"SAH{datetime.utcnow().strftime('%y%m')}"
    while True:
        num = prefix + "".join(random.choices(string.digits, k=4))
        if not db.query(Bill).filter(Bill.bill_number == num).first():
            return num


def _bill_summary(b: Bill) -> BillSummary:
    return BillSummary(
        id=b.id,
        bill_number=b.bill_number,
        patient_id=b.patient_id,
        patient_name=b.patient.full_name if b.patient else None,
        status=b.status,
        total_amount=b.total_amount,
        due_amount=b.due_amount,
        created_at=b.created_at,
    )


def _build_response(b: Bill) -> BillResponse:
    from app.schemas.billing import BillItemResponse, PaymentResponse as PRsp
    return BillResponse(
        id=b.id,
        bill_number=b.bill_number,
        patient_id=b.patient_id,
        appointment_id=b.appointment_id,
        status=b.status,
        subtotal=b.subtotal,
        discount=b.discount,
        gst_percent=b.gst_percent,
        gst_amount=b.gst_amount,
        total_amount=b.total_amount,
        paid_amount=b.paid_amount,
        due_amount=b.due_amount,
        notes=b.notes,
        created_at=b.created_at,
        patient_name=b.patient.full_name if b.patient else None,
        items=[BillItemResponse.model_validate(i) for i in b.items],
        payments=[PRsp.model_validate(p) for p in b.payments],
    )

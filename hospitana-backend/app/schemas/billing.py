from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from decimal import Decimal
from app.models.billing import BillStatus, PaymentMode


class BillItemCreate(BaseModel):
    description: str
    category:    Optional[str] = None
    quantity:    int = 1
    unit_price:  Decimal


class BillCreate(BaseModel):
    patient_id:     int
    appointment_id: Optional[int] = None
    items:          List[BillItemCreate]
    discount:       Optional[Decimal] = Decimal("0")
    gst_percent:    Optional[Decimal] = Decimal("18")
    notes:          Optional[str] = None


class PaymentCreate(BaseModel):
    amount:       Decimal
    payment_mode: PaymentMode
    reference_no: Optional[str] = None
    notes:        Optional[str] = None


class BillItemResponse(BaseModel):
    id:          int
    description: str
    category:    Optional[str]
    quantity:    int
    unit_price:  Decimal
    total_price: Decimal

    model_config = {"from_attributes": True}


class PaymentResponse(BaseModel):
    id:           int
    amount:       Decimal
    payment_mode: PaymentMode
    reference_no: Optional[str]
    paid_at:      datetime

    model_config = {"from_attributes": True}


class BillResponse(BaseModel):
    id:             int
    bill_number:    str
    patient_id:     int
    appointment_id: Optional[int]
    status:         BillStatus
    subtotal:       Decimal
    discount:       Decimal
    gst_percent:    Decimal
    gst_amount:     Decimal
    total_amount:   Decimal
    paid_amount:    Decimal
    due_amount:     Decimal
    notes:          Optional[str]
    created_at:     datetime
    items:          List[BillItemResponse] = []
    payments:       List[PaymentResponse] = []
    patient_name:   Optional[str] = None

    model_config = {"from_attributes": True}


class BillSummary(BaseModel):
    id:           int
    bill_number:  str
    patient_id:   int
    patient_name: Optional[str]
    status:       BillStatus
    total_amount: Decimal
    due_amount:   Decimal
    created_at:   datetime

    model_config = {"from_attributes": True}

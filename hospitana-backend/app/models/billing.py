from sqlalchemy import Column, Integer, String, Text, Numeric, DateTime, ForeignKey, Enum as SAEnum, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

from app.database import Base


class BillStatus(str, enum.Enum):
    draft    = "draft"
    pending  = "pending"
    partial  = "partial"
    paid     = "paid"
    cancelled = "cancelled"


class PaymentMode(str, enum.Enum):
    cash      = "cash"
    upi       = "upi"
    card      = "card"
    insurance = "insurance"
    online    = "online"


class Bill(Base):
    __tablename__ = "bills"

    id             = Column(Integer, primary_key=True, index=True)
    bill_number    = Column(String(20), unique=True, nullable=False)
    patient_id     = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    appointment_id = Column(Integer, ForeignKey("appointments.id"), nullable=True)
    status         = Column(SAEnum(BillStatus), default=BillStatus.pending)
    subtotal       = Column(Numeric(10, 2), default=0)
    discount       = Column(Numeric(10, 2), default=0)
    gst_percent    = Column(Numeric(5, 2), default=18)    # GST %
    gst_amount     = Column(Numeric(10, 2), default=0)
    total_amount   = Column(Numeric(10, 2), default=0)
    paid_amount    = Column(Numeric(10, 2), default=0)
    due_amount     = Column(Numeric(10, 2), default=0)
    notes          = Column(Text, nullable=True)
    created_by     = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at     = Column(DateTime, default=datetime.utcnow)
    updated_at     = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    patient     = relationship("User", foreign_keys=[patient_id])
    creator     = relationship("User", foreign_keys=[created_by])
    appointment = relationship("Appointment", foreign_keys=[appointment_id])
    items       = relationship("BillItem", back_populates="bill", cascade="all, delete-orphan")
    payments    = relationship("Payment", back_populates="bill", cascade="all, delete-orphan")


class BillItem(Base):
    __tablename__ = "bill_items"

    id          = Column(Integer, primary_key=True, index=True)
    bill_id     = Column(Integer, ForeignKey("bills.id", ondelete="CASCADE"), nullable=False)
    description = Column(String(300), nullable=False)
    category    = Column(String(100), nullable=True)   # consultation / lab / medicine / procedure
    quantity    = Column(Integer, default=1)
    unit_price  = Column(Numeric(10, 2), nullable=False)
    total_price = Column(Numeric(10, 2), nullable=False)

    bill = relationship("Bill", back_populates="items")


class Payment(Base):
    __tablename__ = "payments"

    id           = Column(Integer, primary_key=True, index=True)
    bill_id      = Column(Integer, ForeignKey("bills.id", ondelete="CASCADE"), nullable=False)
    amount       = Column(Numeric(10, 2), nullable=False)
    payment_mode = Column(SAEnum(PaymentMode), nullable=False)
    reference_no = Column(String(100), nullable=True)   # UPI txn id / card last4
    paid_at      = Column(DateTime, default=datetime.utcnow)
    received_by  = Column(Integer, ForeignKey("users.id"), nullable=True)
    notes        = Column(Text, nullable=True)

    bill     = relationship("Bill", back_populates="payments")
    receiver = relationship("User", foreign_keys=[received_by])

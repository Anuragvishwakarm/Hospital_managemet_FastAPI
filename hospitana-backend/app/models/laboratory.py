from sqlalchemy import Column, Integer, String, Text, Numeric, DateTime, ForeignKey, Enum as SAEnum, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

from app.database import Base


class LabOrderStatus(str, enum.Enum):
    ordered    = "ordered"
    sample_collected = "sample_collected"
    processing = "processing"
    completed  = "completed"
    cancelled  = "cancelled"


class LabTest(Base):
    __tablename__ = "lab_tests"

    id           = Column(Integer, primary_key=True, index=True)
    name         = Column(String(200), nullable=False, index=True)
    code         = Column(String(50), unique=True, nullable=True)
    category     = Column(String(100), nullable=True)   # Haematology / Biochemistry / etc.
    price        = Column(Numeric(10, 2), default=0)
    normal_range = Column(String(200), nullable=True)
    unit         = Column(String(50), nullable=True)    # mg/dL, g/L, etc.
    description  = Column(Text, nullable=True)
    is_active    = Column(Boolean, default=True)
    created_at   = Column(DateTime, default=datetime.utcnow)

    order_items = relationship("LabOrderItem", back_populates="test")


class LabOrder(Base):
    __tablename__ = "lab_orders"

    id             = Column(Integer, primary_key=True, index=True)
    patient_id     = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    doctor_id      = Column(Integer, ForeignKey("users.id"), nullable=True)
    appointment_id = Column(Integer, ForeignKey("appointments.id"), nullable=True)
    status         = Column(SAEnum(LabOrderStatus), default=LabOrderStatus.ordered)
    sample_collected_at = Column(DateTime, nullable=True)
    completed_at   = Column(DateTime, nullable=True)
    notes          = Column(Text, nullable=True)
    created_by     = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at     = Column(DateTime, default=datetime.utcnow)
    updated_at     = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    patient  = relationship("User", foreign_keys=[patient_id])
    doctor   = relationship("User", foreign_keys=[doctor_id])
    creator  = relationship("User", foreign_keys=[created_by])
    items    = relationship("LabOrderItem", back_populates="order", cascade="all, delete-orphan")


class LabOrderItem(Base):
    __tablename__ = "lab_order_items"

    id        = Column(Integer, primary_key=True, index=True)
    order_id  = Column(Integer, ForeignKey("lab_orders.id", ondelete="CASCADE"), nullable=False)
    test_id   = Column(Integer, ForeignKey("lab_tests.id"), nullable=False)
    result    = Column(Text, nullable=True)
    is_abnormal = Column(Boolean, default=False)
    remarks   = Column(String(300), nullable=True)
    tested_at = Column(DateTime, nullable=True)

    order = relationship("LabOrder", back_populates="items")
    test  = relationship("LabTest", back_populates="order_items")

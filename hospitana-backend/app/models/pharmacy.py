from sqlalchemy import Column, Integer, String, Numeric, DateTime, Date, ForeignKey, Enum as SAEnum, Boolean, Text
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

from app.database import Base


class Medicine(Base):
    __tablename__ = "medicines"

    id             = Column(Integer, primary_key=True, index=True)
    name           = Column(String(200), nullable=False, index=True)
    generic_name   = Column(String(200), nullable=True)
    category       = Column(String(100), nullable=True)   # tablet / syrup / injection / etc.
    manufacturer   = Column(String(200), nullable=True)
    unit           = Column(String(50), default="strip")  # strip / bottle / vial
    price_per_unit = Column(Numeric(10, 2), default=0)
    stock_quantity = Column(Integer, default=0)
    low_stock_threshold = Column(Integer, default=10)
    is_active      = Column(Boolean, default=True)
    hsn_code       = Column(String(20), nullable=True)    # for GST
    gst_percent    = Column(Numeric(5, 2), default=12)
    created_at     = Column(DateTime, default=datetime.utcnow)
    updated_at     = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    batches        = relationship("MedicineBatch", back_populates="medicine", cascade="all, delete-orphan")
    dispense_items = relationship("DispenseItem", back_populates="medicine")


class MedicineBatch(Base):
    __tablename__ = "medicine_batches"

    id            = Column(Integer, primary_key=True, index=True)
    medicine_id   = Column(Integer, ForeignKey("medicines.id", ondelete="CASCADE"), nullable=False)
    batch_number  = Column(String(100), nullable=False)
    expiry_date   = Column(Date, nullable=False)
    quantity      = Column(Integer, default=0)
    purchase_price = Column(Numeric(10, 2), default=0)
    created_at    = Column(DateTime, default=datetime.utcnow)

    medicine = relationship("Medicine", back_populates="batches")


class DispenseOrder(Base):
    __tablename__ = "dispense_orders"

    id              = Column(Integer, primary_key=True, index=True)
    patient_id      = Column(Integer, ForeignKey("users.id"), nullable=False)
    prescription_id = Column(Integer, ForeignKey("prescriptions.id"), nullable=True)
    dispensed_by    = Column(Integer, ForeignKey("users.id"), nullable=True)
    total_amount    = Column(Numeric(10, 2), default=0)
    notes           = Column(Text, nullable=True)
    dispensed_at    = Column(DateTime, default=datetime.utcnow)

    patient  = relationship("User", foreign_keys=[patient_id])
    dispenser = relationship("User", foreign_keys=[dispensed_by])
    items    = relationship("DispenseItem", back_populates="order", cascade="all, delete-orphan")


class DispenseItem(Base):
    __tablename__ = "dispense_items"

    id          = Column(Integer, primary_key=True, index=True)
    order_id    = Column(Integer, ForeignKey("dispense_orders.id", ondelete="CASCADE"), nullable=False)
    medicine_id = Column(Integer, ForeignKey("medicines.id"), nullable=False)
    quantity    = Column(Integer, nullable=False)
    unit_price  = Column(Numeric(10, 2), nullable=False)
    total_price = Column(Numeric(10, 2), nullable=False)

    order    = relationship("DispenseOrder", back_populates="items")
    medicine = relationship("Medicine", back_populates="dispense_items")

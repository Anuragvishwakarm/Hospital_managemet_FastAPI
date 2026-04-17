from sqlalchemy import Column, Integer, String, Text, DateTime, Date, ForeignKey, Enum as SAEnum, Boolean, Numeric
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

from app.database import Base


class BedStatus(str, enum.Enum):
    available  = "available"
    occupied   = "occupied"
    reserved   = "reserved"
    maintenance = "maintenance"


class Ward(Base):
    __tablename__ = "wards"

    id         = Column(Integer, primary_key=True, index=True)
    name       = Column(String(100), nullable=False, unique=True)   # General / ICU / NICU / etc.
    ward_type  = Column(String(100), nullable=True)
    floor      = Column(Integer, default=1)
    total_beds = Column(Integer, default=0)
    is_active  = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    beds = relationship("Bed", back_populates="ward", cascade="all, delete-orphan")


class Bed(Base):
    __tablename__ = "beds"

    id         = Column(Integer, primary_key=True, index=True)
    ward_id    = Column(Integer, ForeignKey("wards.id", ondelete="CASCADE"), nullable=False)
    bed_number = Column(String(20), nullable=False)
    status     = Column(SAEnum(BedStatus), default=BedStatus.available)
    is_active  = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    ward        = relationship("Ward", back_populates="beds")
    admissions  = relationship("Admission", back_populates="bed")


class Admission(Base):
    __tablename__ = "admissions"

    id              = Column(Integer, primary_key=True, index=True)
    patient_id      = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    bed_id          = Column(Integer, ForeignKey("beds.id"), nullable=False)
    doctor_id       = Column(Integer, ForeignKey("users.id"), nullable=True)
    admitted_at     = Column(DateTime, default=datetime.utcnow)
    discharged_at   = Column(DateTime, nullable=True)
    admission_reason = Column(Text, nullable=True)
    discharge_notes  = Column(Text, nullable=True)
    daily_charge    = Column(Numeric(10, 2), default=0)
    is_active       = Column(Boolean, default=True)  # True = currently admitted
    created_by      = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at      = Column(DateTime, default=datetime.utcnow)

    patient  = relationship("User", foreign_keys=[patient_id])
    doctor   = relationship("User", foreign_keys=[doctor_id])
    creator  = relationship("User", foreign_keys=[created_by])
    bed      = relationship("Bed", back_populates="admissions")

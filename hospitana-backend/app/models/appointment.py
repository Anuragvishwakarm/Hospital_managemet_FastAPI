from sqlalchemy import Column, Integer, String, Text, Date, Time, DateTime, ForeignKey, Enum as SAEnum
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

from app.database import Base


class AppointmentStatus(str, enum.Enum):
    scheduled  = "scheduled"
    confirmed  = "confirmed"
    in_progress = "in_progress"
    completed  = "completed"
    cancelled  = "cancelled"
    no_show    = "no_show"


class Appointment(Base):
    __tablename__ = "appointments"

    id              = Column(Integer, primary_key=True, index=True)
    patient_id      = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    doctor_id       = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    appointment_date = Column(Date, nullable=False)
    appointment_time = Column(Time, nullable=False)
    status          = Column(SAEnum(AppointmentStatus), default=AppointmentStatus.scheduled)
    reason          = Column(Text, nullable=True)
    notes           = Column(Text, nullable=True)       # doctor's notes after visit
    token_number    = Column(Integer, nullable=True)
    created_by      = Column(Integer, ForeignKey("users.id"), nullable=True)  # receptionist/patient
    created_at      = Column(DateTime, default=datetime.utcnow)
    updated_at      = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    patient    = relationship("User", foreign_keys=[patient_id])
    doctor     = relationship("User", foreign_keys=[doctor_id])
    creator    = relationship("User", foreign_keys=[created_by])
    prescription = relationship("Prescription", back_populates="appointment", uselist=False)


class Prescription(Base):
    __tablename__ = "prescriptions"

    id             = Column(Integer, primary_key=True, index=True)
    appointment_id = Column(Integer, ForeignKey("appointments.id", ondelete="CASCADE"), unique=True, nullable=False)
    diagnosis      = Column(Text, nullable=True)
    notes          = Column(Text, nullable=True)
    follow_up_date = Column(Date, nullable=True)
    created_at     = Column(DateTime, default=datetime.utcnow)
    updated_at     = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    appointment  = relationship("Appointment", back_populates="prescription")
    medicines    = relationship("PrescriptionMedicine", back_populates="prescription", cascade="all, delete-orphan")


class PrescriptionMedicine(Base):
    __tablename__ = "prescription_medicines"

    id              = Column(Integer, primary_key=True, index=True)
    prescription_id = Column(Integer, ForeignKey("prescriptions.id", ondelete="CASCADE"), nullable=False)
    medicine_name   = Column(String(200), nullable=False)
    dosage          = Column(String(100), nullable=True)   # e.g. "500mg"
    frequency       = Column(String(100), nullable=True)   # e.g. "1-0-1"
    duration        = Column(String(100), nullable=True)   # e.g. "5 days"
    instructions    = Column(String(255), nullable=True)   # e.g. "After meals"

    prescription = relationship("Prescription", back_populates="medicines")

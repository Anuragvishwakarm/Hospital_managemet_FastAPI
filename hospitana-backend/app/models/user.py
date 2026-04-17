from sqlalchemy import Column, Integer, String, Boolean, DateTime, Enum as SAEnum
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

from app.database import Base


class UserRole(str, enum.Enum):
    admin        = "admin"
    doctor       = "doctor"
    receptionist = "receptionist"
    patient      = "patient"
    accountant   = "accountant"


class User(Base):
    __tablename__ = "users"

    id           = Column(Integer, primary_key=True, index=True)
    first_name   = Column(String(100), nullable=False)
    last_name    = Column(String(100), nullable=False)
    email        = Column(String(255), unique=True, index=True, nullable=False)
    phone        = Column(String(15), unique=True, index=True, nullable=False)
    password     = Column(String(255), nullable=False)
    role         = Column(SAEnum(UserRole), default=UserRole.patient, nullable=False)
    is_active    = Column(Boolean, default=False)   # False until admin approves (staff)
    is_verified  = Column(Boolean, default=False)
    created_at   = Column(DateTime, default=datetime.utcnow)
    updated_at   = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    doctor_profile  = relationship("DoctorProfile", back_populates="user", uselist=False)
    patient_profile = relationship("PatientProfile", back_populates="user", uselist=False)

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"

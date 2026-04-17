from sqlalchemy import Column, Integer, String, Text, Date, ForeignKey, DateTime, Enum as SAEnum
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

from app.database import Base


class BloodGroup(str, enum.Enum):
    A_pos  = "A+"
    A_neg  = "A-"
    B_pos  = "B+"
    B_neg  = "B-"
    O_pos  = "O+"
    O_neg  = "O-"
    AB_pos = "AB+"
    AB_neg = "AB-"


class PatientProfile(Base):
    __tablename__ = "patient_profiles"

    id                    = Column(Integer, primary_key=True, index=True)
    user_id               = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    dob                   = Column(Date, nullable=True)
    gender                = Column(String(10), nullable=True)          # male / female / other
    blood_group           = Column(SAEnum(BloodGroup), nullable=True)
    address               = Column(Text, nullable=True)
    city                  = Column(String(100), nullable=True)
    state                 = Column(String(100), nullable=True)
    pincode               = Column(String(10), nullable=True)
    emergency_contact_name  = Column(String(200), nullable=True)
    emergency_contact_phone = Column(String(15), nullable=True)
    allergies             = Column(Text, nullable=True)
    existing_conditions   = Column(Text, nullable=True)
    uhid                  = Column(String(20), unique=True, nullable=True)  # Unique Hospital ID
    created_at            = Column(DateTime, default=datetime.utcnow)
    updated_at            = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="patient_profile")

from sqlalchemy import Column, Integer, String, Text, Boolean, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime

from app.database import Base


class DoctorProfile(Base):
    __tablename__ = "doctor_profiles"

    id               = Column(Integer, primary_key=True, index=True)
    user_id          = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    specialization   = Column(String(200), nullable=False)
    qualification    = Column(String(300), nullable=True)
    registration_no  = Column(String(100), nullable=True)
    experience_years = Column(Integer, default=0)
    bio              = Column(Text, nullable=True)
    consultation_fee = Column(Integer, default=0)        # in INR
    is_available     = Column(Boolean, default=True)
    created_at       = Column(DateTime, default=datetime.utcnow)
    updated_at       = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="doctor_profile")

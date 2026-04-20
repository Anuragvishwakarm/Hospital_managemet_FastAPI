"""
app/models/media.py
===================
Photo gallery tables for wards and hospital facility.

  WardPhoto       — up to 5 per ward (interior, beds, equipment)
  HospitalPhoto   — shared pool for about/home pages

Doctor photos stay on DoctorProfile.photo_url (single URL column) because
each doctor only has one profile photo.
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship

from app.database import Base


class WardPhoto(Base):
    __tablename__ = "ward_photos"

    id         = Column(Integer, primary_key=True, index=True)
    ward_id    = Column(Integer, ForeignKey("wards.id", ondelete="CASCADE"), nullable=False, index=True)
    photo_url  = Column(String(255), nullable=False)   # e.g. /uploads/wards/3/abc123.jpg
    caption    = Column(Text, nullable=True)
    sort_order = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # If your Ward model has `back_populates="photos"` we wire it here.
    # Not required — omit if you want the simplest possible integration.
    ward = relationship("Ward", backref="photos")


class HospitalPhoto(Base):
    __tablename__ = "hospital_photos"

    id         = Column(Integer, primary_key=True, index=True)
    photo_url  = Column(String(255), nullable=False)
    caption    = Column(Text, nullable=True)
    category   = Column(String(50), nullable=True, index=True)  # "exterior" | "reception" | "equipment" | "team" | etc.
    sort_order = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
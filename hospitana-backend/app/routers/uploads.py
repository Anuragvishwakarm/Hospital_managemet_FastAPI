"""
app/routers/uploads.py
======================
Photo upload endpoints for the Sahara Hospital HMS.

Three photo types:
  1. Doctor profile photo     — single photo per doctor
  2. Ward photo gallery       — up to 5 photos per ward
  3. Hospital facility photos — global pool for about/home page

All files land under app/uploads/<kind>/<id>/<filename> and are served
via FastAPI's StaticFiles at /uploads/<kind>/<id>/<filename>.
"""

import os
import secrets
from datetime import datetime
from pathlib import Path
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User, UserRole
from app.models.doctor import DoctorProfile
from app.models.bed import Ward
from app.utils.permissions import get_current_user, admin_only  # type: ignore

from app.models.media import WardPhoto, HospitalPhoto  # type: ignore


router = APIRouter(prefix="/uploads", tags=["Uploads"])

# ─── Disk paths ─────────────────────────────────────────────────────────────
UPLOAD_ROOT = Path(__file__).resolve().parent.parent / "uploads"
DOCTOR_DIR   = UPLOAD_ROOT / "doctors"
WARD_DIR     = UPLOAD_ROOT / "wards"
HOSPITAL_DIR = UPLOAD_ROOT / "hospital"
for d in (DOCTOR_DIR, WARD_DIR, HOSPITAL_DIR):
    d.mkdir(parents=True, exist_ok=True)

ALLOWED_EXT = {".jpg", ".jpeg", ".png", ".webp"}
MAX_SIZE_BYTES = 5 * 1024 * 1024
MAX_WARD_PHOTOS = 5
MAX_HOSPITAL_PHOTOS = 20


# ─── Helpers ────────────────────────────────────────────────────────────────
def _validate_image(upload: UploadFile) -> tuple[bytes, str]:
    ext = Path(upload.filename or "").suffix.lower()
    if ext not in ALLOWED_EXT:
        raise HTTPException(400, f"Only {', '.join(sorted(ALLOWED_EXT))} allowed.")
    data = upload.file.read()
    if len(data) > MAX_SIZE_BYTES:
        raise HTTPException(413, f"File too large. Max {MAX_SIZE_BYTES // (1024*1024)} MB.")
    if len(data) == 0:
        raise HTTPException(400, "Empty file.")
    return data, ext


def _random_filename(ext: str) -> str:
    return f"{secrets.token_hex(8)}{ext}"


def _write(path: Path, data: bytes):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "wb") as f:
        f.write(data)


def _absolute(request: Request, url_path: str) -> str:
    base = str(request.base_url).rstrip("/")
    return f"{base}{url_path}"


# ════════════════════════════════════════════════════════════════════════════
# DOCTOR PHOTO
# ════════════════════════════════════════════════════════════════════════════
def _save_doctor_photo(doctor_id: int, upload: UploadFile) -> str:
    data, ext = _validate_image(upload)
    filename = f"{doctor_id}{ext}"
    target = DOCTOR_DIR / filename
    for old_ext in ALLOWED_EXT:
        old = DOCTOR_DIR / f"{doctor_id}{old_ext}"
        if old.exists() and old != target:
            old.unlink()
    _write(target, data)
    return f"/uploads/doctors/{filename}"


def _update_doctor_url(db: Session, doctor_id: int, url_path: Optional[str]):
    profile = db.query(DoctorProfile).filter(DoctorProfile.user_id == doctor_id).first()
    if not profile:
        raise HTTPException(404, "Doctor profile not found.")
    profile.photo_url = url_path
    db.commit()


@router.post("/doctor-photo")
def upload_own_doctor_photo(
    request: Request,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != UserRole.doctor:
        raise HTTPException(403, "Doctors only.")
    url_path = _save_doctor_photo(current_user.id, file)
    _update_doctor_url(db, current_user.id, url_path)
    return {"photo_url": url_path, "absolute_url": _absolute(request, url_path)}


@router.post("/doctor-photo/{doctor_id}")
def admin_upload_doctor_photo(
    doctor_id: int,
    request: Request,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(admin_only),
):
    doc = db.query(User).filter(User.id == doctor_id, User.role == UserRole.doctor).first()
    if not doc:
        raise HTTPException(404, "Doctor not found.")
    url_path = _save_doctor_photo(doctor_id, file)
    _update_doctor_url(db, doctor_id, url_path)
    return {"photo_url": url_path, "absolute_url": _absolute(request, url_path)}


@router.delete("/doctor-photo/{doctor_id}")
def delete_doctor_photo(
    doctor_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    is_admin = current_user.role == UserRole.admin
    is_self = current_user.role == UserRole.doctor and current_user.id == doctor_id
    if not (is_admin or is_self):
        raise HTTPException(403, "Not allowed.")
    for ext in ALLOWED_EXT:
        old = DOCTOR_DIR / f"{doctor_id}{ext}"
        if old.exists():
            old.unlink()
    _update_doctor_url(db, doctor_id, None)
    return {"ok": True}


# ════════════════════════════════════════════════════════════════════════════
# WARD GALLERY
# ════════════════════════════════════════════════════════════════════════════
class WardPhotoResponse(BaseModel):
    id: int
    ward_id: int
    photo_url: str
    caption: Optional[str] = None
    sort_order: int = 0
    model_config = {"from_attributes": True}


@router.get("/ward-photos/{ward_id}", response_model=List[WardPhotoResponse])
def list_ward_photos(ward_id: int, db: Session = Depends(get_db)):
    rows = (
        db.query(WardPhoto)
        .filter(WardPhoto.ward_id == ward_id)
        .order_by(WardPhoto.sort_order, WardPhoto.id)
        .all()
    )
    return rows


@router.post("/ward-photo/{ward_id}", response_model=WardPhotoResponse)
def upload_ward_photo(
    ward_id: int,
    request: Request,
    file: UploadFile = File(...),
    caption: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(admin_only),
):
    ward = db.query(Ward).filter(Ward.id == ward_id).first()
    if not ward:
        raise HTTPException(404, "Ward not found.")

    existing_count = db.query(WardPhoto).filter(WardPhoto.ward_id == ward_id).count()
    if existing_count >= MAX_WARD_PHOTOS:
        raise HTTPException(
            400, f"Ward already has {MAX_WARD_PHOTOS} photos. Delete one first."
        )

    data, ext = _validate_image(file)
    filename = _random_filename(ext)
    target = WARD_DIR / str(ward_id) / filename
    _write(target, data)
    url_path = f"/uploads/wards/{ward_id}/{filename}"

    row = WardPhoto(
        ward_id=ward_id,
        photo_url=url_path,
        caption=caption,
        sort_order=existing_count,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@router.delete("/ward-photo/{ward_id}/{photo_id}")
def delete_ward_photo(
    ward_id: int,
    photo_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(admin_only),
):
    row = (
        db.query(WardPhoto)
        .filter(WardPhoto.id == photo_id, WardPhoto.ward_id == ward_id)
        .first()
    )
    if not row:
        raise HTTPException(404, "Photo not found.")

    filename = Path(row.photo_url).name
    disk_path = WARD_DIR / str(ward_id) / filename
    if disk_path.exists():
        disk_path.unlink()

    db.delete(row)
    db.commit()
    return {"ok": True}


# ════════════════════════════════════════════════════════════════════════════
# HOSPITAL FACILITY PHOTOS
# ════════════════════════════════════════════════════════════════════════════
class HospitalPhotoResponse(BaseModel):
    id: int
    photo_url: str
    caption: Optional[str] = None
    category: Optional[str] = None
    sort_order: int = 0
    model_config = {"from_attributes": True}


@router.get("/hospital-photos", response_model=List[HospitalPhotoResponse])
def list_hospital_photos(
    category: Optional[str] = None,
    db: Session = Depends(get_db),
):
    q = db.query(HospitalPhoto)
    if category:
        q = q.filter(HospitalPhoto.category == category)
    return q.order_by(HospitalPhoto.sort_order, HospitalPhoto.id).all()


@router.post("/hospital-photo", response_model=HospitalPhotoResponse)
def upload_hospital_photo(
    request: Request,
    file: UploadFile = File(...),
    caption: Optional[str] = None,
    category: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(admin_only),
):
    count = db.query(HospitalPhoto).count()
    if count >= MAX_HOSPITAL_PHOTOS:
        raise HTTPException(
            400, f"Hospital gallery full ({MAX_HOSPITAL_PHOTOS} photos max). Delete one first."
        )

    data, ext = _validate_image(file)
    filename = _random_filename(ext)
    target = HOSPITAL_DIR / filename
    _write(target, data)
    url_path = f"/uploads/hospital/{filename}"

    row = HospitalPhoto(
        photo_url=url_path,
        caption=caption,
        category=category,
        sort_order=count,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@router.delete("/hospital-photo/{photo_id}")
def delete_hospital_photo(
    photo_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(admin_only),
):
    row = db.query(HospitalPhoto).filter(HospitalPhoto.id == photo_id).first()
    if not row:
        raise HTTPException(404, "Photo not found.")

    filename = Path(row.photo_url).name
    disk_path = HOSPITAL_DIR / filename
    if disk_path.exists():
        disk_path.unlink()

    db.delete(row)
    db.commit()
    return {"ok": True}
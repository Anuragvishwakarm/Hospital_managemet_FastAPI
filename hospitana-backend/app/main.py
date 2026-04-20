import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.database import engine, Base

# Import models so Alembic / Base.metadata picks them up
from app.models import (  # noqa: F401
    User, DoctorProfile, PatientProfile,
    Appointment, Prescription, PrescriptionMedicine,
    Bill, BillItem, Payment,
    Medicine, MedicineBatch, DispenseOrder, DispenseItem,
    LabTest, LabOrder, LabOrderItem,
    Ward, Bed, Admission,
)

# Routers
from app.routers import (
    auth, admin, doctor, patient, receptionist, account, public,
    appointment, billing, pharmacy, laboratory, bed, uploads,
)

# ── create_all DISABLED — Alembic handles all migrations ─────────────────────
# Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Hospitana HMS — Backend API",
    description="Hospital Management System for Sahara Hospital, Bhadohi UP",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

# ── CORS ──────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Static uploads (doctor photos) ────────────────────────────────────────────
# Files land on disk under app/uploads/doctors/{doctor_id}.{ext}
# and are served publicly at http://<host>/uploads/doctors/{doctor_id}.{ext}
UPLOAD_ROOT = os.path.join(os.path.dirname(__file__), "uploads")
os.makedirs(UPLOAD_ROOT, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=UPLOAD_ROOT), name="uploads")

# ── Routes ────────────────────────────────────────────────────────────────────
API_PREFIX = "/api/v1"

app.include_router(auth.router,         prefix=API_PREFIX)
app.include_router(admin.router,        prefix=API_PREFIX)
app.include_router(doctor.router,       prefix=API_PREFIX)
app.include_router(patient.router,      prefix=API_PREFIX)
app.include_router(receptionist.router, prefix=API_PREFIX)
app.include_router(account.router,      prefix=API_PREFIX)
app.include_router(appointment.router,  prefix=API_PREFIX)
app.include_router(billing.router,      prefix=API_PREFIX)
app.include_router(pharmacy.router,     prefix=API_PREFIX)
app.include_router(laboratory.router,   prefix=API_PREFIX)
app.include_router(bed.router,          prefix=API_PREFIX)
app.include_router(public.router,       prefix=API_PREFIX)
app.include_router(uploads.router,      prefix=API_PREFIX)


# ── Health check ──────────────────────────────────────────────────────────────
@app.get("/health", tags=["Health"])
def health():
    return {"status": "ok", "service": "Hospitana HMS API", "version": "1.0.0"}


@app.get("/", tags=["Health"])
def root():
    return {"message": "Hospitana HMS API", "docs": "/api/docs"}
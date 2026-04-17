# Hospitana HMS — Backend API (Complete)

FastAPI backend for **Sahara Hospital, Bhadohi UP**.

---

## Project Structure

```
hospitana-backend/
├── app/
│   ├── main.py              ← FastAPI app, CORS, all router registrations
│   ├── config.py            ← Settings loaded from .env
│   ├── database.py          ← SQLAlchemy engine + get_db dependency
│   ├── models/
│   │   ├── user.py          ← User (all roles in one table)
│   │   ├── doctor.py        ← DoctorProfile
│   │   ├── patient.py       ← PatientProfile, BloodGroup
│   │   ├── appointment.py   ← Appointment, Prescription, PrescriptionMedicine
│   │   ├── billing.py       ← Bill, BillItem, Payment
│   │   ├── pharmacy.py      ← Medicine, MedicineBatch, DispenseOrder, DispenseItem
│   │   ├── laboratory.py    ← LabTest, LabOrder, LabOrderItem
│   │   └── bed.py           ← Ward, Bed, Admission
│   ├── schemas/             ← Pydantic request/response models (mirror of models/)
│   ├── routers/             ← Route handlers
│   │   ├── auth.py          /auth/*
│   │   ├── admin.py         /admin/*
│   │   ├── doctor.py        /doctors/*
│   │   ├── patient.py       /patients/*
│   │   ├── receptionist.py  /receptionist/*
│   │   ├── account.py       /account/*
│   │   ├── appointment.py   /appointments/*
│   │   ├── billing.py       /billing/*
│   │   ├── pharmacy.py      /pharmacy/*
│   │   ├── laboratory.py    /laboratory/*
│   │   └── bed.py           /beds/*
│   └── utils/
│       ├── auth.py          ← JWT helpers + bcrypt
│       └── permissions.py   ← Role-based dependency guards
├── alembic/env.py
├── alembic.ini
├── create_admin.py          ← Seed default accounts (run once)
├── requirements.txt
└── .env.example
```

---

## Setup

```bash
# 1. Install
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
pip uninstall bcrypt -y && pip install bcrypt==4.0.1  # CRITICAL

# 2. Database
psql -U postgres -c "CREATE DATABASE hospitana_db;"

# 3. Configure
cp .env.example .env   # edit DB_PASSWORD and SECRET_KEY

# 4. Migrate + run
alembic revision --autogenerate -m "initial"
alembic upgrade head
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 5. Seed defaults
python create_admin.py
```

Swagger: `http://localhost:8000/api/docs`

---

## Default Credentials  ⚠️ Change before go-live!

| Role         | Email                        | Password    |
|--------------|------------------------------|-------------|
| Admin        | admin@saharahospital.com     | Admin@1234  |
| Doctor       | doctor@saharahospital.com    | Doctor@1234 |
| Receptionist | reception@saharahospital.com | Staff@1234  |
| Accountant   | accounts@saharahospital.com  | Staff@1234  |

---

## API Reference  (prefix: `/api/v1`)

### Auth `/auth`
| Method | Endpoint         | Access | Description                       |
|--------|------------------|--------|-----------------------------------|
| POST   | /register        | Public | Patient self-register             |
| POST   | /staff-register  | Public | Staff register → pending approval |
| POST   | /login           | Public | Login → tokens                    |
| POST   | /token/refresh   | Public | Refresh access token              |
| GET    | /profile         | Auth   | Logged-in user profile            |
| PUT    | /change-password | Auth   | Change own password               |

### Admin `/admin`
| Method | Endpoint                     | Description                |
|--------|------------------------------|----------------------------|
| GET    | /dashboard-stats             | KPI counts                 |
| GET    | /staff                       | List staff (role filter)   |
| GET    | /staff/pending               | Pending approvals          |
| GET    | /staff/{id}                  | Staff detail               |
| POST   | /staff                       | Create staff (active now)  |
| PUT    | /staff/{id}                  | Update staff               |
| PUT    | /staff/{id}/approve          | Approve pending            |
| PUT    | /staff/{id}/reject           | Reject & delete            |
| PUT    | /staff/{id}/deactivate       | Deactivate                 |
| PUT    | /staff/{id}/reset-password   | Reset to default pwd       |
| GET    | /users                       | All users list             |

### Doctors `/doctors`
| Method | Endpoint                   | Description                  |
|--------|----------------------------|------------------------------|
| GET    | /                          | List active doctors           |
| GET    | /me                        | Doctor's own profile         |
| GET    | /meta/specializations      | Specialization list           |
| GET    | /{id}                      | Doctor detail                |
| POST   | /{id}/profile              | Create doctor profile        |
| PUT    | /{id}/profile              | Update doctor profile        |
| PUT    | /{id}/toggle-availability  | Toggle on/off                |

### Patients `/patients`
| Method | Endpoint       | Access              | Description           |
|--------|----------------|---------------------|-----------------------|
| GET    | /              | Admin, Receptionist | List patients         |
| GET    | /me            | Patient             | Own record            |
| GET    | /{id}          | Staff or self       | Patient detail        |
| POST   | /              | Admin, Receptionist | Register patient      |
| PUT    | /{id}          | Staff or self       | Update basic info     |
| PUT    | /{id}/profile  | Staff or self       | Update medical profile|

### Appointments `/appointments`
| Method | Endpoint              | Description                      |
|--------|-----------------------|----------------------------------|
| GET    | /                     | List appointments (role-scoped)  |
| GET    | /today                | Today's appointments             |
| GET    | /available-slots      | Open slots for doctor + date     |
| POST   | /                     | Book appointment                 |
| GET    | /{id}                 | Appointment detail               |
| PUT    | /{id}                 | Update appointment               |
| PUT    | /{id}/cancel          | Cancel                           |
| PUT    | /{id}/complete        | Mark completed (doctor/admin)    |
| POST   | /{id}/prescription    | Add prescription + medicines     |
| GET    | /{id}/prescription    | Get prescription                 |

### Billing `/billing`
| Method | Endpoint    | Description                       |
|--------|-------------|-----------------------------------|
| GET    | /stats      | Revenue, pending, today totals    |
| GET    | /           | List bills (patient sees own)     |
| GET    | /{id}       | Bill with items + payments        |
| POST   | /           | Create bill (auto GST calc)       |
| POST   | /{id}/pay   | Record payment (cash/UPI/card)    |
| PUT    | /{id}/cancel| Cancel bill                       |

### Pharmacy `/pharmacy`
| Method | Endpoint                    | Description                |
|--------|-----------------------------|----------------------------|
| GET    | /medicines                  | List medicines             |
| GET    | /medicines/low-stock        | Low stock alerts           |
| GET    | /medicines/{id}             | Medicine detail            |
| POST   | /medicines                  | Add to catalog             |
| PUT    | /medicines/{id}             | Update medicine            |
| POST   | /medicines/{id}/add-stock   | Add stock batch            |
| GET    | /medicines/{id}/batches     | List batches               |
| GET    | /dispense                   | List dispense orders       |
| POST   | /dispense                   | Dispense to patient        |

### Laboratory `/laboratory`
| Method | Endpoint                       | Description               |
|--------|--------------------------------|---------------------------|
| GET    | /tests                         | Test catalog              |
| GET    | /tests/categories              | Categories list           |
| POST   | /tests                         | Add test                  |
| PUT    | /tests/{id}                    | Update test               |
| GET    | /orders                        | List orders               |
| POST   | /orders                        | Create lab order          |
| GET    | /orders/{id}                   | Order detail + results    |
| PUT    | /orders/{id}/collect-sample    | Sample collected          |
| PUT    | /orders/{id}/start-processing  | Start processing          |
| PUT    | /orders/{id}/results           | Enter results             |

### Beds & Wards `/beds`
| Method | Endpoint                    | Description                |
|--------|-----------------------------|----------------------------|
| GET    | /wards                      | List wards                 |
| POST   | /wards                      | Create ward                |
| PUT    | /wards/{id}                 | Update ward                |
| GET    | /occupancy                  | Overall occupancy stats    |
| GET    | /                           | List beds (filterable)     |
| POST   | /                           | Add bed to ward            |
| PUT    | /{id}                       | Update bed status          |
| GET    | /admissions                 | List admissions            |
| POST   | /admissions                 | Admit patient              |
| PUT    | /admissions/{id}/discharge  | Discharge patient          |

### Receptionist `/receptionist`
| Method | Endpoint           | Description              |
|--------|--------------------|--------------------------|
| GET    | /dashboard         | Summary stats            |
| GET    | /available-doctors | Currently available docs |

### Account `/account`
| Method | Endpoint    | Description          |
|--------|-------------|----------------------|
| GET    | /dashboard  | Accountant dashboard |
| GET    | /profile    | Own profile          |

---

## Role Access Matrix

| Module        | admin | doctor | receptionist | patient | accountant |
|---------------|:-----:|:------:|:------------:|:-------:|:----------:|
| /admin        | ✅    | ❌     | ❌           | ❌      | ❌         |
| /doctors      | ✅    | ✅     | ✅           | ✅      | ✅         |
| /patients     | ✅    | ❌     | ✅           | own     | ❌         |
| /appointments | ✅    | own    | ✅           | own     | ❌         |
| /billing      | ✅    | ❌     | ✅           | own     | ✅         |
| /pharmacy     | ✅    | ✅(r)  | ✅           | ❌      | ✅         |
| /laboratory   | ✅    | ✅     | ✅           | own     | ❌         |
| /beds         | ✅    | ✅     | ✅           | own     | ❌         |
| /receptionist | ❌    | ❌     | ✅           | ❌      | ❌         |
| /account      | ❌    | ❌     | ❌           | ❌      | ✅         |

---

## DB Schema

```
users
  ├── doctor_profiles (1:1)
  ├── patient_profiles (1:1)
  ├── appointments  →  prescriptions  →  prescription_medicines
  ├── bills  →  bill_items + payments
  ├── lab_orders  →  lab_order_items  →  lab_tests
  ├── dispense_orders  →  dispense_items  →  medicines
  └── admissions  →  beds  →  wards

medicines  →  medicine_batches
wards  →  beds  →  admissions
```

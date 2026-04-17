from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from decimal import Decimal
from app.models.laboratory import LabOrderStatus


class LabTestCreate(BaseModel):
    name:         str
    code:         Optional[str] = None
    category:     Optional[str] = None
    price:        Optional[Decimal] = Decimal("0")
    normal_range: Optional[str] = None
    unit:         Optional[str] = None
    description:  Optional[str] = None


class LabTestUpdate(BaseModel):
    name:         Optional[str] = None
    category:     Optional[str] = None
    price:        Optional[Decimal] = None
    normal_range: Optional[str] = None
    unit:         Optional[str] = None
    is_active:    Optional[bool] = None


class LabTestResponse(BaseModel):
    id:           int
    name:         str
    code:         Optional[str]
    category:     Optional[str]
    price:        Decimal
    normal_range: Optional[str]
    unit:         Optional[str]
    is_active:    bool

    model_config = {"from_attributes": True}


class LabOrderCreate(BaseModel):
    patient_id:     int
    doctor_id:      Optional[int] = None
    appointment_id: Optional[int] = None
    test_ids:       List[int]
    notes:          Optional[str] = None


class LabResultInput(BaseModel):
    test_id:     int
    result:      str
    is_abnormal: Optional[bool] = False
    remarks:     Optional[str] = None


class LabOrderItemResponse(BaseModel):
    id:          int
    test_id:     int
    result:      Optional[str]
    is_abnormal: bool
    remarks:     Optional[str]
    tested_at:   Optional[datetime]
    test_name:   Optional[str] = None

    model_config = {"from_attributes": True}


class LabOrderResponse(BaseModel):
    id:                  int
    patient_id:          int
    doctor_id:           Optional[int]
    appointment_id:      Optional[int]
    status:              LabOrderStatus
    sample_collected_at: Optional[datetime]
    completed_at:        Optional[datetime]
    notes:               Optional[str]
    created_at:          datetime
    items:               List[LabOrderItemResponse] = []
    patient_name:        Optional[str] = None

    model_config = {"from_attributes": True}

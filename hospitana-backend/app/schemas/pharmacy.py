from pydantic import BaseModel
from typing import Optional, List
from datetime import date, datetime
from decimal import Decimal


class MedicineCreate(BaseModel):
    name:            str
    generic_name:    Optional[str] = None
    category:        Optional[str] = None
    manufacturer:    Optional[str] = None
    unit:            Optional[str] = "strip"
    price_per_unit:  Optional[Decimal] = Decimal("0")
    stock_quantity:  Optional[int] = 0
    low_stock_threshold: Optional[int] = 10
    hsn_code:        Optional[str] = None
    gst_percent:     Optional[Decimal] = Decimal("12")


class MedicineUpdate(BaseModel):
    name:            Optional[str] = None
    generic_name:    Optional[str] = None
    category:        Optional[str] = None
    manufacturer:    Optional[str] = None
    unit:            Optional[str] = None
    price_per_unit:  Optional[Decimal] = None
    low_stock_threshold: Optional[int] = None
    is_active:       Optional[bool] = None


class MedicineResponse(BaseModel):
    id:             int
    name:           str
    generic_name:   Optional[str]
    category:       Optional[str]
    manufacturer:   Optional[str]
    unit:           str
    price_per_unit: Decimal
    stock_quantity: int
    low_stock_threshold: int
    is_active:      bool
    gst_percent:    Decimal
    is_low_stock:   bool = False

    model_config = {"from_attributes": True}

    def model_post_init(self, __context):
        self.is_low_stock = self.stock_quantity <= self.low_stock_threshold


class BatchCreate(BaseModel):
    batch_number:   str
    expiry_date:    date
    quantity:       int
    purchase_price: Optional[Decimal] = Decimal("0")


class BatchResponse(BaseModel):
    id:             int
    medicine_id:    int
    batch_number:   str
    expiry_date:    date
    quantity:       int
    purchase_price: Decimal
    created_at:     datetime

    model_config = {"from_attributes": True}


class DispenseItemInput(BaseModel):
    medicine_id: int
    quantity:    int


class DispenseCreate(BaseModel):
    patient_id:      int
    prescription_id: Optional[int] = None
    items:           List[DispenseItemInput]
    notes:           Optional[str] = None


class DispenseItemResponse(BaseModel):
    id:          int
    medicine_id: int
    quantity:    int
    unit_price:  Decimal
    total_price: Decimal
    medicine_name: Optional[str] = None

    model_config = {"from_attributes": True}


class DispenseResponse(BaseModel):
    id:           int
    patient_id:   int
    total_amount: Decimal
    dispensed_at: datetime
    items:        List[DispenseItemResponse] = []

    model_config = {"from_attributes": True}

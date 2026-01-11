from pydantic import BaseModel
from typing import Optional, List

class InvoiceItem(BaseModel):
    description: str
    quantity: int
    rate: float

class InvoiceData(BaseModel):
    companyName: Optional[str] = None
    address: Optional[str] = None

    clientName: Optional[str] = None
    clientAddress: Optional[str] = None

    date: Optional[str] = None

    items: List[InvoiceItem] = []

    gst: Optional[str] = None
    paymentMode: Optional[str] = None
    paymentStatus: Optional[str] = None

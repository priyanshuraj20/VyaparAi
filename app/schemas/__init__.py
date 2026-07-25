import uuid
from pydantic import BaseModel, Field, field_validator
from typing import Optional
from enum import Enum


# ─── Request Schemas ─────────────────────────────────────────────────────────

class TransactionTypeEnum(str, Enum):
    credit_given = "credit_given"
    payment_received = "payment_received"


class CreateTransactionRequest(BaseModel):
    customer_id: str
    transaction_type: TransactionTypeEnum
    amount: float = Field(..., gt=0, description="Amount must be positive")
    item_description: Optional[str] = None
    source: str = "text"
    confidence: float = Field(1.0, ge=0.0, le=1.0)

    @field_validator("customer_id")
    @classmethod
    def validate_uuid(cls, v: str) -> str:
        try:
            uuid.UUID(v)
            return v
        except ValueError:
            raise ValueError("Invalid UUID format for customer_id")


class CreateCustomerRequest(BaseModel):
    name: str = Field(..., min_length=1)
    phone: Optional[str] = None
    alias_notes: Optional[str] = None


class OCRRequest(BaseModel):
    image_url: str


class ReminderRequest(BaseModel):
    customer_id: str
    outstanding_amount: float
    days_overdue: int = 30

    @field_validator("customer_id")
    @classmethod
    def validate_uuid(cls, v: str) -> str:
        try:
            uuid.UUID(v)
            return v
        except ValueError:
            raise ValueError("Invalid UUID format for customer_id")


# ─── Response Schemas ─────────────────────────────────────────────────────────

class TransactionResponse(BaseModel):
    transaction_id: str
    new_balance: float
    status: str


class CustomerResponse(BaseModel):
    customer_id: str
    customer_name: str
    outstanding_balance: float
    last_payment_date: Optional[str]
    transactions: list[dict]


class BalanceResponse(BaseModel):
    customer_id: str
    outstanding_balance: float


class ReminderResponse(BaseModel):
    reminder_id: str
    customer_name: str
    draft_message: str
    requires_approval: bool


class HealthResponse(BaseModel):
    status: str
    service: str
    environment: str

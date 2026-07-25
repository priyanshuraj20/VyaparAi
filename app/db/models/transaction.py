import uuid
import enum
from datetime import datetime, timezone
from sqlalchemy import Column, String, Text, Numeric, Float, DateTime, ForeignKey, Enum as SQLEnum, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.db.session import Base


class TransactionType(str, enum.Enum):
    CREDIT_GIVEN = "credit_given"
    PAYMENT_RECEIVED = "payment_received"


class TransactionStatus(str, enum.Enum):
    PENDING_CONFIRMATION = "pending_confirmation"
    CONFIRMED = "confirmed"
    REJECTED = "rejected"
    UNDONE = "undone"


class TransactionSource(str, enum.Enum):
    TEXT = "text"
    VOICE = "voice"
    OCR = "ocr"


class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    customer_id = Column(UUID(as_uuid=True), ForeignKey("customers.id", ondelete="CASCADE"), nullable=False, index=True)
    type = Column(SQLEnum(TransactionType, name="transaction_type", values_callable=lambda x: [e.value for e in x]), nullable=False)
    amount = Column(Numeric(10, 2), nullable=False)
    item_description = Column(Text, nullable=True)
    status = Column(SQLEnum(TransactionStatus, name="transaction_status", values_callable=lambda x: [e.value for e in x]), default=TransactionStatus.CONFIRMED, nullable=False, index=True)
    source = Column(SQLEnum(TransactionSource, name="transaction_source", values_callable=lambda x: [e.value for e in x]), default=TransactionSource.TEXT, nullable=False)
    confidence_score = Column(Float, default=1.0, nullable=False)
    raw_input = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None), nullable=False, index=True)
    confirmed_at = Column(DateTime, nullable=True)

    customer = relationship("Customer", back_populates="transactions")

    __table_args__ = (
        Index("idx_transactions_customer_status", "customer_id", "status"),
    )

    def __repr__(self):
        return f"<Transaction type={self.type} amount={self.amount} status={self.status}>"

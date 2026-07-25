import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Text, Boolean, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.db.session import Base


class Customer(Base):
    __tablename__ = "customers"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False, index=True)
    alias_notes = Column(Text, nullable=True)
    phone = Column(String(50), nullable=True, index=True)
    whatsapp_opted_in = Column(Boolean, default=False, nullable=False)
    opted_in_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None), nullable=False)

    transactions = relationship("Transaction", back_populates="customer", cascade="all, delete-orphan")
    reminders = relationship("Reminder", back_populates="customer", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Customer name={self.name} phone={self.phone}>"

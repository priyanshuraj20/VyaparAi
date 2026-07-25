import uuid
import enum
from datetime import datetime, timezone
from sqlalchemy import Column, Numeric, Boolean, DateTime, ForeignKey, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.db.session import Base


class ReminderChannel(str, enum.Enum):
    CONVERSATIONAL = "conversational"
    TEMPLATE = "template"
    OWNER_ONLY = "owner_only"


class Reminder(Base):
    __tablename__ = "reminders"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    customer_id = Column(UUID(as_uuid=True), ForeignKey("customers.id", ondelete="CASCADE"), nullable=False, index=True)
    amount_at_time = Column(Numeric(10, 2), nullable=False)
    proposed_at = Column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None), nullable=False)
    approved_by_owner = Column(Boolean, nullable=True)
    channel_used = Column(SQLEnum(ReminderChannel, name="reminder_channel", values_callable=lambda x: [e.value for e in x]), nullable=True)
    sent_at = Column(DateTime, nullable=True)

    customer = relationship("Customer", back_populates="reminders")

    def __repr__(self):
        return f"<Reminder customer_id={self.customer_id} amount={self.amount_at_time} sent={self.sent_at}>"

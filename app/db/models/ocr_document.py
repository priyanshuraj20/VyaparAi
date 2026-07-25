import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, Float, Boolean, DateTime, ForeignKey, JSON
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from app.db.session import Base


class OCRDocument(Base):
    __tablename__ = "ocr_documents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    message_id = Column(UUID(as_uuid=True), ForeignKey("messages.id", ondelete="CASCADE"), nullable=False, index=True)
    extracted_json = Column(JSON().with_variant(JSONB, "postgresql"), nullable=False)
    confidence_score = Column(Float, default=1.0, nullable=False)
    reviewed = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None), nullable=False)

    message = relationship("Message", back_populates="ocr_documents")

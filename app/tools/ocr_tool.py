import uuid
import structlog
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models import OCRDocument
from app.services.vision_service import vision_service, OCRResult


logger = structlog.get_logger()


async def extract_from_image(db: AsyncSession, image_url: str, message_id: Optional[str] = None) -> dict:
    """
    Calls Vision LLM to extract items from handwritten list/bill image.
    Saves extraction result in OCRDocument for audit trail.
    Returns structured items + confidence.
    """
    try:
        result: OCRResult = await vision_service.extract_from_image_url(image_url)
    except ValueError as e:
        logger.error("ocr_extraction_failed", error=str(e))
        raise

    # Persist OCR result for audit
    if message_id:
        ocr_doc = OCRDocument(
            message_id=uuid.UUID(message_id),
            extracted_json={
                "items": [item.model_dump() for item in result.items],
                "overall_confidence": result.overall_confidence,
                "raw_text": result.raw_text,
            },
            confidence_score=result.overall_confidence,
        )
        db.add(ocr_doc)
        await db.commit()
        logger.info("ocr_document_saved", confidence=result.overall_confidence, items=len(result.items))

    return {
        "items": [item.model_dump() for item in result.items],
        "overall_confidence": result.overall_confidence,
        "raw_text": result.raw_text,
    }

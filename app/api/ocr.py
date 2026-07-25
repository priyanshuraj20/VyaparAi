from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.tools.ocr_tool import extract_from_image
from app.schemas import OCRRequest
import structlog

logger = structlog.get_logger()

router = APIRouter(prefix="/ocr", tags=["OCR"])


@router.post("")
async def ocr_extract(
    body: OCRRequest,
    db: AsyncSession = Depends(get_db),
):
    """Submit an image URL for item extraction — internal use by webhook flow."""
    try:
        result = await extract_from_image(db, body.image_url)
        return result
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logger.error("ocr_extract_failed", error=str(e))
        raise HTTPException(status_code=500, detail="Vision extraction failed")

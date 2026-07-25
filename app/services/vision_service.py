import base64
import json
import structlog
from typing import Optional
from pydantic import BaseModel
from openai import AsyncOpenAI
from app.core.config import settings

logger = structlog.get_logger()


class OCRItem(BaseModel):
    description: str
    amount: Optional[float] = None
    confidence: float = 1.0


class OCRResult(BaseModel):
    items: list[OCRItem]
    overall_confidence: float
    raw_text: Optional[str] = None


VISION_PROMPT = """You are helping a small kirana store owner in India process a handwritten shopping list or bill.

Extract all items and their prices/amounts from the image provided.
Return a JSON object with this EXACT structure:
{
  "items": [
    {"description": "item name", "amount": <number or null>, "confidence": <0.0-1.0>}
  ],
  "overall_confidence": <0.0-1.0>,
  "raw_text": "<full text visible in image>"
}

Rules:
- If handwriting is unclear for an amount, set confidence < 0.85 and amount to null
- overall_confidence = average of all item confidences
- Descriptions in original language (Hindi/English)
"""


class VisionService:
    """Extracts structured item lists from handwritten list photos via OpenRouter API."""

    def __init__(self):
        self.client = AsyncOpenAI(
            api_key=settings.OPENROUTER_API_KEY,
            base_url="https://openrouter.ai/api/v1",
        )
        self.model = settings.OPENROUTER_VISION_MODEL or "openai/gpt-4o-mini"

    async def extract_from_image_url(self, image_url: str) -> OCRResult:
        """
        Sends an image (URL or base64 data URL) to Vision LLM via OpenRouter.
        Returns structured OCRResult with confidence scores.
        """
        try:
            # Handle base64 or public URL format
            if not image_url.startswith("data:") and not image_url.startswith("http"):
                data_url = f"data:image/jpeg;base64,{image_url}"
            else:
                data_url = image_url

            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": VISION_PROMPT},
                            {"type": "image_url", "image_url": {"url": data_url}},
                        ],
                    }
                ],
                response_format={"type": "json_object"},
            )

            raw_content = response.choices[0].message.content.strip()
            if raw_content.startswith("```"):
                lines = raw_content.split("\n")
                raw_content = "\n".join(lines[1:-1])

            parsed = json.loads(raw_content)
            result = OCRResult(**parsed)
            logger.info("vision_extraction_done", items=len(result.items), confidence=result.overall_confidence)
            return result

        except json.JSONDecodeError as e:
            logger.error("vision_json_failed", error=str(e))
            raise ValueError(f"Vision returned unparseable output: {e}")
        except Exception as e:
            logger.error("vision_extraction_failed", error=str(e))
            raise


vision_service = VisionService()

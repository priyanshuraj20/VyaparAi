import os
import base64
import structlog
from openai import AsyncOpenAI
from app.core.config import settings

logger = structlog.get_logger()


class WhisperService:
    """
    Transcribes Hindi/Hinglish voice notes via OpenRouter LLM Audio/Text processing.
    """

    def __init__(self):
        self.client = AsyncOpenAI(
            api_key=settings.OPENROUTER_API_KEY,
            base_url="https://openrouter.ai/api/v1",
        )
        self.model = settings.OPENROUTER_MODEL or "deepseek/deepseek-chat"

    async def transcribe(self, audio_bytes: bytes, filename: str = "audio.ogg") -> str:
        """
        Accepts raw audio bytes, passes to OpenRouter transcription service.
        """
        ext = os.path.splitext(filename)[1].lower() or ".ogg"
        mime_map = {
            ".ogg": "audio/ogg",
            ".mp3": "audio/mpeg",
            ".m4a": "audio/mp4",
            ".wav": "audio/wav",
            ".aac": "audio/aac",
        }
        mime_type = mime_map.get(ext, "audio/ogg")
        b64_audio = base64.b64encode(audio_bytes).decode("utf-8")
        data_url = f"data:{mime_type};base64,{b64_audio}"

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": "Transcribe this audio file or description accurately into Hindi/Hinglish text as spoken. Return ONLY the transcribed text, no extra commentary.",
                            },
                        ],
                    }
                ],
            )

            transcription = response.choices[0].message.content.strip()
            logger.info("audio_transcribed", length=len(transcription))
            return transcription

        except Exception as e:
            logger.error("audio_transcription_failed", error=str(e))
            raise


whisper_service = WhisperService()

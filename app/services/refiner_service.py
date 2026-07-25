import structlog
from typing import Optional
from openai import AsyncOpenAI
from app.core.config import settings

logger = structlog.get_logger()

REFINER_SYSTEM_PROMPT = """You are a Response Refiner layer for VyaparAI business assistant.

CRITICAL INSTRUCTIONS:
1. If the input is a GREETING, CONVERSATIONAL MESSAGE, or ASSISTANT INTRO (e.g. starts with "👋", "Hello", "Nice to meet you", or lists features):
   - DO NOT convert it into a transaction card or customer record card.
   - Pass the conversational greeting/intro text through cleanly.

2. If the input is a CUSTOMER CREATED notification:
   Format as:
   ✅ Customer Created

   Customer: [Name]
   Phone Number: *[Phone Number if provided, else N/A]*

   You can now record transactions for this customer.

3. If the input is a BUSINESS TRANSACTION (e.g. Payment Recorded, Credit Recorded):
   - Keep exact customer names, amounts, balances, payment modes, and transaction types.
   - Format cleanly in professional accounting software style.
   - Retain passive reversal line at the bottom: "Need to reverse it? Reply \"undo\"."

4. NEVER add informal terms like "papa", "uncle", or "bhai". Return ONLY the refined message text.
"""


class ResponseRefiner:
    """
    Lightweight Response Refiner layer powered by Groq / OpenRouter.
    Applies domain-aware formatting and preserves exact business values.
    """

    def __init__(self):
        if settings.GROQ_API_KEY:
            self.client = AsyncOpenAI(
                api_key=settings.GROQ_API_KEY,
                base_url="https://api.groq.com/openai/v1",
            )
            self.model = "llama-3.1-8b-instant"
        else:
            self.client = AsyncOpenAI(
                api_key=settings.OPENROUTER_API_KEY,
                base_url="https://openrouter.ai/api/v1",
            )
            self.model = settings.OPENROUTER_VISION_MODEL or "openai/gpt-4o-mini"

    async def refine(self, raw_message: str) -> str:
        """
        Refine a raw message string before sending to WhatsApp.
        Falls back safely to raw_message if any error occurs.
        """
        if not raw_message or not raw_message.strip():
            return raw_message

        # Skip refiner for greetings/intros that start with 👋 or Developer Mode header
        if raw_message.strip().startswith("👋") or "🧠 AI Planner Reasoning" in raw_message:
            return raw_message

        # Skip refiner for ultra-short standard messages
        if len(raw_message.strip()) < 15:
            return raw_message

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": REFINER_SYSTEM_PROMPT},
                    {"role": "user", "content": f"Raw backend output: {raw_message}"},
                ],
                temperature=0.1,
                max_tokens=300,
            )

            refined = response.choices[0].message.content.strip()

            # Safety assertion: if raw message was an error, refined message must NOT claim success
            lower_raw = raw_message.lower()
            if any(err_kw in lower_raw for err_kw in ["error", "failed", "couldn't find", "nahi mila", "no customer found"]):
                if "✅" in refined and "✅" not in raw_message:
                    logger.warning("refiner_safety_block_success_on_error", raw=raw_message, refined=refined)
                    return raw_message

            # Ensure no informal family terms leak into refined response
            for bad_term in ["papa", "uncle", "bhai"]:
                if bad_term in refined.lower() and bad_term not in raw_message.lower():
                    refined = refined.replace(bad_term, "").replace(bad_term.capitalize(), "")

            if refined and len(refined) > 5:
                logger.info("response_refined", original_len=len(raw_message), refined_len=len(refined))
                return refined
            return raw_message

        except Exception as e:
            logger.warning("response_refiner_fallback", error=str(e))
            return raw_message


refiner_service = ResponseRefiner()

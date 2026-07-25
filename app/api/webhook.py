import hmac
import hashlib
import json
from typing import Any, Optional
from fastapi import APIRouter, Request, Response, HTTPException, Query
from app.core.config import settings
import structlog

logger = structlog.get_logger()
from app.services.whatsapp_service import whatsapp_service
from app.services.refiner_service import refiner_service
from app.memory.redis_store import redis_store

router = APIRouter(prefix="/webhook", tags=["WhatsApp Webhook"])


def _verify_signature(payload: bytes, signature_header: Optional[str]) -> bool:
    """Validate Meta X-Hub-Signature-256 header when WHATSAPP_APP_SECRET is set."""
    app_secret = getattr(settings, "WHATSAPP_APP_SECRET", "")
    if not app_secret:
        return True

    if not signature_header or not signature_header.startswith("sha256="):
        return False

    expected_sig = hmac.new(
        app_secret.encode("utf-8"),
        msg=payload,
        digestmod=hashlib.sha256,
    ).hexdigest()
    provided_sig = signature_header.split("sha256=", 1)[1]
    return hmac.compare_digest(expected_sig, provided_sig)


# ─────────────────────────────────────────────────────────
# GET /webhook  — Meta challenge verification
# ─────────────────────────────────────────────────────────
@router.get("")
async def verify_webhook(
    hub_mode: Optional[str] = Query(None, alias="hub.mode"),
    hub_verify_token: Optional[str] = Query(None, alias="hub.verify_token"),
    hub_challenge: Optional[str] = Query(None, alias="hub.challenge"),
):
    """Meta WhatsApp Webhook Verification Endpoint."""
    if hub_mode == "subscribe" and hub_verify_token == settings.WHATSAPP_VERIFY_TOKEN:
        logger.info("webhook_verified")
        return Response(content=hub_challenge, media_type="text/plain")
    logger.warning("webhook_verification_failed", token=hub_verify_token)
    raise HTTPException(status_code=403, detail="Forbidden: Invalid verify token")


# ─────────────────────────────────────────────────────────
# POST /webhook  — Incoming WhatsApp messages
# ─────────────────────────────────────────────────────────
@router.post("")
async def receive_message(request: Request):
    """Receives and processes incoming WhatsApp messages."""
    raw_body = await request.body()
    sig_header = request.headers.get("X-Hub-Signature-256")

    if not _verify_signature(raw_body, sig_header):
        logger.warning("webhook_invalid_signature")
        raise HTTPException(status_code=401, detail="Invalid webhook signature")

    if not raw_body or not raw_body.strip():
        return {"status": "ignored", "reason": "empty body"}

    try:
        body: dict = json.loads(raw_body)
    except json.JSONDecodeError as e:
        logger.warning("webhook_malformed_json", error=str(e))
        raise HTTPException(status_code=400, detail="Invalid JSON body")

    if not isinstance(body, dict) or body.get("object") != "whatsapp_business_account":
        return {"status": "ignored"}

    for entry in body.get("entry", []):
        for change in entry.get("changes", []):
            value = change.get("value", {})
            messages = value.get("messages", [])

            for message in messages:
                try:
                    await _handle_message(message, value)
                except Exception as e:
                    logger.error("message_handling_error", message_id=message.get("id"), error=str(e))

    return {"status": "ok"}


async def _handle_message(message: dict, value: dict) -> None:
    """Dispatch a single inbound WhatsApp message to appropriate handler."""
    sender = message.get("from", "")
    msg_type = message.get("type", "text")
    msg_id = message.get("id", "")

    # ── Owner-only guard ──────────────────────────────────
    if not whatsapp_service.is_owner(sender):
        logger.warning("non_owner_message_ignored", sender=sender, message_id=msg_id)
        return

    # ── Upstash Redis Idempotency Guard (Deduplication) ────
    if msg_id:
        if await redis_store.is_duplicate_message(msg_id):
            logger.info("webhook_duplicate_message_ignored", message_id=msg_id)
            return

    logger.info("owner_message_received", message_id=msg_id, sender=sender, type=msg_type)

    # ── Dispatch by message type ──────────────────────────
    if msg_type == "text":
        text_body = message.get("text", {}).get("body", "")
        await _process_text(sender, text_body)

    elif msg_type == "audio":
        audio_id = message.get("audio", {}).get("id")
        if not audio_id:
            await whatsapp_service.send_text_message(sender, "Voice note audio ID missing. Dobara bhejiye.")
            return
        await _process_voice(sender, audio_id)

    elif msg_type == "image":
        image_id = message.get("image", {}).get("id")
        if not image_id:
            await whatsapp_service.send_text_message(sender, "Photo image ID missing. Dobara bhejiye.")
            return
        await _process_image(sender, image_id)

    elif msg_type in ("document", "video", "sticker", "location", "contacts"):
        await whatsapp_service.send_text_message(
            sender,
            "Yeh format (document/video/sticker) abhi support nahi karta. Text, voice note, ya bill photo bhejiye."
        )

    else:
        await whatsapp_service.send_text_message(
            sender,
            "Yeh message type abhi support nahi karta. Text, voice note, ya bill photo bhejiye."
        )


async def _process_text(sender: str, text: str) -> None:
    """Handle a plain text message from the owner."""
    from app.agents.planner import planner_agent

    if not text or not text.strip():
        await whatsapp_service.send_text_message(
            sender, "Please type a text message or send a voice note."
        )
        return

    logger.info("processing_text", sender=sender, text_preview=text[:80])
    raw_reply = await planner_agent.process(sender=sender, text=text, source="text")
    final_reply = await refiner_service.refine(raw_reply)
    await whatsapp_service.send_text_message(sender, final_reply)


async def _process_voice(sender: str, audio_id: str) -> None:
    """Download audio, transcribe via Whisper, then route through Planner."""
    from app.services.whisper_service import whisper_service
    from app.agents.planner import planner_agent
    try:
        audio_bytes = await whatsapp_service.download_media(audio_id)
        transcription = await whisper_service.transcribe(audio_bytes, filename="audio.ogg")
        logger.info("voice_transcribed", preview=transcription[:80])
        raw_reply = await planner_agent.process(sender=sender, text=transcription, source="voice")
        final_reply = await refiner_service.refine(raw_reply)
        await whatsapp_service.send_text_message(sender, final_reply)
    except Exception as e:
        logger.error("voice_processing_failed", error=str(e))
        await whatsapp_service.send_text_message(
            sender, "Voice note wasn't clear. Please try again or send a text message."
        )


async def _process_image(sender: str, image_id: str) -> None:
    """Download image, run Vision OCR, then route through Planner."""
    from app.agents.planner import planner_agent
    try:
        image_bytes = await whatsapp_service.download_media(image_id)
        import base64
        b64_image = base64.b64encode(image_bytes).decode("utf-8")
        data_url = f"data:image/jpeg;base64,{b64_image}"
        raw_reply = await planner_agent.process(sender=sender, text="[IMAGE]", source="ocr", image_url=data_url)
        final_reply = await refiner_service.refine(raw_reply)
        await whatsapp_service.send_text_message(sender, final_reply)
    except Exception as e:
        logger.error("image_processing_failed", error=str(e))
        await whatsapp_service.send_text_message(
            sender, "Image could not be read clearly. Please send a clearer photo."
        )

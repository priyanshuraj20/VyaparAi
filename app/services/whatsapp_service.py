import re
import json
import httpx
import structlog
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception
from app.core.config import settings

logger = structlog.get_logger()

GRAPH_API_BASE = "https://graph.facebook.com/v18.0"


def _is_retryable(exc: Exception) -> bool:
    """Retry on 5xx or network errors, not on 4xx client errors."""
    if isinstance(exc, httpx.HTTPStatusError):
        return exc.response.status_code >= 500
    return isinstance(exc, (httpx.ConnectError, httpx.TimeoutException, httpx.RemoteProtocolError))


class WhatsAppService:
    """Handles sending and receiving via Meta Cloud API with retry logic and connection pooling."""

    def __init__(self):
        self.phone_number_id = settings.WHATSAPP_PHONE_NUMBER_ID
        self.access_token = settings.WHATSAPP_ACCESS_TOKEN
        self.headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }
        self._client: httpx.AsyncClient | None = None

    def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=15.0)
        return self._client

    def _log_api_error(self, resp: httpx.Response, url: str, payload: dict = None) -> None:
        """Log full structured Meta Graph API error diagnostics."""
        meta_error = {}
        error_code = None
        error_message = None
        error_data = None

        try:
            body = resp.json()
            if isinstance(body, dict):
                meta_error = body.get("error", {})
                error_code = meta_error.get("code")
                error_message = meta_error.get("message")
                error_data = meta_error.get("error_data")
        except Exception:
            pass

        logger.error(
            "whatsapp_graph_api_error",
            url=url,
            status=resp.status_code,
            payload=payload,
            response_body=resp.text,
            meta_error_code=error_code,
            meta_error_message=error_message,
            meta_error_data=error_data,
        )

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=8),
        retry=retry_if_exception(_is_retryable),
        reraise=True,
    )
    async def send_text_message(self, to: str, body: str) -> dict:
        """Send a plain text WhatsApp message. Retries up to 3x on network/5xx errors."""
        clean_to = re.sub(r"\D", "", to or "")
        url = f"{GRAPH_API_BASE}/{self.phone_number_id}/messages"
        payload = {
            "messaging_product": "whatsapp",
            "to": clean_to,
            "type": "text",
            "text": {"body": body},
        }
        client = self._get_client()
        resp = await client.post(url, json=payload, headers=self.headers)
        if resp.is_error:
            self._log_api_error(resp, url, payload)
        else:
            logger.info(
    "whatsapp_send",
    to=clean_to,
    status=resp.status_code,
    response=resp.json(),
)
        resp.raise_for_status()
        return resp.json()

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=8),
        retry=retry_if_exception(_is_retryable),
        reraise=True,
    )
    async def send_template_message(self, to: str, template_name: str, language_code: str = "hi") -> dict:
        """Send a Meta-approved template message (for outside 24-hr window)."""
        clean_to = re.sub(r"\D", "", to or "")
        url = f"{GRAPH_API_BASE}/{self.phone_number_id}/messages"
        payload = {
            "messaging_product": "whatsapp",
            "to": clean_to,
            "type": "template",
            "template": {
                "name": template_name,
                "language": {"code": language_code},
            },
        }
        client = self._get_client()
        resp = await client.post(url, json=payload, headers=self.headers)
        if resp.is_error:
            self._log_api_error(resp, url, payload)
        else:
            logger.info("whatsapp_template_send", to=clean_to, template=template_name, status=resp.status_code)
        resp.raise_for_status()
        return resp.json()

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=8),
        retry=retry_if_exception(_is_retryable),
        reraise=True,
    )
    async def download_media(self, media_id: str) -> bytes:
        """Download WhatsApp media file. Retries up to 3x."""
        url = f"{GRAPH_API_BASE}/{media_id}"
        client = self._get_client()
        meta_resp = await client.get(url, headers=self.headers)
        if meta_resp.is_error:
            self._log_api_error(meta_resp, url)
        meta_resp.raise_for_status()
        media_url = meta_resp.json()["url"]

        file_resp = await client.get(media_url, headers=self.headers)
        if file_resp.is_error:
            self._log_api_error(file_resp, media_url)
        file_resp.raise_for_status()
        logger.info("whatsapp_media_download", media_id=media_id, size=len(file_resp.content))
        return file_resp.content

    def is_owner(self, sender_number: str) -> bool:
        """Verify the sender is the registered store owner."""
        def _normalize(val: str) -> str:
            cleaned = re.sub(r"\D", "", val or "")
            return "91" + cleaned if len(cleaned) == 10 else cleaned

        return _normalize(sender_number) == _normalize(settings.OWNER_PHONE_NUMBER)

    async def close(self):
        """Close HTTP client session on app shutdown."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()


whatsapp_service = WhatsAppService()

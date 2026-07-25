import json
import httpx
import structlog
from typing import Optional, Any
from app.core.config import settings

logger = structlog.get_logger()

PENDING_ACTION_TTL = 1800  # 30 minutes TTL
IDEMPOTENCY_TTL = 86400    # 24 hours TTL


class UpstashRedisStore:
    """
    Upstash Redis client for temporary conversation state ONLY:
    - Pending action / candidate confirmations (30 min TTL)
    - Last transaction reference & undo context (24 hours / 30 min TTL)
    - Idempotency message IDs (24 hours TTL)

    PostgreSQL remains 100% the primary database & source of truth.
    Redis DOES NOT store customers, ledgers, reports, or reminders.
    """

    def __init__(self):
        self.url = settings.UPSTASH_REDIS_REST_URL
        self.token = settings.UPSTASH_REDIS_REST_TOKEN

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
        }

    async def _cmd(self, command: list) -> Any:
        """Executes a Redis command array via Upstash REST API."""
        if not self.url or not self.token:
            return None
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                r = await client.post(self.url, json=command, headers=self._headers())
                if r.status_code == 200:
                    data = r.json()
                    return data.get("result")
                logger.warning("upstash_redis_cmd_failed", status=r.status_code, body=r.text)
                return None
        except Exception as e:
            logger.warning("upstash_redis_exception", error=str(e))
            return None

    # ── 1. Idempotency (Duplicate Webhook Delivery Check) ────────────────────
    async def is_duplicate_message(self, message_id: str) -> bool:
        """
        Returns True if message_id has already been processed within 24h.
        Uses Redis SET NX (set if not exists) for atomic idempotency check.
        """
        if not message_id:
            return False
        key = f"msg:{message_id}"
        # SET key 1 NX EX 86400 -> returns "OK" if new, None if already exists
        res = await self._cmd(["SET", key, "1", "NX", "EX", IDEMPOTENCY_TTL])
        is_dup = (res is None)
        if is_dup:
            logger.info("duplicate_whatsapp_message_blocked", message_id=message_id)
        return is_dup

    # ── 2. Pending Confirmation State (30 min TTL) ───────────────────────────
    async def set_pending_action(self, sender: str, pending_data: dict, ttl: int = PENDING_ACTION_TTL) -> None:
        """Stores temporary pending action state with automatic TTL expiry."""
        key = f"pending:{sender}"
        val_str = json.dumps(pending_data)
        await self._cmd(["SET", key, val_str, "EX", ttl])
        logger.info("redis_pending_action_set", sender=sender, action_type=pending_data.get("action_type"))

    async def get_pending_action(self, sender: str) -> Optional[dict]:
        """Retrieves pending action state from Redis. Returns None if expired or missing."""
        key = f"pending:{sender}"
        res = await self._cmd(["GET", key])
        if not res:
            return None
        try:
            return json.loads(res)
        except Exception:
            return None

    async def clear_pending_action(self, sender: str) -> None:
        """Clears pending action state upon execution or cancelation."""
        key = f"pending:{sender}"
        await self._cmd(["DEL", key])

    # ── 3. Last Transaction Reference (for Undo) ──────────────────────────────
    async def set_last_transaction_id(self, sender: str, txn_id: Optional[str]) -> None:
        key = f"last_txn:{sender}"
        if txn_id:
            await self._cmd(["SET", key, txn_id, "EX", IDEMPOTENCY_TTL])
        else:
            await self._cmd(["DEL", key])

    async def get_last_transaction_id(self, sender: str) -> Optional[str]:
        key = f"last_txn:{sender}"
        res = await self._cmd(["GET", key])
        return res if isinstance(res, str) else None

    # ── 4. Smart Correction Context (after Undo) ─────────────────────────────
    async def set_last_undone_context(self, sender: str, context: Optional[dict]) -> None:
        key = f"undone:{sender}"
        if context:
            await self._cmd(["SET", key, json.dumps(context), "EX", PENDING_ACTION_TTL])
        else:
            await self._cmd(["DEL", key])

    async def get_last_undone_context(self, sender: str) -> Optional[dict]:
        key = f"undone:{sender}"
        res = await self._cmd(["GET", key])
        if not res:
            return None
        try:
            return json.loads(res)
        except Exception:
            return None

    async def clear_last_undone_context(self, sender: str) -> None:
        key = f"undone:{sender}"
        await self._cmd(["DEL", key])


redis_store = UpstashRedisStore()

from typing import Any, Optional
from dataclasses import dataclass, field
from datetime import datetime, timezone

PENDING_ACTION_TTL_SECONDS = 900  # 15 minutes
SESSION_INACTIVE_TTL_SECONDS = 86400  # 24 hours


@dataclass
class PendingAction:
    """Represents an action awaiting owner confirmation."""
    action_type: str              # e.g., "add_transaction", "send_reminder"
    payload: dict                 # action arguments
    draft_message: str            # description shown to papa
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def is_expired(self, ttl_seconds: int = PENDING_ACTION_TTL_SECONDS) -> bool:
        elapsed = (datetime.now(timezone.utc) - self.created_at).total_seconds()
        return elapsed > ttl_seconds


@dataclass
class SessionState:
    """Per-sender in-memory session: confirmations, last action, recent turns."""
    sender: str
    _pending_action: Optional[PendingAction] = field(default=None, repr=False)
    last_transaction_id: Optional[str] = None          # for undo
    last_customer_name: Optional[str] = None           # context resolution
    last_undone_context: Optional[dict] = None         # for smart correction ("actually 500")
    conversation_history: list[dict] = field(default_factory=list)  # recent turns for LLM context
    last_accessed_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def touch(self):
        self.last_accessed_at = datetime.now(timezone.utc)

    @property
    def pending_action(self) -> Optional[PendingAction]:
        if self._pending_action and self._pending_action.is_expired():
            self._pending_action = None
        return self._pending_action

    @pending_action.setter
    def pending_action(self, action: Optional[PendingAction]):
        self.touch()
        self._pending_action = action

    def add_turn(self, role: str, content: str):
        """Add a conversation turn; keep only last 10 for context window."""
        self.touch()
        self.conversation_history.append({"role": role, "content": content})
        if len(self.conversation_history) > 10:
            self.conversation_history = self.conversation_history[-10:]

    def clear_pending(self):
        self.touch()
        self._pending_action = None

    def set_pending(self, action: PendingAction):
        self.pending_action = action


class SessionStore:
    """
    In-memory store for per-sender sessions with auto-eviction.
    Single-store MVP — simple, efficient, and TTL aware.
    """

    def __init__(self):
        self._store: dict[str, SessionState] = {}

    def get(self, sender: str) -> SessionState:
        if sender not in self._store:
            self._store[sender] = SessionState(sender=sender)
        state = self._store[sender]
        state.touch()
        _ = state.pending_action
        return state

    def clear(self, sender: str):
        self._store.pop(sender, None)

    def has_pending(self, sender: str) -> bool:
        state = self._store.get(sender)
        return state is not None and state.pending_action is not None

    def cleanup_inactive(self, max_inactive_seconds: int = SESSION_INACTIVE_TTL_SECONDS):
        """Evicts sessions that have been inactive for > max_inactive_seconds."""
        now = datetime.now(timezone.utc)
        expired_senders = [
            s for s, state in self._store.items()
            if (now - state.last_accessed_at).total_seconds() > max_inactive_seconds
        ]
        for s in expired_senders:
            self._store.pop(s, None)


# Global singleton
session_store = SessionStore()

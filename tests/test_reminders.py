import pytest
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.db.models import Base


@pytest.fixture
async def db_session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        yield session
    await engine.dispose()


@pytest.mark.asyncio
async def test_propose_reminder_requires_approval(db_session):
    from app.tools.customer_tool import create_customer
    from app.tools.reminder_tool import propose_reminder

    cust = await create_customer(db_session, "Deepak Verma", phone="9876543211")
    cid = cust["customer_id"]

    result = await propose_reminder(db_session, cid, outstanding_amount=750.0, days_overdue=35)
    # CRITICAL: requires_approval must ALWAYS be True
    assert result["requires_approval"] is True
    assert "draft_message" in result
    assert "reminder_id" in result
    assert "750" in result["draft_message"] or "₹750" in result["draft_message"]


@pytest.mark.asyncio
async def test_reminder_never_auto_sent(db_session):
    """Verify send_reminder requires reminder_id (can't call without propose first)."""
    from app.tools.reminder_tool import send_reminder

    with pytest.raises((ValueError, Exception)):
        await send_reminder(db_session, "nonexistent-id", channel="conversational")


@pytest.mark.asyncio
async def test_session_store_pending():
    from app.memory.session_store import SessionStore, PendingAction

    store = SessionStore()
    session = store.get("919876543210")
    assert session.pending_action is None
    assert not store.has_pending("919876543210")

    session.set_pending(PendingAction(
        action_type="add_transaction",
        payload={"amount": 500},
        draft_message="₹500 record karu?",
    ))
    assert store.has_pending("919876543210")
    session.clear_pending()
    assert not store.has_pending("919876543210")


@pytest.mark.asyncio
async def test_session_store_ttl_expiry():
    from datetime import datetime, timezone, timedelta
    from app.memory.session_store import SessionStore, PendingAction

    store = SessionStore()
    session = store.get("919999999999")

    # Created 20 minutes ago (past 15-minute TTL)
    old_time = datetime.now(timezone.utc) - timedelta(minutes=20)
    session.set_pending(PendingAction(
        action_type="add_transaction",
        payload={"amount": 1000},
        draft_message="Expired action",
        created_at=old_time
    ))

    # Should evaluate as expired and return None
    assert session.pending_action is None
    assert not store.has_pending("919999999999")

"""
Sprint 7 — End-to-End Integration Test
Tests the full business flow:
  Customer created → Credit recorded → Payment received →
  Balance verified → Outstanding report → Reminder proposed → Session undo
No LLM calls — all deterministic tool layer.
"""
import pytest
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.db.models import Base


@pytest.fixture
async def db():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        yield session
    await engine.dispose()


@pytest.mark.asyncio
async def test_full_business_flow(db):
    from app.tools.customer_tool import create_customer, resolve_customer, get_customer_history
    from app.tools.ledger_tool import add_transaction, undo_last, get_live_balance
    from app.tools.report_tool import get_outstanding_report, get_daily_report
    from app.tools.reminder_tool import propose_reminder

    # ── Step 1: Create customers ──────────────────────────────────────────────
    ram = await create_customer(db, name="Ram Sharma", phone="9876540001")
    sita = await create_customer(db, name="Sita Devi", phone="9876540002")
    assert ram["customer_id"] and sita["customer_id"]

    # ── Step 2: Credit to Ram ─────────────────────────────────────────────────
    txn1 = await add_transaction(db, ram["customer_id"], "credit_given", 650.0,
                                  item_description="Atta, oil", confidence=0.95)
    assert txn1["status"] == "confirmed"
    assert txn1["new_balance"] == 650.0

    # ── Step 3: Credit to Sita ────────────────────────────────────────────────
    await add_transaction(db, sita["customer_id"], "credit_given", 320.0, confidence=1.0)

    # ── Step 4: Partial payment from Ram ─────────────────────────────────────
    txn2 = await add_transaction(db, ram["customer_id"], "payment_received", 200.0, confidence=1.0)
    assert txn2["new_balance"] == 450.0

    # ── Step 5: Live balance — single source of truth ─────────────────────────
    balance = await get_live_balance(db, ram["customer_id"])
    assert balance == 450.0

    # ── Step 6: Customer history ──────────────────────────────────────────────
    history = await get_customer_history(db, ram["customer_id"])
    assert history["outstanding_balance"] == 450.0
    assert len(history["transactions"]) == 2
    assert history["last_payment_date"] is not None

    # ── Step 7: Fuzzy customer resolve ───────────────────────────────────────
    resolved = await resolve_customer(db, "Ram")
    assert resolved["match_confidence"] >= 0.85
    assert resolved["customer_id"] == ram["customer_id"]

    # ── Step 8: Daily report ──────────────────────────────────────────────────
    daily = await get_daily_report(db)
    assert daily["total_credit_given"] == 970.0   # 650 + 320
    assert daily["total_payment_received"] == 200.0

    # ── Step 9: Outstanding report — only positive balances ───────────────────
    outstanding = await get_outstanding_report(db)
    assert outstanding["total_outstanding"] == 770.0  # 450 + 320
    assert len(outstanding["customers"]) == 2
    # Highest balance first
    assert outstanding["customers"][0]["outstanding_balance"] == 450.0

    # ── Step 10: Propose reminder (NEVER auto-send) ───────────────────────────
    reminder = await propose_reminder(db, ram["customer_id"],
                                      outstanding_amount=450.0, days_overdue=32)
    assert reminder["requires_approval"] is True
    assert "Ram Sharma" in reminder["draft_message"]
    assert "450" in reminder["draft_message"]

    # ── Step 11: Undo last transaction (undo payment) ─────────────────────────
    undo = await undo_last(db, txn2["transaction_id"])
    assert undo["status"] == "undone"
    # Balance back to 650 after undoing the 200 payment
    assert await get_live_balance(db, ram["customer_id"]) == 650.0


@pytest.mark.asyncio
async def test_low_confidence_never_affects_balance(db):
    """Transactions below 0.85 confidence must not change live balance."""
    from app.tools.customer_tool import create_customer
    from app.tools.ledger_tool import add_transaction, get_live_balance

    cust = await create_customer(db, "Test Low Conf")
    cid = cust["customer_id"]

    result = await add_transaction(db, cid, "credit_given", 999.0, confidence=0.50)
    assert result["status"] == "pending_confirmation"
    assert await get_live_balance(db, cid) == 0.0  # MUST be 0 — not yet confirmed


@pytest.mark.asyncio
async def test_duplicate_transaction_blocked(db):
    """Duplicate entries within 5-min window must raise ValueError."""
    from app.tools.customer_tool import create_customer
    from app.tools.ledger_tool import add_transaction

    cust = await create_customer(db, "Duplicate Test")
    cid = cust["customer_id"]

    await add_transaction(db, cid, "credit_given", 500.0, confidence=1.0)
    with pytest.raises(ValueError, match="Duplicate"):
        await add_transaction(db, cid, "credit_given", 500.0, confidence=1.0)


@pytest.mark.asyncio
async def test_session_store_confirmation_flow():
    """Test the in-memory session pending/confirm/deny cycle."""
    from app.memory.session_store import SessionStore, PendingAction

    store = SessionStore()
    sender = "919876543210"
    session = store.get(sender)

    # No pending initially
    assert not store.has_pending(sender)

    # Set pending action
    session.set_pending(PendingAction(
        action_type="add_transaction",
        payload={"customer_id": "abc", "amount": 650},
        draft_message="₹650 record karu? (haan/nahi)",
    ))
    assert store.has_pending(sender)
    assert session.pending_action.action_type == "add_transaction"

    # Confirm clears it
    session.clear_pending()
    assert not store.has_pending(sender)

    # Conversation history tracking
    session.add_turn("user", "Ram ko 650 udhaar diya")
    session.add_turn("assistant", "✅ Record ho gaya!")
    assert len(session.conversation_history) == 2

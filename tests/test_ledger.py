import pytest
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.db.models import Base, Customer


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
async def test_add_credit_transaction(db_session):
    from app.tools.customer_tool import create_customer
    from app.tools.ledger_tool import add_transaction, get_live_balance

    cust = await create_customer(db_session, name="Ram Sharma", phone="9876543210")
    customer_id = cust["customer_id"]

    result = await add_transaction(
        db_session, customer_id=customer_id,
        transaction_type="credit_given", amount=650.0,
        source="text", confidence=0.95
    )
    assert result["status"] == "confirmed"
    assert result["new_balance"] == 650.0

    # Verify single source of truth — live balance
    live = await get_live_balance(db_session, customer_id)
    assert live == 650.0


@pytest.mark.asyncio
async def test_payment_reduces_balance(db_session):
    from app.tools.customer_tool import create_customer
    from app.tools.ledger_tool import add_transaction, get_live_balance

    cust = await create_customer(db_session, name="Suresh Kumar")
    cid = cust["customer_id"]

    await add_transaction(db_session, cid, "credit_given", 1000.0, confidence=1.0)
    await add_transaction(db_session, cid, "payment_received", 400.0, confidence=1.0)

    balance = await get_live_balance(db_session, cid)
    assert balance == 600.0


@pytest.mark.asyncio
async def test_low_confidence_creates_pending(db_session):
    from app.tools.customer_tool import create_customer
    from app.tools.ledger_tool import add_transaction

    cust = await create_customer(db_session, name="Mohan Lal")
    cid = cust["customer_id"]

    result = await add_transaction(
        db_session, cid, "credit_given", 500.0,
        confidence=0.70   # below threshold
    )
    assert result["status"] == "pending_confirmation"
    # Balance should be 0 since not confirmed
    from app.tools.ledger_tool import get_live_balance
    assert await get_live_balance(db_session, cid) == 0.0


@pytest.mark.asyncio
async def test_undo_transaction(db_session):
    from app.tools.customer_tool import create_customer
    from app.tools.ledger_tool import add_transaction, undo_last, get_live_balance

    cust = await create_customer(db_session, name="Vijay Singh")
    cid = cust["customer_id"]

    res = await add_transaction(db_session, cid, "credit_given", 300.0, confidence=1.0)
    assert await get_live_balance(db_session, cid) == 300.0

    undo = await undo_last(db_session, res["transaction_id"])
    assert undo["status"] == "undone"
    assert await get_live_balance(db_session, cid) == 0.0


@pytest.mark.asyncio
async def test_duplicate_detection(db_session):
    from app.tools.customer_tool import create_customer
    from app.tools.ledger_tool import add_transaction

    cust = await create_customer(db_session, name="Ramesh Yadav")
    cid = cust["customer_id"]

    await add_transaction(db_session, cid, "credit_given", 200.0, confidence=1.0)
    with pytest.raises(ValueError, match="Duplicate"):
        await add_transaction(db_session, cid, "credit_given", 200.0, confidence=1.0)

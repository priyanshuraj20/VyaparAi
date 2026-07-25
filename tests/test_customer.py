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
async def test_resolve_customer_exact_match(db_session):
    from app.tools.customer_tool import create_customer, resolve_customer

    await create_customer(db_session, name="Ram Sharma")
    result = await resolve_customer(db_session, "Ram Sharma")
    assert result["match_confidence"] == 1.0
    assert result["customer_name"] == "Ram Sharma"


@pytest.mark.asyncio
async def test_resolve_customer_partial_match(db_session):
    from app.tools.customer_tool import create_customer, resolve_customer

    await create_customer(db_session, name="Ram Sharma")
    result = await resolve_customer(db_session, "Ram")
    assert result["match_confidence"] >= 0.85
    assert "Ram" in result["customer_name"]


@pytest.mark.asyncio
async def test_resolve_customer_no_match_raises(db_session):
    from app.tools.customer_tool import resolve_customer

    with pytest.raises(ValueError, match="NoMatchFound"):
        await resolve_customer(db_session, "Xyz Unknown Person")


@pytest.mark.asyncio
async def test_customer_history_live_balance(db_session):
    from app.tools.customer_tool import create_customer, get_customer_history
    from app.tools.ledger_tool import add_transaction

    cust = await create_customer(db_session, "Sita Devi")
    cid = cust["customer_id"]
    await add_transaction(db_session, cid, "credit_given", 500.0, confidence=1.0)
    await add_transaction(db_session, cid, "payment_received", 150.0, confidence=1.0)

    history = await get_customer_history(db_session, cid)
    assert history["outstanding_balance"] == 350.0
    assert len(history["transactions"]) == 2

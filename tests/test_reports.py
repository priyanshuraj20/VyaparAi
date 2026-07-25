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
async def test_daily_report_empty(db_session):
    from app.tools.report_tool import get_daily_report
    report = await get_daily_report(db_session)
    assert report["total_credit_given"] == 0.0
    assert report["total_payment_received"] == 0.0
    assert report["transaction_count"] == 0


@pytest.mark.asyncio
async def test_daily_report_with_data(db_session):
    from app.tools.customer_tool import create_customer
    from app.tools.ledger_tool import add_transaction
    from app.tools.report_tool import get_daily_report

    cust = await create_customer(db_session, "Govind Das")
    cid = cust["customer_id"]
    await add_transaction(db_session, cid, "credit_given", 800.0, confidence=1.0)
    await add_transaction(db_session, cid, "payment_received", 300.0, confidence=1.0)

    report = await get_daily_report(db_session)
    assert report["total_credit_given"] == 800.0
    assert report["total_payment_received"] == 300.0
    assert report["net_change"] == 500.0


@pytest.mark.asyncio
async def test_outstanding_report(db_session):
    from app.tools.customer_tool import create_customer
    from app.tools.ledger_tool import add_transaction
    from app.tools.report_tool import get_outstanding_report

    c1 = await create_customer(db_session, "Arjun Mehta")
    c2 = await create_customer(db_session, "Priya Gupta")
    await add_transaction(db_session, c1["customer_id"], "credit_given", 500.0, confidence=1.0)
    await add_transaction(db_session, c2["customer_id"], "credit_given", 200.0, confidence=1.0)
    await add_transaction(db_session, c2["customer_id"], "payment_received", 200.0, confidence=1.0)

    report = await get_outstanding_report(db_session)
    # c2 balance = 0, so only c1 should appear
    assert len(report["customers"]) == 1
    assert report["customers"][0]["name"] == "Arjun Mehta"
    assert report["total_outstanding"] == 500.0

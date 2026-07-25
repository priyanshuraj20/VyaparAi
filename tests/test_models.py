import pytest
import uuid
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.db.models import (
    Base,
    Customer,
    Transaction,
    TransactionType,
    TransactionStatus,
    TransactionSource,
    Reminder,
    ReminderChannel,
    Conversation,
    Message,
    MessageDirection,
    MessageType,
    OCRDocument,
)


@pytest.mark.asyncio
async def test_database_models_creation_and_query():
    # In-memory SQLite async engine
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        # Create Customer
        customer = Customer(
            name="Ram Sharma",
            alias_notes="Gandhi Road Kirana store regular",
            phone="919876543210",
            whatsapp_opted_in=True,
            opted_in_at=datetime.now(timezone.utc)
        )
        session.add(customer)
        await session.commit()
        await session.refresh(customer)

        assert customer.id is not None
        assert customer.name == "Ram Sharma"

        # Create Transactions (Credit & Payment)
        txn1 = Transaction(
            customer_id=customer.id,
            type=TransactionType.CREDIT_GIVEN,
            amount=650.00,
            item_description="Atta, Mustard Oil, Rice",
            status=TransactionStatus.CONFIRMED,
            source=TransactionSource.VOICE,
            confidence_score=0.95,
            raw_input="Ram ko 650 ka udhaar diya"
        )
        txn2 = Transaction(
            customer_id=customer.id,
            type=TransactionType.PAYMENT_RECEIVED,
            amount=200.00,
            item_description="Cash payment",
            status=TransactionStatus.CONFIRMED,
            source=TransactionSource.TEXT,
            confidence_score=1.0,
            raw_input="Ram ne 200 diya"
        )
        session.add_all([txn1, txn2])
        await session.commit()

        # Create Reminder
        reminder = Reminder(
            customer_id=customer.id,
            amount_at_time=450.00,
            approved_by_owner=True,
            channel_used=ReminderChannel.CONVERSATIONAL,
            sent_at=datetime.now(timezone.utc)
        )
        session.add(reminder)
        await session.commit()

        # Create Conversation & Message
        conv = Conversation()
        session.add(conv)
        await session.commit()

        msg = Message(
            conversation_id=conv.id,
            direction=MessageDirection.INBOUND,
            type=MessageType.IMAGE,
            content="Photo of handwritten list",
            media_url="https://media.whatsapp.com/sample.jpg"
        )
        session.add(msg)
        await session.commit()

        # Create OCRDocument
        ocr_doc = OCRDocument(
            message_id=msg.id,
            extracted_json={"items": [{"name": "Sugar", "price": 100}]},
            confidence_score=0.90,
            reviewed=True
        )
        session.add(ocr_doc)
        await session.commit()
        await session.refresh(ocr_doc)

        assert ocr_doc.id is not None
        assert ocr_doc.extracted_json["items"][0]["name"] == "Sugar"

    await engine.dispose()

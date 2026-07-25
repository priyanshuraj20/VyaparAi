import uuid
import structlog
from datetime import datetime, timezone, timedelta
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func
from app.db.models import (
    Customer,
    Transaction,
    TransactionStatus,
    TransactionType,
    Reminder,
    ReminderChannel,
)
from app.tools.ledger_tool import get_live_balance

logger = structlog.get_logger()

OVERDUE_DAYS = 30


async def get_overdue_customers(db: AsyncSession) -> list[dict]:
    """
    Identifies customers with outstanding balance and last credit > OVERDUE_DAYS ago.
    """
    overdue_cutoff = (datetime.now(timezone.utc) - timedelta(days=OVERDUE_DAYS)).replace(tzinfo=None)

    # Get last credit date per customer
    subq = (
        select(
            Transaction.customer_id,
            func.max(Transaction.created_at).label("last_credit_at"),
        )
        .where(
            and_(
                Transaction.type == TransactionType.CREDIT_GIVEN,
                Transaction.status == TransactionStatus.CONFIRMED,
            )
        )
        .group_by(Transaction.customer_id)
        .subquery()
    )

    result = await db.execute(
        select(Customer, subq.c.last_credit_at)
        .join(subq, subq.c.customer_id == Customer.id)
        .where(subq.c.last_credit_at <= overdue_cutoff)
    )
    rows = result.all()

    overdue = []
    for customer, last_credit_at in rows:
        balance = await get_live_balance(db, str(customer.id))
        if balance > 0:
            days_overdue = (datetime.now(timezone.utc) - last_credit_at).days
            overdue.append({
                "customer_id": str(customer.id),
                "customer_name": customer.name,
                "outstanding_balance": balance,
                "days_overdue": days_overdue,
                "whatsapp_opted_in": customer.whatsapp_opted_in,
                "phone": customer.phone,
            })

    logger.info("overdue_customers_fetched", count=len(overdue))
    return overdue


async def propose_reminder(
    db: AsyncSession,
    customer_id: str,
    outstanding_amount: float,
    days_overdue: int,
) -> dict:
    """
    Drafts a reminder message and saves a pending Reminder record.
    ALWAYS requires_approval = True — never auto-sent.
    """
    cust_result = await db.execute(
        select(Customer).where(Customer.id == uuid.UUID(customer_id))
    )
    customer = cust_result.scalars().first()
    if not customer:
        raise ValueError(f"CustomerNotFound: {customer_id}")

    draft = (
        f"Namaste {customer.name} ji! 🙏\n"
        f"Aapka ₹{outstanding_amount:.0f} ka hisaab baaki hai.\n"
        f"Suvidha ho to jaldi ada kar dijiye. Dhanyawad!"
    )

    reminder = Reminder(
        customer_id=uuid.UUID(customer_id),
        amount_at_time=outstanding_amount,
    )
    db.add(reminder)
    await db.commit()
    await db.refresh(reminder)

    logger.info("reminder_proposed", customer=customer.name, amount=outstanding_amount)

    return {
        "reminder_id": str(reminder.id),
        "customer_name": customer.name,
        "draft_message": draft,
        "requires_approval": True,
    }


async def send_reminder(
    db: AsyncSession,
    reminder_id: str,
    channel: str,
) -> dict:
    """
    Mark reminder as sent. Actual dispatch is handled by the webhook layer
    (WhatsAppService) which is called before this function.
    """
    result = await db.execute(
        select(Reminder).where(Reminder.id == uuid.UUID(reminder_id))
    )
    reminder = result.scalars().first()
    if not reminder:
        raise ValueError(f"ReminderNotFound: {reminder_id}")

    reminder.approved_by_owner = True
    reminder.channel_used = ReminderChannel(channel)
    reminder.sent_at = datetime.now(timezone.utc).replace(tzinfo=None)
    await db.commit()

    logger.info("reminder_sent", reminder_id=reminder_id, channel=channel)
    return {"reminder_id": reminder_id, "status": "sent", "channel": channel}

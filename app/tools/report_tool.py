import uuid
import structlog
from datetime import datetime, timezone, timedelta
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func, case
from app.db.models import (
    Customer,
    Transaction,
    TransactionType,
    TransactionStatus,
)

logger = structlog.get_logger()

# Report overdue threshold
OVERDUE_DAYS = 30


async def get_daily_report(db: AsyncSession) -> dict:
    """
    Today's udhaar and payment summary.
    Uses live SQL aggregation — no cached values.
    """
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0).replace(tzinfo=None)

    result = await db.execute(
        select(
            func.coalesce(
                func.sum(
                    case(
                        (Transaction.type == TransactionType.CREDIT_GIVEN, Transaction.amount),
                        else_=0
                    )
                ), 0
            ).label("total_credit"),
            func.coalesce(
                func.sum(
                    case(
                        (Transaction.type == TransactionType.PAYMENT_RECEIVED, Transaction.amount),
                        else_=0
                    )
                ), 0
            ).label("total_paid"),
            func.count(Transaction.id.distinct()).label("transaction_count"),
        ).where(
            and_(
                Transaction.status == TransactionStatus.CONFIRMED,
                Transaction.created_at >= today_start,
            )
        )
    )
    row = result.one()
    logger.info("daily_report_generated")
    return {
        "date": str(datetime.now(timezone.utc).date()),
        "total_credit_given": float(row.total_credit),
        "total_payment_received": float(row.total_paid),
        "transaction_count": row.transaction_count,
        "net_change": float(row.total_credit) - float(row.total_paid),
    }


async def get_monthly_report(db: AsyncSession) -> dict:
    """
    This month's udhaar and payment summary.
    """
    now = datetime.now(timezone.utc)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0).replace(tzinfo=None)

    result = await db.execute(
        select(
            func.coalesce(
                func.sum(
                    case(
                        (Transaction.type == TransactionType.CREDIT_GIVEN, Transaction.amount),
                        else_=0
                    )
                ), 0
            ).label("total_credit"),
            func.coalesce(
                func.sum(
                    case(
                        (Transaction.type == TransactionType.PAYMENT_RECEIVED, Transaction.amount),
                        else_=0
                    )
                ), 0
            ).label("total_paid"),
            func.count(Transaction.customer_id.distinct()).label("unique_customers"),
        ).where(
            and_(
                Transaction.status == TransactionStatus.CONFIRMED,
                Transaction.created_at >= month_start,
            )
        )
    )
    row = result.one()
    logger.info("monthly_report_generated", month=now.strftime("%B %Y"))
    return {
        "month": now.strftime("%B %Y"),
        "total_credit_given": float(row.total_credit),
        "total_payment_received": float(row.total_paid),
        "unique_customers": row.unique_customers,
        "net_outstanding_added": float(row.total_credit) - float(row.total_paid),
    }


async def get_outstanding_report(db: AsyncSession) -> dict:
    """
    All customers with a positive outstanding balance.
    Balance always computed live: SUM(credit) - SUM(payments).
    """
    # Aggregate per customer
    result = await db.execute(
        select(
            Customer.id,
            Customer.name,
            func.coalesce(
                func.sum(
                    case(
                        (Transaction.type == TransactionType.CREDIT_GIVEN, Transaction.amount),
                        else_=0
                    )
                ), 0
            ).label("total_credit"),
            func.coalesce(
                func.sum(
                    case(
                        (Transaction.type == TransactionType.PAYMENT_RECEIVED, Transaction.amount),
                        else_=0
                    )
                ), 0
            ).label("total_paid"),
        )
        .join(Transaction, Transaction.customer_id == Customer.id, isouter=True)
        .where(
            and_(
                Transaction.status == TransactionStatus.CONFIRMED,
            )
        )
        .group_by(Customer.id, Customer.name)
    )
    rows = result.all()

    outstanding = [
        {"customer_id": str(row.id), "name": row.name, "outstanding_balance": float(row.total_credit) - float(row.total_paid)}
        for row in rows
        if (float(row.total_credit) - float(row.total_paid)) > 0
    ]
    outstanding.sort(key=lambda x: x["outstanding_balance"], reverse=True)
    total = sum(c["outstanding_balance"] for c in outstanding)

    logger.info("outstanding_report_generated", customers=len(outstanding), total=total)
    return {
        "customers": outstanding,
        "total_outstanding": round(total, 2),
    }

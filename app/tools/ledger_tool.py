import uuid
import structlog
from datetime import datetime, timezone, timedelta
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func, case
from sqlalchemy.exc import IntegrityError
from app.db.models import (
    Customer,
    Transaction,
    TransactionType,
    TransactionStatus,
    TransactionSource,
)

logger = structlog.get_logger()

# Confidence threshold from productDesign §6.3
CONFIDENCE_THRESHOLD = 0.85

# Duplicate detection window (minutes)
DUPLICATE_WINDOW_MINUTES = 5


async def add_transaction(
    db: AsyncSession,
    customer_id: str,
    transaction_type: str,
    amount: float,
    item_description: Optional[str] = None,
    payment_mode: Optional[str] = "Cash",
    source: str = "text",
    confidence: float = 1.0,
    raw_input: Optional[str] = None,
) -> dict:
    """
    Record a credit_given or payment_received transaction.
    - Auto-confirms if confidence >= CONFIDENCE_THRESHOLD
    - Returns pending_confirmation status if below threshold
    - Detects duplicates within DUPLICATE_WINDOW_MINUTES
    """
    if amount <= 0:
        raise ValueError("Amount must be positive")

    try:
        cust_uuid = uuid.UUID(customer_id)
    except ValueError:
        raise ValueError(f"Invalid customer ID format: {customer_id}")

    # Verify customer exists first
    cust_check = await db.execute(select(Customer.id).where(Customer.id == cust_uuid))
    if not cust_check.scalar_one_or_none():
        raise ValueError(f"CustomerNotFound: {customer_id}")

    # ── Duplicate detection ───────────────────────────────────────────────────
    window_start = (datetime.now(timezone.utc) - timedelta(minutes=DUPLICATE_WINDOW_MINUTES)).replace(tzinfo=None)
    dup_result = await db.execute(
        select(Transaction).where(
            and_(
                Transaction.customer_id == cust_uuid,
                Transaction.type == TransactionType(transaction_type),
                Transaction.amount == amount,
                Transaction.status == TransactionStatus.CONFIRMED,
                Transaction.created_at >= window_start,
            )
        )
    )
    if dup_result.scalars().first():
        logger.warning("duplicate_transaction_detected", customer_id=customer_id, amount=amount)
        raise ValueError(
            f"Duplicate transaction detected: ₹{amount:.0f} already recorded in the last {DUPLICATE_WINDOW_MINUTES} minutes."
        )

    # ── Confidence → status ──────────────────────────────────────────────────
    status = (
        TransactionStatus.CONFIRMED
        if confidence >= CONFIDENCE_THRESHOLD
        else TransactionStatus.PENDING_CONFIRMATION
    )

    desc_final = item_description
    if payment_mode and payment_mode != "Cash" and not item_description:
        desc_final = f"Payment Mode: {payment_mode}"

    txn = Transaction(
        customer_id=cust_uuid,
        type=TransactionType(transaction_type),
        amount=amount,
        item_description=desc_final,
        status=status,
        source=TransactionSource(source),
        confidence_score=confidence,
        raw_input=raw_input,
        confirmed_at=datetime.now(timezone.utc).replace(tzinfo=None) if status == TransactionStatus.CONFIRMED else None,
    )
    db.add(txn)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise ValueError(f"CustomerNotFound: {customer_id}")

    await db.refresh(txn)

    new_balance = await get_live_balance(db, customer_id)

    logger.info(
        "transaction_added",
        transaction_id=str(txn.id),
        customer_id=customer_id,
        type=transaction_type,
        amount=amount,
        payment_mode=payment_mode,
        new_balance=new_balance,
        status=status.value,
    )

    return {
        "transaction_id": str(txn.id),
        "customer_id": customer_id,
        "type": transaction_type,
        "amount": amount,
        "payment_mode": payment_mode or "Cash",
        "new_balance": new_balance,
        "status": status.value,
    }


async def undo_last(db: AsyncSession, transaction_id: str) -> dict:
    """
    Reverse (soft-undo) a transaction by marking status as UNDONE.
    Recalculates balance automatically.
    """
    try:
        txn_uuid = uuid.UUID(transaction_id)
    except ValueError:
        raise ValueError(f"Invalid transaction ID format: {transaction_id}")

    result = await db.execute(select(Transaction).where(Transaction.id == txn_uuid))
    txn = result.scalars().first()

    if not txn:
        raise ValueError(f"TransactionNotFound: {transaction_id}")
    if txn.status == TransactionStatus.UNDONE:
        raise ValueError(f"TransactionAlreadyVoid: {transaction_id}")

    txn.status = TransactionStatus.UNDONE
    await db.commit()

    new_balance = await get_live_balance(db, str(txn.customer_id))
    logger.info("transaction_undone", transaction_id=transaction_id, new_balance=new_balance)

    return {
        "status": "undone",
        "transaction_id": transaction_id,
        "customer_id": str(txn.customer_id),
        "new_balance": new_balance,
    }


async def get_live_balance(db: AsyncSession, customer_id: str) -> float:
    """
    Computes live balance: SUM(credit_given) - SUM(payment_received) for CONFIRMED transactions.
    """
    try:
        cust_uuid = uuid.UUID(customer_id)
    except ValueError:
        return 0.0

    result = await db.execute(
        select(
            func.coalesce(
                func.sum(
                    case(
                        (Transaction.type == TransactionType.CREDIT_GIVEN, Transaction.amount),
                        else_=-Transaction.amount,
                    )
                ),
                0.0,
            )
        ).where(
            and_(
                Transaction.customer_id == cust_uuid,
                Transaction.status == TransactionStatus.CONFIRMED,
            )
        )
    )
    return float(result.scalar_one())

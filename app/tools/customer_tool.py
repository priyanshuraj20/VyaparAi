import uuid
import structlog
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_
from app.db.models import Customer, Transaction, TransactionStatus, TransactionType
from app.tools.ledger_tool import get_live_balance

logger = structlog.get_logger()

# Customer match confidence thresholds
HIGH_CONFIDENCE = 0.85


def _fuzzy_score(query: str, name: str) -> float:
    """
    Simple token-based fuzzy matching score (0.0 - 1.0).
    """
    query_lower = query.lower().strip()
    name_lower = name.lower().strip()

    # Exact match
    if query_lower == name_lower:
        return 1.0

    # Name contains query or query contains name
    if query_lower in name_lower or name_lower in query_lower:
        return 0.90

    # Token overlap
    query_tokens = set(query_lower.split())
    name_tokens = set(name_lower.split())
    overlap = query_tokens & name_tokens
    if overlap:
        score = len(overlap) / max(len(query_tokens), len(name_tokens))
        return round(min(score + 0.1, 0.84), 2)

    return 0.0


async def resolve_customer(
    db: AsyncSession,
    name_raw: str,
    context_hint: Optional[str] = None,
) -> dict:
    """
    Fuzzy-match a raw name string against the customer database.
    Returns: customer_id, match_confidence, ambiguous_candidates list.
    """
    result = await db.execute(select(Customer))
    all_customers = result.scalars().all()

    if not all_customers:
        raise ValueError(f"NoMatchFound: No customer found matching '{name_raw}'")

    # Score each customer
    scored = []
    for c in all_customers:
        score = _fuzzy_score(name_raw, c.name)
        if context_hint and c.alias_notes and context_hint.lower() in (c.alias_notes or "").lower():
            score = min(score + 0.1, 1.0)
        if score > 0:
            scored.append((score, c))

    if not scored:
        raise ValueError(f"NoMatchFound: No customer found matching '{name_raw}'")

    scored.sort(key=lambda x: x[0], reverse=True)
    best_score, best_customer = scored[0]

    # Collect all partial/ambiguous candidates (score >= 0.5)
    candidates = []
    for score, c in scored:
        if score >= 0.5:
            bal = await get_live_balance(db, str(c.id))
            candidates.append({
                "customer_id": str(c.id),
                "name": c.name,
                "balance": bal,
                "score": score
            })

    ambiguous = [c["name"] for c in candidates[1:]]

    logger.info(
        "customer_resolved",
        name_raw=name_raw,
        matched=best_customer.name,
        confidence=best_score,
        candidates_count=len(candidates),
    )

    return {
        "customer_id": str(best_customer.id),
        "customer_name": best_customer.name,
        "match_confidence": best_score,
        "ambiguous_candidates": ambiguous,
        "candidates": candidates,
    }


async def get_customer_history(db: AsyncSession, customer_id: str) -> dict:
    """
    Returns a customer's full transaction history and live outstanding balance.
    """
    cust_result = await db.execute(
        select(Customer).where(Customer.id == uuid.UUID(customer_id))
    )
    customer = cust_result.scalars().first()
    if not customer:
        raise ValueError(f"CustomerNotFound: {customer_id}")

    txn_result = await db.execute(
        select(Transaction).where(
            and_(
                Transaction.customer_id == uuid.UUID(customer_id),
                Transaction.status == TransactionStatus.CONFIRMED,
            )
        ).order_by(Transaction.created_at.desc())
    )
    transactions = txn_result.scalars().all()

    balance = await get_live_balance(db, customer_id)
    last_payment = next(
        (t for t in transactions if t.type == TransactionType.PAYMENT_RECEIVED), None
    )

    logger.info("customer_history_fetched", customer_id=customer_id, txn_count=len(transactions))

    return {
        "customer_id": customer_id,
        "customer_name": customer.name,
        "outstanding_balance": balance,
        "last_payment_date": str(last_payment.created_at.date()) if last_payment else None,
        "transactions": [
            {
                "id": str(t.id),
                "type": t.type.value,
                "amount": float(t.amount),
                "description": t.item_description,
                "date": str(t.created_at.date()),
                "source": t.source.value,
            }
            for t in transactions
        ],
    }


async def create_customer(db: AsyncSession, name: str, phone: Optional[str] = None, alias_notes: Optional[str] = None) -> dict:
    """Create a new customer record."""
    customer = Customer(name=name, phone=phone, alias_notes=alias_notes)
    db.add(customer)
    await db.commit()
    await db.refresh(customer)
    logger.info("customer_created", name=name, id=str(customer.id))
    return {"customer_id": str(customer.id), "name": customer.name}

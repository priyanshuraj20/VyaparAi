from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.tools.customer_tool import get_customer_history
from app.tools.ledger_tool import get_live_balance
from app.schemas import CustomerResponse, BalanceResponse
import structlog

logger = structlog.get_logger()

router = APIRouter(prefix="/customer", tags=["Customer"])


@router.get("/{customer_id}", response_model=CustomerResponse)
async def get_customer(
    customer_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get a customer's profile + full transaction history with live balance."""
    try:
        result = await get_customer_history(db, customer_id)
        return CustomerResponse(**result)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error("get_customer_failed", error=str(e))
        raise HTTPException(status_code=500, detail="Internal error")


@router.get("/{customer_id}/balance", response_model=BalanceResponse)
async def get_balance(
    customer_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get current outstanding balance for a customer — live computed, never cached."""
    try:
        balance = await get_live_balance(db, customer_id)
        return BalanceResponse(customer_id=customer_id, outstanding_balance=balance)
    except Exception as e:
        logger.error("get_balance_failed", error=str(e))
        raise HTTPException(status_code=500, detail="Internal error")

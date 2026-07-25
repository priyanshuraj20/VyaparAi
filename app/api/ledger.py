from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.schemas import CreateTransactionRequest, TransactionResponse
from app.tools.ledger_tool import add_transaction, undo_last
import structlog

logger = structlog.get_logger()

router = APIRouter(prefix="/ledger", tags=["Ledger"])


@router.post("", response_model=TransactionResponse)
async def create_transaction(
    body: CreateTransactionRequest,
    db: AsyncSession = Depends(get_db),
):
    """Manually create a transaction — fallback/admin use."""
    try:
        result = await add_transaction(
            db=db,
            customer_id=body.customer_id,
            transaction_type=body.transaction_type.value,
            amount=body.amount,
            item_description=body.item_description,
            source=body.source,
            confidence=body.confidence,
        )
        return TransactionResponse(**result)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("ledger_create_failed", error=str(e))
        raise HTTPException(status_code=500, detail="Internal error")

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.tools.ledger_tool import undo_last
import structlog

logger = structlog.get_logger()

router = APIRouter(prefix="/transaction", tags=["Transactions"])


@router.post("/{transaction_id}/undo")
async def undo_transaction(
    transaction_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Reverse a transaction within the undo window — marks as 'undone', preserves audit trail."""
    try:
        result = await undo_last(db, transaction_id)
        logger.info("transaction_undone_via_api", transaction_id=transaction_id)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error("transaction_undo_failed", error=str(e))
        raise HTTPException(status_code=500, detail="Internal error")

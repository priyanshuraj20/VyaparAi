from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.tools.reminder_tool import propose_reminder, send_reminder
from app.tools.ledger_tool import get_live_balance
from app.schemas import ReminderRequest, ReminderResponse
import structlog

logger = structlog.get_logger()

router = APIRouter(prefix="/reminder", tags=["Reminders"])


@router.post("", response_model=ReminderResponse)
async def create_reminder(
    body: ReminderRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Propose a reminder for a customer — always requires owner approval.
    Never auto-sent. Returns draft message for papa to review.
    """
    try:
        # Fetch live balance if not provided
        balance = body.outstanding_amount or await get_live_balance(db, body.customer_id)
        result = await propose_reminder(
            db=db,
            customer_id=body.customer_id,
            outstanding_amount=balance,
            days_overdue=body.days_overdue,
        )
        return ReminderResponse(**result)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error("reminder_propose_failed", error=str(e))
        raise HTTPException(status_code=500, detail="Internal error")


@router.post("/{reminder_id}/approve")
async def approve_reminder(
    reminder_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Owner explicitly approves a pending reminder.
    After this, the channel-aware send logic dispatches it.
    """
    try:
        # For MVP: default channel logic — conversational
        # Production: check 24hr window here
        result = await send_reminder(db, reminder_id, channel="conversational")
        logger.info("reminder_approved_via_api", reminder_id=reminder_id)
        return {"status": "approved_and_sent", "reminder_id": reminder_id, "channel": result["channel"]}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error("reminder_approve_failed", error=str(e))
        raise HTTPException(status_code=500, detail="Internal error")

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.tools.report_tool import get_daily_report, get_monthly_report, get_outstanding_report
import structlog

logger = structlog.get_logger()

router = APIRouter(prefix="/reports", tags=["Reports"])


@router.get("/daily")
async def daily_report(db: AsyncSession = Depends(get_db)):
    """Today's credit and payment summary — live SQL aggregation."""
    logger.info("daily_report_requested")
    return await get_daily_report(db)


@router.get("/monthly")
async def monthly_report(db: AsyncSession = Depends(get_db)):
    """This month's credit and payment summary — live SQL aggregation."""
    logger.info("monthly_report_requested")
    return await get_monthly_report(db)


@router.get("/outstanding")
async def outstanding_report(db: AsyncSession = Depends(get_db)):
    """All customers with outstanding balance > 0, sorted highest first."""
    logger.info("outstanding_report_requested")
    return await get_outstanding_report(db)

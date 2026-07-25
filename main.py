from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import structlog
from app.core.config import settings
from app.core.logging import setup_logging
from app.api import webhook, reports, ledger, customers, ocr, reminders, transactions

from app.services.whatsapp_service import whatsapp_service

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    logger.info(
        "VyaparAI starting",
        environment=settings.ENVIRONMENT,
        owner=settings.OWNER_PHONE_NUMBER,
        phone_number_id=settings.WHATSAPP_PHONE_NUMBER_ID,
    )
    yield
    await whatsapp_service.close()
    logger.info("VyaparAI shutting down")


app = FastAPI(
    title="VyaparAI API",
    description="AI Business Manager for Kirana Stores — WhatsApp native",
    version="1.0.0",
    docs_url="/docs" if settings.ENVIRONMENT != "production" else None,
    redoc_url=None,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

# ── Routes ────────────────────────────────────────────────────────────────────
app.include_router(webhook.router)
app.include_router(reports.router)
app.include_router(ledger.router)
app.include_router(customers.router)
app.include_router(ocr.router)
app.include_router(reminders.router)
app.include_router(transactions.router)


@app.get("/health", tags=["System"])
async def health_check():
    return {
        "status": "ok",
        "service": "VyaparAI",
        "environment": settings.ENVIRONMENT,
        "version": "1.0.0",
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=(settings.ENVIRONMENT == "development"),
        log_level=settings.LOG_LEVEL.lower(),
    )

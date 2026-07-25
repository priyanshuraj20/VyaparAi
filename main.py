from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
import structlog
from app.core.config import settings
from app.core.logging import setup_logging
from app.api import webhook, reports, ledger, customers, ocr, reminders, transactions, landing

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
    description="Agentic AI WhatsApp Business Ledger Assistant",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# ── Static Files & Templates ──────────────────────────────────────────────────
static_dir = Path(__file__).resolve().parent / "app" / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

# ── Routes ────────────────────────────────────────────────────────────────────
app.include_router(landing.router)
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

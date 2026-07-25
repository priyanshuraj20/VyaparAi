from pathlib import Path
from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter(tags=["Landing Page"])

TEMPLATE_PATH = Path(__file__).resolve().parent.parent / "templates" / "index.html"


@router.get("/", response_class=HTMLResponse, include_in_schema=False)
async def landing_page():
    if TEMPLATE_PATH.exists():
        html_content = TEMPLATE_PATH.read_text(encoding="utf-8")
        return HTMLResponse(content=html_content)
    return HTMLResponse(content="<h1>VyaparAI API Online</h1>", status_code=200)

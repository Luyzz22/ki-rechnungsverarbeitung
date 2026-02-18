from fastapi import FastAPI, responses
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from budget_routes import router as budget_router
from invoice_api import router as invoice_router  # <— NEU

app = FastAPI()

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:3001",
        "https://sbsnexus.de",
        "https://www.sbsnexus.de",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "web" / "static"

# statische Dateien (Logo, CSS usw.)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/landing", response_class=responses.HTMLResponse)
async def landing_page():
    index_path = STATIC_DIR / "landing" / "index.html"
    return responses.FileResponse(index_path)


# vorhandene Router
app.include_router(budget_router)

# NEU: Invoice-API (POST /api/v1/process)
app.include_router(invoice_router)

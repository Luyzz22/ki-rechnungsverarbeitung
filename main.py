from fastapi import FastAPI, responses
from budget_routes import router as budget_router
from fastapi.staticfiles import StaticFiles
from pathlib import Path

app = FastAPI()

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "web" / "static"

# statische Dateien (Logo, CSS usw.)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

@app.get("/landing", response_class=responses.HTMLResponse)
async def landing_page():
    index_path = STATIC_DIR / "landing" / "index.html"
    return responses.FileResponse(index_path)

"""
Budget API Routes für SBS Invoice System
"""
from fastapi import APIRouter, Request, Query, HTTPException
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

from budget_service import BudgetService

router = APIRouter(tags=["Budget"])
templates = Jinja2Templates(directory="web/templates")
budget_service = BudgetService()

MONAT_NAMEN = ["Januar", "Februar", "März", "April", "Mai", "Juni", "Juli", "August", "September", "Oktober", "November", "Dezember"]

class BudgetSetRequest(BaseModel):
    kategorie_id: int
    jahr: int
    monat: int
    betrag: float
    notiz: Optional[str] = None

class BudgetCopyRequest(BaseModel):
    von_jahr: int
    von_monat: int
    nach_jahr: int
    nach_monat: int
    prozent_aenderung: float = 0

@router.get("/budget", response_class=HTMLResponse)
async def budget_dashboard(request: Request, jahr: int = Query(default=None), monat: int = Query(default=None)):
    if jahr is None:
        jahr = datetime.now().year
    if monat is None:
        monat = datetime.now().month
    
    budget_service.update_ist_werte_from_invoices(jahr, monat)
    summary = budget_service.get_dashboard_summary(jahr, monat)
    trend_data = budget_service.get_trend_data(monate_zurueck=12)
    pie_data = budget_service.get_kategorie_verteilung(jahr, monat)
    
    return templates.TemplateResponse("budget.html", {
        "request": request, "jahr": jahr, "monat": monat,
        "monat_namen": MONAT_NAMEN, "summary": summary,
        "trend_data": trend_data, "pie_data": pie_data
    })

@router.get("/budget/jahr", response_class=HTMLResponse)
async def budget_jahresansicht(request: Request, jahr: int = Query(default=None)):
    if jahr is None:
        jahr = datetime.now().year
    jahresbudget = budget_service.get_jahresbudget(jahr)
    return templates.TemplateResponse("budget_jahr.html", {
        "request": request, "jahr": jahr, "monat_namen": MONAT_NAMEN, "jahresbudget": jahresbudget
    })

@router.get("/api/budget/kategorien")
async def get_kategorien(nur_aktive: bool = Query(default=True), mit_budget: bool = Query(default=False), jahr: int = Query(default=None), monat: int = Query(default=None)):
    kategorien = budget_service.get_kategorien(nur_aktive)
    if mit_budget and jahr and monat:
        auswertungen = budget_service.get_monatsauswertung(jahr, monat)
        budget_map = {a["kategorie_id"]: a["budget_soll"] for a in auswertungen}
        for kat in kategorien:
            kat["budget"] = budget_map.get(kat["id"], 0)
    return kategorien

@router.post("/api/budget/set")
async def set_budget(request: BudgetSetRequest):
    try:
        budget_id = budget_service.set_monatsbudget(kategorie_id=request.kategorie_id, jahr=request.jahr, monat=request.monat, betrag=request.betrag, notiz=request.notiz)
        return {"success": True, "budget_id": budget_id}
    except Exception as e:
        return {"success": False, "error": str(e)}

@router.post("/api/budget/copy")
async def copy_budgets(request: BudgetCopyRequest):
    try:
        kopiert = budget_service.copy_budgets_to_month(von_jahr=request.von_jahr, von_monat=request.von_monat, nach_jahr=request.nach_jahr, nach_monat=request.nach_monat, prozent_aenderung=request.prozent_aenderung)
        return {"success": True, "kopiert": kopiert}
    except Exception as e:
        return {"success": False, "error": str(e)}

@router.get("/api/budget/summary")
async def get_summary(jahr: int = Query(...), monat: int = Query(...)):
    budget_service.update_ist_werte_from_invoices(jahr, monat)
    return budget_service.get_dashboard_summary(jahr, monat)

@router.get("/api/budget/trend")
async def get_trend(kategorie_id: Optional[int] = Query(default=None), monate: int = Query(default=12)):
    return budget_service.get_trend_data(kategorie_id, monate)

@router.get("/api/budget/verteilung")
async def get_verteilung(jahr: int = Query(...), monat: int = Query(...)):
    return budget_service.get_kategorie_verteilung(jahr, monat)

@router.get("/api/budget/alerts")
async def get_alerts(nur_ungelesen: bool = Query(default=False), limit: int = Query(default=50)):
    return budget_service.get_alerts(nur_ungelesen, limit)

@router.post("/api/budget/alerts/{alert_id}/read")
async def mark_alert_read(alert_id: int):
    return {"success": budget_service.mark_alert_read(alert_id)}

@router.post("/api/budget/alerts/read-all")
async def mark_all_alerts_read():
    count = budget_service.mark_all_alerts_read()
    return {"success": True, "count": count}

@router.get("/api/budget/export")
async def export_budgets(jahr: int = Query(...), monat: int = Query(...)):
    try:
        import openpyxl
        from openpyxl.styles import Font, PatternFill, Border, Side
        
        auswertungen = budget_service.get_monatsauswertung(jahr, monat)
        summary = budget_service.get_dashboard_summary(jahr, monat)
        
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = f"Budget {MONAT_NAMEN[monat-1]} {jahr}"
        
        header_font = Font(bold=True, color="FFFFFF")
        header_fill = PatternFill(start_color="003856", end_color="003856", fill_type="solid")
        thin_border = Border(left=Side(style='thin'), right=Side(style='thin'), top=Side(style='thin'), bottom=Side(style='thin'))
        
        ws.merge_cells('A1:F1')
        ws['A1'] = f"Budget-Report: {MONAT_NAMEN[monat-1]} {jahr}"
        ws['A1'].font = Font(bold=True, size=16)
        
        ws['A3'], ws['B3'] = "Gesamt-Budget:", summary['gesamt_budget']
        ws['A4'], ws['B4'] = "Gesamt-Ausgaben:", summary['gesamt_ausgaben']
        ws['B3'].number_format = ws['B4'].number_format = '#,##0.00 €'
        
        headers = ['Kategorie', 'Budget', 'Ist', 'Differenz', 'Auslastung', 'Status']
        for col, header in enumerate(headers, 1):
            cell = ws.cell(row=6, column=col, value=header)
            cell.font, cell.fill, cell.border = header_font, header_fill, thin_border
        
        for row, kat in enumerate(auswertungen, 7):
            ws.cell(row=row, column=1, value=kat['kategorie_name']).border = thin_border
            ws.cell(row=row, column=2, value=kat['budget_soll']).border = thin_border
            ws.cell(row=row, column=3, value=kat['ist_ausgaben']).border = thin_border
            ws.cell(row=row, column=4, value=kat['differenz']).border = thin_border
            ws.cell(row=row, column=5, value=f"{kat['auslastung_prozent']}%").border = thin_border
            status = "OK" if kat['alert_severity'] == 'info' else "Achtung" if kat['alert_severity'] == 'warning' else "Überschritten"
            ws.cell(row=row, column=6, value=status).border = thin_border
        
        ws.column_dimensions['A'].width = 28
        for c in 'BCDEF': ws.column_dimensions[c].width = 15
        
        filepath = f"/tmp/budget_{jahr}_{monat:02d}.xlsx"
        wb.save(filepath)
        return FileResponse(filepath, filename=f"budget_{jahr}_{monat:02d}.xlsx", media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    except ImportError:
        raise HTTPException(status_code=500, detail="openpyxl nicht installiert")

@router.get("/api/budget/jahresbudget")
async def get_jahresbudget(jahr: int = Query(...)):
    return budget_service.get_jahresbudget(jahr)

@router.post("/api/budget/init-demo")
async def init_demo():
    from budget_service import create_demo_budgets
    create_demo_budgets()
    return {"success": True, "message": "Demo-Daten erstellt"}

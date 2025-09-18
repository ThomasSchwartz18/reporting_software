from __future__ import annotations
from fastapi import FastAPI, Depends, HTTPException
from fastapi.responses import JSONResponse
from .db import SessionLocal
from sqlalchemy.orm import Session
from . import schemas as s
from . import crud

app = FastAPI(title="Floor Reports API", version="0.1.0")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/health")
def health(db: Session = Depends(get_db)):
    db.execute("SELECT 1")
    return {"ok": True}

@app.get("/defect-codes", response_model=list[s.DefectCodeOut])
def get_defect_codes(db: Session = Depends(get_db)):
    return crud.list_defect_codes(db)

@app.post("/aoi-reports")
def post_aoi_report(payload: s.AOIReportCreate, db: Session = Depends(get_db)):
    try:
        report = crud.create_aoi_report(db, payload)
        return JSONResponse({"id": report.id, "ok": True})
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/kpi/summary", response_model=s.KPISummary)
def kpi_summary(db: Session = Depends(get_db)):
    return crud.kpi_summary(db)

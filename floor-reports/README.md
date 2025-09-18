# Floor Reports (MVP)
Capture floor data (starting with AOI) and auto-generate weekly summaries.

## Quick Start
1) Python 3.11+, Docker Desktop (optional), Git
2) Create .env: copy .env.example -> .env and pick DATABASE_URL
3) Install deps & initialize DB:
   bash scripts/bootstrap.sh
4) Run API:
   bash scripts/run.sh
5) Open http://127.0.0.1:8000/docs
6) Seed basics (lines, operations, a few defect codes):
   python scripts/seed_minimum.py
7) Generate a sample weekly report (HTML & PDF if WeasyPrint available):
   python reports/weekly.py

## Swap DBs later
- Change only `DATABASE_URL` in .env (SQLite ↔ Postgres)
- Run `alembic upgrade head` if schema changes exist

## Notes
- PDF generation uses WeasyPrint if installed; otherwise we emit HTML only.
- Add Auth/RBAC, SAP sync, and more operations later.

from __future__ import annotations
from datetime import datetime, timedelta
from jinja2 import Environment, FileSystemLoader, select_autoescape
from pathlib import Path
from app.db import SessionLocal
from app import models as m

# Data pull
with SessionLocal() as s:
    # naive sums for MVP
    total_jobs = s.query(m.Job).count()
    boards = s.query(m.AOIReport).all()
    total_boards = sum(x.boards_inspected for x in boards)
    total_ng = sum(x.boards_ng for x in boards)
    site_ppm = (total_ng / total_boards * 1_000_000) if total_boards else 0.0

    # top defects by count
    q = (
        s.query(m.AOIDefect, m.DefectCode)
        .join(m.DefectCode, m.AOIDefect.defect_code == m.DefectCode.code)
        .all()
    )
    agg = {}
    for d, dc in q:
        agg.setdefault(dc.code, {"name": dc.name, "count": 0})
        agg[dc.code]["count"] += d.count
    top_defects = [
        {"code": code, "name": meta["name"], "count": meta["count"]}
        for code, meta in sorted(agg.items(), key=lambda x: x[1]["count"], reverse=True)[:10]
    ]

kpi = {
    "total_jobs": total_jobs,
    "total_boards": total_boards,
    "total_ng": total_ng,
    "site_ppm": site_ppm,
}

# Render
env = Environment(loader=FileSystemLoader("reports/templates"), autoescape=select_autoescape())
tpl = env.get_template("weekly.html")
start_date = (datetime.utcnow() - timedelta(days=7)).date().isoformat()
end_date = datetime.utcnow().date().isoformat()
html = tpl.render(kpi=kpi, start_date=start_date, end_date=end_date, top_defects=top_defects)

out_dir = Path("reports/out"); out_dir.mkdir(parents=True, exist_ok=True)
html_path = out_dir / f"weekly_{end_date}.html"
html_path.write_text(html, encoding="utf-8")
print(f"Wrote {html_path}")

# Try PDF via WeasyPrint, if present
try:
    from weasyprint import HTML  # type: ignore
    pdf_path = out_dir / f"weekly_{end_date}.pdf"
    HTML(string=html).write_pdf(str(pdf_path))
    print(f"Wrote {pdf_path}")
except Exception as e:
    print("PDF step skipped:", e)

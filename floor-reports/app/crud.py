from __future__ import annotations
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload
from . import models as m
from . import schemas as s

# Simple upserts/helpers

def get_or_create_assembly(db: Session, number: str) -> m.Assembly:
    a = db.execute(select(m.Assembly).where(m.Assembly.number == number)).scalar_one_or_none()
    if a: return a
    a = m.Assembly(number=number)
    db.add(a); db.flush()
    return a

def get_or_create_revision(db: Session, assembly_id: str, rev_code: str | None) -> m.Revision | None:
    if not rev_code: return None
    r = db.execute(select(m.Revision).where(m.Revision.assembly_id==assembly_id, m.Revision.rev_code==rev_code)).scalar_one_or_none()
    if r: return r
    r = m.Revision(assembly_id=assembly_id, rev_code=rev_code)
    db.add(r); db.flush()
    return r

def get_or_create_job(db: Session, job_number: str, assembly_id: str, revision_id: str | None) -> m.Job:
    j = db.execute(select(m.Job).where(m.Job.job_number==job_number)).scalar_one_or_none()
    if j: return j
    j = m.Job(job_number=job_number, assembly_id=assembly_id, revision_id=revision_id)
    db.add(j); db.flush()
    return j

def get_or_create_by_name(db: Session, model, name: str):
    obj = db.execute(select(model).where(model.name==name)).scalar_one_or_none()
    if obj: return obj
    obj = model(name=name)
    db.add(obj); db.flush()
    return obj

def get_or_create_operator(db: Session, badge: str | None) -> m.Operator | None:
    if not badge: return None
    op = db.execute(select(m.Operator).where(m.Operator.badge==badge)).scalar_one_or_none()
    if op: return op
    op = m.Operator(badge=badge)
    db.add(op); db.flush()
    return op

# Core create

def create_aoi_report(db: Session, payload: s.AOIReportCreate) -> m.AOIReport:
    a = get_or_create_assembly(db, payload.assembly_number)
    r = get_or_create_revision(db, a.id, payload.revision_code)
    j = get_or_create_job(db, payload.job_number, a.id, r.id if r else None)
    opn = get_or_create_by_name(db, m.Operation, payload.operation_name)
    line = get_or_create_by_name(db, m.Line, payload.line_name)
    oper = get_or_create_operator(db, payload.operator_badge)

    report = m.AOIReport(
        job_id=j.id,
        operation_id=opn.id,
        line_id=line.id,
        operator_id=oper.id if oper else None,
        boards_inspected=payload.boards_inspected,
        boards_ng=payload.boards_ng,
        notes=payload.notes,
    )
    db.add(report); db.flush()

    # Link defects (must exist in dictionary)
    codes = {c.code for c in db.execute(select(m.DefectCode)).scalars()}
    for d in payload.defects:
        if d.defect_code not in codes:
            raise ValueError(f"Unknown defect_code: {d.defect_code}")
        db.add(m.AOIDefect(aoi_report_id=report.id, defect_code=d.defect_code, count=d.count))

    db.commit(); db.refresh(report)
    return report

# Simple queries

def list_operations(db: Session):
    stmt = select(m.Operation).order_by(m.Operation.name)
    return db.execute(stmt).scalars().all()


def list_lines(db: Session):
    stmt = select(m.Line).order_by(m.Line.name)
    return db.execute(stmt).scalars().all()


def list_defect_codes(db: Session):
    stmt = select(m.DefectCode).order_by(m.DefectCode.code)
    return db.execute(stmt).scalars().all()

def kpi_summary(db: Session) -> dict:
    # naive impl for MVP
    total_jobs = db.query(m.Job).count()
    boards = db.query(m.AOIReport).all()
    total_boards = sum(x.boards_inspected for x in boards)
    total_ng = sum(x.boards_ng for x in boards)
    site_ppm = (total_ng / total_boards * 1_000_000) if total_boards else 0.0
    return {"total_jobs": total_jobs, "total_boards": total_boards, "total_ng": total_ng, "site_ppm": site_ppm}


def get_aoi_report_details(db: Session, report_id: str):
    stmt = (
        select(m.AOIReport)
        .where(m.AOIReport.id == report_id)
        .options(
            joinedload(m.AOIReport.job).joinedload(m.Job.assembly),
            joinedload(m.AOIReport.job).joinedload(m.Job.revision),
            joinedload(m.AOIReport.operation),
            joinedload(m.AOIReport.line),
            joinedload(m.AOIReport.operator),
        )
    )
    report = db.execute(stmt).scalar_one_or_none()
    if not report:
        return None

    defects_stmt = (
        select(m.AOIDefect)
        .where(m.AOIDefect.aoi_report_id == report.id)
        .options(joinedload(m.AOIDefect.defect))
        .order_by(m.AOIDefect.id)
    )
    defects = db.execute(defects_stmt).scalars().all()
    return {"report": report, "defects": defects}

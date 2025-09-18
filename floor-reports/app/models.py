from __future__ import annotations
import uuid, datetime as dt
from sqlalchemy import (
    Column, String, Integer, DateTime, ForeignKey, Text, CheckConstraint, UniqueConstraint
)
from sqlalchemy.orm import relationship
from .db import Base


def uuid_str() -> str:
    return str(uuid.uuid4())

class DefectCode(Base):
    __tablename__ = "defect_codes"
    code = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    description = Column(Text)
    default_operation = Column(String, nullable=False)  # 'SMT AOI' | 'TH AOI' | 'Either'
    component_class = Column(String)
    category = Column(String)

class Assembly(Base):
    __tablename__ = "assemblies"
    id = Column(String(36), primary_key=True, default=uuid_str)
    number = Column(String, unique=True, nullable=False)
    description = Column(Text)
    created_at = Column(DateTime, default=dt.datetime.utcnow, nullable=False)

class Revision(Base):
    __tablename__ = "revisions"
    id = Column(String(36), primary_key=True, default=uuid_str)
    assembly_id = Column(String(36), ForeignKey("assemblies.id"), nullable=False)
    rev_code = Column(String, nullable=False)
    effective_from = Column(DateTime)
    effective_to = Column(DateTime)
    __table_args__ = (UniqueConstraint("assembly_id","rev_code", name="uq_assembly_rev"),)
    assembly = relationship("Assembly")

class Job(Base):
    __tablename__ = "jobs"
    id = Column(String(36), primary_key=True, default=uuid_str)
    job_number = Column(String, unique=True, nullable=False)
    assembly_id = Column(String(36), ForeignKey("assemblies.id"), nullable=False)
    revision_id = Column(String(36), ForeignKey("revisions.id"))
    planned_qty = Column(Integer)
    start_ts = Column(DateTime, default=dt.datetime.utcnow)
    end_ts = Column(DateTime)
    assembly = relationship("Assembly")
    revision = relationship("Revision")

class Operation(Base):
    __tablename__ = "operations"
    id = Column(String(36), primary_key=True, default=uuid_str)
    name = Column(String, unique=True, nullable=False)

class Line(Base):
    __tablename__ = "lines"
    id = Column(String(36), primary_key=True, default=uuid_str)
    name = Column(String, unique=True, nullable=False)

class Operator(Base):
    __tablename__ = "operators"
    id = Column(String(36), primary_key=True, default=uuid_str)
    badge = Column(String, unique=True, nullable=False)
    first_name = Column(String)
    last_name = Column(String)
    role = Column(String, default="Operator")  # Operator | Lead | QE | Admin

class AOIReport(Base):
    __tablename__ = "aoi_reports"
    id = Column(String(36), primary_key=True, default=uuid_str)
    job_id = Column(String(36), ForeignKey("jobs.id"), nullable=False)
    operation_id = Column(String(36), ForeignKey("operations.id"), nullable=False)
    line_id = Column(String(36), ForeignKey("lines.id"))
    operator_id = Column(String(36), ForeignKey("operators.id"))
    report_ts = Column(DateTime, default=dt.datetime.utcnow, nullable=False)
    boards_inspected = Column(Integer, nullable=False)
    boards_ng = Column(Integer, nullable=False)
    notes = Column(Text)
    __table_args__ = (
        CheckConstraint("boards_inspected >= 0", name="ck_inspected_nonneg"),
        CheckConstraint("boards_ng >= 0 AND boards_ng <= boards_inspected", name="ck_ng_bounds"),
    )
    job = relationship("Job")
    operation = relationship("Operation")
    line = relationship("Line")
    operator = relationship("Operator")

class AOIDefect(Base):
    __tablename__ = "aoi_defects"
    id = Column(String(36), primary_key=True, default=uuid_str)
    aoi_report_id = Column(String(36), ForeignKey("aoi_reports.id", ondelete="CASCADE"), nullable=False)
    defect_code = Column(String, ForeignKey("defect_codes.code"), nullable=False)
    count = Column(Integer, nullable=False)
    __table_args__ = (CheckConstraint("count >= 0", name="ck_count_nonneg"),)
    report = relationship("AOIReport")
    defect = relationship("DefectCode")

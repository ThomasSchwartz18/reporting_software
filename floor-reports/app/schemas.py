from __future__ import annotations
from pydantic import BaseModel, Field, field_validator
from typing import List, Optional

class AOIDefectItem(BaseModel):
    defect_code: str
    count: int = Field(ge=0)

class AOIReportCreate(BaseModel):
    # Accepts job/assembly identifiers so we can upsert basics
    job_number: str
    assembly_number: str
    revision_code: Optional[str] = None
    operation_name: str  # e.g., "SMT AOI" | "TH AOI"
    line_name: str
    operator_badge: Optional[str] = None
    boards_inspected: int = Field(ge=0)
    boards_ng: int = Field(ge=0)
    notes: Optional[str] = None
    defects: List[AOIDefectItem] = []

    @field_validator("boards_ng")
    @classmethod
    def ng_leq_inspected(cls, v, info):
        inspected = info.data.get("boards_inspected", None)
        if inspected is not None and v > inspected:
            raise ValueError("boards_ng cannot exceed boards_inspected")
        return v

class DefectCodeOut(BaseModel):
    code: str
    name: str
    description: str | None = None
    default_operation: str
    component_class: str | None = None
    category: str | None = None

class KPISummary(BaseModel):
    total_jobs: int
    total_boards: int
    total_ng: int
    site_ppm: float

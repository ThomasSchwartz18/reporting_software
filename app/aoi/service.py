"""Business logic helpers for the AOI inspection module."""
from __future__ import annotations

from collections.abc import Iterable
from datetime import date
from typing import Any

from flask import current_app

from ..extensions import db
from ..models import User
from .models import AoiBoardData, AoiForm, AoiProblemCode, AoiRejection

PROBLEM_CODES: tuple[tuple[int, str], ...] = (
    (1, "Missing Component"),
    (2, "Part In Wrong Location"),
    (3, "Wrong Component"),
    (4, "Damaged Component"),
    (5, "Parts Not Seated"),
    (6, "Insufficient Solder"),
    (7, "Solder Bridge"),
    (8, "No Solder"),
    (9, "Damaged Pads Or Circuitry"),
    (10, "Reversed Polarity"),
    (11, "Excessive Solder"),
    (12, "Solder Splash"),
    (13, "Solder Voids, Holes, Etc."),
    (14, "Solder Balls"),
    (15, "Part Tombstoned"),
    (16, "Part Skewed"),
    (17, "Part Flipped"),
    (18, "Part Billboard"),
    (19, "Part Leaning"),
    (20, "Solder In Solder Free Area"),
    (21, "Missing RTV/EPOXY/CONF COAT/DYMAX"),
    (22, "RTV/EPOXY/CONF COAT/DYMAX In Contact Area"),
    (23, "Missing Revision/ Dye Mark"),
    (24, "Blue Sheet Part"),
    (25, "Defective Component"),
)


def ensure_problem_codes() -> None:
    """Ensure the lookup table is seeded with the authoritative codes."""

    existing = {code for code, _ in db.session.query(AoiProblemCode.code).all()}
    missing = [code for code, _ in PROBLEM_CODES if code not in existing]

    if not missing and len(existing) == len(PROBLEM_CODES):
        return

    for code, name in PROBLEM_CODES:
        problem = AoiProblemCode.query.get(code)
        if problem is None:
            db.session.add(AoiProblemCode(code=code, name=name))
        elif problem.name != name:
            current_app.logger.warning(
                "AOI problem code name mismatch for %s: %s -> %s", code, problem.name, name
            )
            problem.name = name

    db.session.commit()


def compute_qty_accepted(qty_inspected: int, qty_rejected: int) -> int:
    """Return the computed accepted quantity ensuring it is never negative."""

    accepted = qty_inspected - qty_rejected
    return max(accepted, 0)


def find_problem_name(code: int) -> str | None:
    """Return the human-readable name for ``code`` or ``None``."""

    mapping = dict(PROBLEM_CODES)
    return mapping.get(code)


def get_problem_codes() -> list[dict[str, int | str]]:
    """Return a serialisable list of problem codes for the UI."""

    codes = AoiProblemCode.query.order_by(AoiProblemCode.code.asc()).all()
    if not codes:
        ensure_problem_codes()
        codes = AoiProblemCode.query.order_by(AoiProblemCode.code.asc()).all()
    return [code.to_dict() for code in codes]


def get_known_inspectors() -> list[str]:
    """Return usernames that can be used as inspector selections."""

    inspectors = [user.username for user in User.query.order_by(User.username.asc())]
    return inspectors


class ValidationError(Exception):
    """Raised when incoming payload fails validation."""

    def __init__(self, errors: dict[str, Any]):
        super().__init__("AOI form validation failed")
        self.errors = errors


def _parse_int(value: Any, field: str, min_value: int | None = None) -> int:
    if value in (None, ""):
        return 0
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:  # pragma: no cover - protective branch
        raise ValidationError({field: "Must be an integer"}) from exc
    if min_value is not None and parsed < min_value:
        raise ValidationError({field: f"Must be >= {min_value}"})
    return parsed


def _parse_date(value: Any, field: str) -> date:
    if isinstance(value, date):
        return value
    if not value:
        raise ValidationError({field: "Date is required"})
    try:
        return date.fromisoformat(str(value))
    except ValueError as exc:  # pragma: no cover - protective branch
        raise ValidationError({field: "Invalid date"}) from exc


def normalise_payload(data: dict[str, Any]) -> dict[str, Any]:
    """Validate and normalise the AOI payload for persistence."""

    errors: dict[str, Any] = {}

    header = data.get("header", {})
    job = data.get("job", {})
    lot = data.get("lot_result", {})

    status_value = data.get("status", "submitted")
    if status_value not in {"draft", "submitted"}:
        errors["status"] = "Status must be 'draft' or 'submitted'"

    record: dict[str, Any] = {
        "date": None,
        "type": None,
        "form_number": data.get("form_meta", {}).get("form_number", "Form-114"),
        "form_rev": data.get("form_meta", {}).get("form_rev", "Rev. 17 (9/9/2025)"),
        "customer": job.get("customer"),
        "assembly": job.get("assembly"),
        "job_number": job.get("job_number"),
        "revision": job.get("revision"),
        "panels_count": None,
        "boards_count": None,
        "inspector": job.get("inspector"),
        "qty_inspected": 0,
        "qty_rejected": 0,
        "qty_accepted": 0,
        "comments": data.get("comments"),
        "status": status_value,
    }

    try:
        record["date"] = _parse_date(header.get("date"), "date")
    except ValidationError as err:
        errors.update(err.errors)

    type_value = header.get("type")
    if type_value not in {"SMT", "TH"}:
        errors["type"] = "Type must be either 'SMT' or 'TH'"
    else:
        record["type"] = type_value

    try:
        record["panels_count"] = _parse_int(job.get("panels_count"), "panels_count", 0)
        record["boards_count"] = _parse_int(job.get("boards_count"), "boards_count", 0)
        record["qty_inspected"] = _parse_int(lot.get("qty_inspected"), "qty_inspected", 0)
        record["qty_rejected"] = _parse_int(lot.get("qty_rejected"), "qty_rejected", 0)
    except ValidationError as err:
        errors.update(err.errors)

    if record["qty_rejected"] > record["qty_inspected"]:
        errors["qty_rejected"] = "Rejected cannot exceed inspected"

    record["qty_accepted"] = compute_qty_accepted(
        record["qty_inspected"], record["qty_rejected"]
    )

    rejections_input = data.get("rejections", [])
    rejections: list[dict[str, Any]] = []
    rejection_errors: list[dict[str, Any]] = []

    for index, item in enumerate(rejections_input):
        row_errors: dict[str, Any] = {}
        quantity = item.get("quantity")
        problem_code = item.get("problem_code")

        try:
            quantity_value = _parse_int(quantity, f"rejections[{index}].quantity", 1)
        except ValidationError as err:
            row_errors.update(err.errors)
            quantity_value = None

        if problem_code is None:
            row_errors["problem_code"] = "Problem code is required"
        else:
            try:
                problem_code = int(problem_code)
            except (TypeError, ValueError):
                row_errors["problem_code"] = "Problem code must be a number"
            else:
                if find_problem_name(problem_code) is None:
                    row_errors["problem_code"] = "Unknown problem code"

        if row_errors:
            rejection_errors.append(row_errors)
            continue

        rejections.append(
            {
                "quantity": quantity_value,
                "problem_code": problem_code,
                "reference_designators": (item.get("reference_designators") or "").strip(),
            }
        )

    board_data_input = data.get("board_data", [])
    board_rows: list[dict[str, Any]] = []
    for item in board_data_input:
        if not any(item.values()):
            continue
        board_rows.append(
            {
                "board_id": (item.get("board_id") or "").strip() or None,
                "reference_designators": (item.get("reference_designators") or "").strip()
                or None,
                "problem_code": int(item["problem_code"]) if item.get("problem_code") else None,
                "comments": (item.get("comments") or "").strip() or None,
            }
        )

    if rejection_errors:
        errors["rejections"] = rejection_errors

    if errors:
        raise ValidationError(errors)

    record["rejections"] = rejections
    record["board_data"] = board_rows
    return record


def create_form(payload: dict[str, Any]) -> AoiForm:
    """Persist a new AOI form using ``payload`` data."""

    record = normalise_payload(payload)

    form = AoiForm(
        date=record["date"],
        type=record["type"],
        form_number=record["form_number"],
        form_rev=record["form_rev"],
        customer=record.get("customer"),
        assembly=record.get("assembly"),
        job_number=record.get("job_number"),
        revision=record.get("revision"),
        panels_count=record.get("panels_count"),
        boards_count=record.get("boards_count"),
        inspector=record.get("inspector"),
        qty_inspected=record["qty_inspected"],
        qty_rejected=record["qty_rejected"],
        qty_accepted=record["qty_accepted"],
        comments=record.get("comments"),
        status=record.get("status", "submitted"),
    )

    for rejection in record["rejections"]:
        form.rejections.append(
            AoiRejection(
                quantity=rejection["quantity"],
                problem_code=rejection["problem_code"],
                reference_designators=rejection.get("reference_designators"),
            )
        )

    for board_row in record["board_data"]:
        form.board_data.append(
            AoiBoardData(
                board_id=board_row.get("board_id"),
                reference_designators=board_row.get("reference_designators"),
                problem_code=board_row.get("problem_code"),
                comments=board_row.get("comments"),
            )
        )

    db.session.add(form)
    db.session.commit()

    return form


def serialize_form(form: AoiForm) -> dict[str, Any]:
    """Return a JSON-serialisable representation of ``form``."""

    return {
        "id": str(form.id),
        "form_number": form.form_number,
        "form_rev": form.form_rev,
        "date": form.date.isoformat(),
        "type": form.type,
        "customer": form.customer,
        "assembly": form.assembly,
        "job_number": form.job_number,
        "revision": form.revision,
        "panels_count": form.panels_count,
        "boards_count": form.boards_count,
        "inspector": form.inspector,
        "qty_inspected": form.qty_inspected,
        "qty_rejected": form.qty_rejected,
        "qty_accepted": form.qty_accepted,
        "comments": form.comments,
        "status": form.status,
        "created_at": form.created_at.isoformat() if form.created_at else None,
        "updated_at": form.updated_at.isoformat() if form.updated_at else None,
        "rejections": [
            {
                "id": str(rejection.id),
                "quantity": rejection.quantity,
                "problem_code": rejection.problem_code,
                "problem_name": rejection.problem.name,
                "reference_designators": rejection.reference_designators,
            }
            for rejection in form.rejections
        ],
        "board_data": [
            {
                "id": str(board.id),
                "board_id": board.board_id,
                "reference_designators": board.reference_designators,
                "problem_code": board.problem_code,
                "problem_name": board.problem.name if board.problem else None,
                "comments": board.comments,
            }
            for board in form.board_data
        ],
    }


def serialize_forms(forms: Iterable[AoiForm]) -> list[dict[str, Any]]:
    """Return a list of serialised form payloads."""

    return [serialize_form(form) for form in forms]

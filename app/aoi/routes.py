"""Route handlers for AOI inspection forms."""
from __future__ import annotations

from datetime import date

from flask import Response, jsonify, render_template, request, url_for

from ..extensions import db
from . import aoi_bp
from .models import AoiForm
from .service import (
    ValidationError,
    compute_qty_accepted,
    create_form,
    ensure_problem_codes,
    get_known_inspectors,
    get_problem_codes,
    serialize_form,
)


@aoi_bp.before_app_request
def ensure_lookup_seeded() -> None:
    """Seed lookup values on first request."""

    ensure_problem_codes()


@aoi_bp.get("/new")
def new_form() -> str:
    """Render a new AOI inspection form."""

    inspectors = get_known_inspectors()
    codes = get_problem_codes()
    return render_template(
        "aoi/form.html",
        today=date.today(),
        inspectors=inspectors,
        problem_codes=codes,
    )


@aoi_bp.post("")
def submit_form() -> Response:
    """Create a new AOI form from JSON payload."""

    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return jsonify({"error": "Invalid payload"}), 400

    try:
        form = create_form(payload)
    except ValidationError as exc:
        db.session.rollback()
        return jsonify({"error": exc.errors}), 422

    action = payload.get("status", "submitted")
    message = "Draft saved" if action == "draft" else "Form submitted"

    return (
        jsonify(
            {
                "message": message,
                "form": serialize_form(form),
                "redirect": url_for("aoi.view_form", form_id=form.id),
            }
        ),
        201,
    )


@aoi_bp.get("/<form_id>")
def view_form(form_id: str) -> str:
    """Display a saved AOI form."""

    form = AoiForm.query.get_or_404(form_id)
    return render_template(
        "aoi/view.html",
        form=form,
        problem_codes=get_problem_codes(),
        compute_qty_accepted=compute_qty_accepted,
    )


@aoi_bp.get("/<form_id>/print")
def print_form(form_id: str) -> Response:
    """Render a print/PDF friendly layout."""

    form = AoiForm.query.get_or_404(form_id)
    format_hint = request.args.get("format")

    html = render_template(
        "aoi/print.html",
        form=form,
        problem_codes=get_problem_codes(),
    )

    if format_hint == "pdf":
        try:
            from weasyprint import HTML  # type: ignore
        except Exception as exc:  # pragma: no cover - dependency optional
            return (
                jsonify(
                    {
                        "error": "PDF generation requires WeasyPrint", 
                        "details": str(exc),
                    }
                ),
                501,
            )

        pdf = HTML(string=html).write_pdf()
        response = Response(pdf, mimetype="application/pdf")
        response.headers["Content-Disposition"] = (
            f"inline; filename=aoi-form-{form.id}.pdf"
        )
        return response

    return Response(html, mimetype="text/html")


@aoi_bp.get("/codes")
def problem_code_lookup() -> Response:
    """Provide the authoritative list of problem codes."""

    return jsonify({"problem_codes": get_problem_codes()})

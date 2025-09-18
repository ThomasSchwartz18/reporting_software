from __future__ import annotations

import os
from itertools import zip_longest
from typing import Any, Dict, List

from flask import Flask, flash, g, redirect, render_template, request, url_for
from werkzeug.datastructures import ImmutableMultiDict

from app import crud
from app.db import SessionLocal
from app import schemas as s


def create_app() -> Flask:
    """Application factory for the Flask UI."""
    app = Flask(
        __name__,
        template_folder=os.path.join(os.path.dirname(__file__), "templates"),
        static_folder=os.path.join(os.path.dirname(__file__), "static"),
    )
    app.config["SECRET_KEY"] = os.getenv("FLASK_SECRET_KEY", "dev-secret")

    @app.before_request
    def _open_session() -> None:
        if "db" not in g:
            g.db = SessionLocal()

    @app.teardown_appcontext
    def _close_session(exc: BaseException | None) -> None:  # type: ignore[override]
        db = g.pop("db", None)
        if not db:
            return
        if exc:
            db.rollback()
        db.close()

    def _load_form_options() -> Dict[str, Any]:
        db = g.db
        return {
            "operations": crud.list_operations(db),
            "lines": crud.list_lines(db),
            "defect_codes": crud.list_defect_codes(db),
        }

    def _build_defect_rows(form: ImmutableMultiDict[str, str]) -> List[Dict[str, str]]:
        codes = form.getlist("defect_code")
        counts = form.getlist("defect_count")
        rows = [
            {"code": code or "", "count": count or ""}
            for code, count in zip_longest(codes, counts, fillvalue="")
        ]
        if not rows:
            rows.append({"code": "", "count": ""})
        return rows

    @app.get("/")
    def dashboard() -> str:
        summary = crud.kpi_summary(g.db)
        return render_template("index.html", summary=summary)

    @app.get("/defect-codes")
    def defect_codes() -> str:
        codes = crud.list_defect_codes(g.db)
        return render_template("defect_codes.html", defect_codes=codes)

    def _parse_defects(form: ImmutableMultiDict[str, str]) -> List[s.AOIDefectItem]:
        defects: List[s.AOIDefectItem] = []
        codes = form.getlist("defect_code")
        counts = form.getlist("defect_count")
        for code, count in zip(codes, counts):
            if not code and not count:
                continue
            if not code or not count:
                raise ValueError("Each defect row must include a code and a count.")
            try:
                count_value = int(count)
            except ValueError as exc:  # pragma: no cover - defensive
                raise ValueError("Defect counts must be whole numbers.") from exc
            defects.append(s.AOIDefectItem(defect_code=code, count=count_value))
        return defects

    def _handle_form_error(error_message: str, context: Dict[str, Any]) -> str:
        flash(error_message, "danger")
        return render_template("new_report.html", **context)

    @app.route("/aoi-reports/new", methods=["GET", "POST"])
    def new_aoi_report() -> str:
        context: Dict[str, Any] = {
            "form_data": request.form or {},
            "defect_rows": _build_defect_rows(request.form),
            **_load_form_options(),
        }

        if request.method == "POST":
            form = request.form
            try:
                defects = _parse_defects(form)
                job_number = form.get("job_number", "").strip()
                assembly_number = form.get("assembly_number", "").strip()
                operation_name = form.get("operation_name", "").strip()
                line_name = form.get("line_name", "").strip()
                boards_inspected_raw = form.get("boards_inspected", "").strip()
                boards_ng_raw = form.get("boards_ng", "").strip()

                if not job_number or not assembly_number:
                    raise ValueError("Job and assembly numbers are required.")
                if not operation_name or not line_name:
                    raise ValueError("Operation and line selections are required.")
                if not boards_inspected_raw or not boards_ng_raw:
                    raise ValueError("Board counts are required.")

                payload = s.AOIReportCreate(
                    job_number=job_number,
                    assembly_number=assembly_number,
                    revision_code=form.get("revision_code") or None,
                    operation_name=operation_name,
                    line_name=line_name,
                    operator_badge=form.get("operator_badge") or None,
                    boards_inspected=int(boards_inspected_raw),
                    boards_ng=int(boards_ng_raw),
                    notes=form.get("notes") or None,
                    defects=defects,
                )
            except ValueError as exc:
                return _handle_form_error(str(exc), context)

            try:
                report = crud.create_aoi_report(g.db, payload)
            except ValueError as exc:
                return _handle_form_error(str(exc), context)

            flash("AOI report created successfully.", "success")
            return redirect(url_for("report_confirmation", report_id=report.id))

        return render_template("new_report.html", **context)

    @app.get("/aoi-reports/<report_id>/created")
    def report_confirmation(report_id: str) -> str:
        details = crud.get_aoi_report_details(g.db, report_id)
        if not details:
            flash("Unable to locate the requested report.", "warning")
            return redirect(url_for("new_aoi_report"))
        return render_template("report_confirmation.html", **details)

    return app


__all__ = ["create_app"]

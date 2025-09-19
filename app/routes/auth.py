"""Authentication and administration routes."""
from __future__ import annotations

import json

from collections.abc import Iterable
from datetime import date
from typing import Any
from uuid import uuid4

from flask import (
    Blueprint,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from sqlalchemy import func

from ..extensions import db
from ..models import ApplicationSetting, EmployeeSubmission, Role, SessionEvent, User


auth_bp = Blueprint("auth", __name__)


def ensure_session_token() -> str:
    """Guarantee a stable identifier for the current browser session."""

    token = session.get("session_token")
    if not token:
        token = uuid4().hex
        session["session_token"] = token
    return token


def set_progress_banner(details: str, primary: str | None = None) -> None:
    """Persist the banner messaging that appears above application pages."""

    session["progress_primary"] = primary or "Session update"
    session["progress_details"] = details


def derive_banner(
    event_type: str,
    details: dict[str, Any] | None,
    context_value: str | None,
    user: User | None,
) -> tuple[str, str] | None:
    """Translate an interaction into the banner language shown to the user."""

    username = (user.username if user else session.get("username")) or "User"
    payload = details or {}

    if event_type == "login":
        return (
            "Authentication complete",
            f"{username} is signed in. Double-check that you're using the intended account before continuing.",
        )

    if event_type == "area_selected":
        area = payload.get("area") or context_value or "an area"
        return (
            "Area confirmation",
            f"{username} selected {area}. Confirm this is where you need to work before moving forward.",
        )

    if event_type == "report_selected":
        report_label = payload.get("report") or context_value or "a report"
        return (
            "Report confirmation",
            f"{username} chose {report_label}. Make sure this is the report you expect before proceeding.",
        )

    if event_type == "return_to_area_selection":
        area = payload.get("area") or context_value
        if area:
            message = (
                f"{username} returned after reviewing {area}. Use this step to reassess your selection before continuing."
            )
        else:
            message = (
                f"{username} moved back a step. Review the available areas carefully before continuing."
            )
        return ("Navigation update", message)

    if event_type == "view_report":
        report_label = payload.get("report") or context_value or "the selected report"
        return (
            "Report in progress",
            f"{username} is viewing {report_label}. Validate that the displayed information matches your intent.",
        )

    return None


def record_session_event(
    event_type: str,
    *,
    details: dict[str, Any] | None = None,
    context_value: str | None = None,
    user: User | None = None,
) -> SessionEvent:
    """Persist an interaction for later administrative analysis."""

    token = ensure_session_token()
    actor = user or get_current_user()
    username = (actor.username if actor else session.get("username")) or None

    try:
        details_payload = json.dumps(details or {})
    except (TypeError, ValueError):
        details_payload = json.dumps({"raw": str(details)})

    event = SessionEvent(
        session_id=token,
        user_id=actor.id if actor else None,
        username=username,
        event_type=event_type,
        context_value=context_value,
        event_details=details_payload,
        path=request.path,
    )

    db.session.add(event)
    db.session.commit()
    return event


def load_event_details(event: SessionEvent) -> dict[str, Any]:
    """Return the stored event payload as a dictionary."""

    try:
        return json.loads(event.event_details or "{}")
    except (TypeError, ValueError):
        return {"raw": event.event_details or ""}


def get_current_user() -> User | None:
    """Return the currently authenticated user, if any."""

    user_id = session.get("user_id")
    if user_id is None:
        return None
    return db.session.get(User, user_id)


def ensure_logged_in() -> User | None:
    """Helper used by routes to guard access gracefully."""

    user = get_current_user()
    if user is None:
        flash("Please log in to continue.", "error")
    return user


def role_allowed(user_role: str, allowed_roles: Iterable[Role]) -> bool:
    """Return whether the provided role string matches the allowed list."""

    try:
        role_enum = Role(user_role)
    except ValueError:
        return False
    return role_enum in set(allowed_roles)


@auth_bp.route("/", methods=["GET", "POST"])
@auth_bp.route("/login", methods=["GET", "POST"])
def login() -> Any:
    """Render the login form and handle submissions."""

    users = User.query.order_by(User.username).all()

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            session["user_id"] = user.id
            session["username"] = user.username
            session["role"] = user.role
            ensure_session_token()
            record_session_event("login", details={"method": "password"}, user=user)
            banner = derive_banner("login", {"method": "password"}, None, user)
            if banner is not None:
                primary, text = banner
                set_progress_banner(text, primary)
            flash("Logged in successfully.", "success")
            return redirect(url_for("auth.dashboard"))

        flash("Invalid username or password.", "error")

    return render_template("auth/login.html", users=users)


@auth_bp.route("/dashboard")
def dashboard() -> Any:
    """Display the dashboard tailored to the signed-in user."""

    user = ensure_logged_in()
    if user is None:
        return redirect(url_for("auth.login"))

    is_admin = user.role_enum is Role.ADMIN
    is_staff = user.role_enum is Role.STAFF
    analysis_access = role_allowed(user.role, {Role.ADMIN, Role.MANAGER})

    record_session_event(
        "view_dashboard",
        details={"role": user.role},
        context_value=user.role,
        user=user,
    )

    return render_template(
        "auth/dashboard.html",
        user=user,
        is_admin=is_admin,
        is_staff=is_staff,
        analysis_access=analysis_access,
    )


@auth_bp.route("/reports/aoi/smt")
def report_aoi_smt() -> Any:
    """Render the SMT AOI report selection."""

    user = ensure_logged_in()
    if user is None:
        return redirect(url_for("auth.login"))

    details = {"report": "SMT Data Inspection Sheet", "area": "AOI"}
    record_session_event(
        "view_report",
        details=details,
        context_value="SMT Data Inspection Sheet",
        user=user,
    )
    banner = derive_banner("view_report", details, "SMT Data Inspection Sheet", user)
    if banner is not None:
        primary, text = banner
        set_progress_banner(text, primary)

    return render_template(
        "auth/report_inspection_sheet.html",
        user=user,
        page_title="SMT Data Inspection Sheet",
        report_type="SMT",
        report_date=date.today(),
        defect_rows=range(1, 11),
        rejection_rows=range(1, 11),
    )


@auth_bp.route("/reports/aoi/th")
def report_aoi_th() -> Any:
    """Render the TH AOI report selection."""

    user = ensure_logged_in()
    if user is None:
        return redirect(url_for("auth.login"))

    details = {"report": "TH Data Inspection Sheet", "area": "AOI"}
    record_session_event(
        "view_report",
        details=details,
        context_value="TH Data Inspection Sheet",
        user=user,
    )
    banner = derive_banner("view_report", details, "TH Data Inspection Sheet", user)
    if banner is not None:
        primary, text = banner
        set_progress_banner(text, primary)

    return render_template(
        "auth/report_inspection_sheet.html",
        user=user,
        page_title="TH Data Inspection Sheet",
        report_type="TH",
        report_date=date.today(),
        defect_rows=range(1, 11),
        rejection_rows=range(1, 11),
    )


@auth_bp.route("/session/event", methods=["POST"])
def session_event() -> Any:
    """Capture in-app interactions triggered via asynchronous requests."""

    user = ensure_logged_in()
    if user is None:
        return jsonify({"error": "Authentication required"}), 401

    payload = request.get_json(silent=True) or {}
    event_type = str(payload.get("event_type", "")).strip()
    if not event_type:
        return jsonify({"error": "An event_type value is required."}), 400

    details = payload.get("details")
    if not isinstance(details, dict):
        details = {}

    context_value = payload.get("context")
    if context_value is None:
        context_value = details.get("area") or details.get("report")

    record_session_event(
        event_type,
        details=details,
        context_value=context_value,
        user=user,
    )

    banner = derive_banner(event_type, details, context_value, user)
    response: dict[str, Any] = {"status": "ok"}
    if banner is not None:
        primary, text = banner
        set_progress_banner(text, primary)
        response["banner"] = {"primary": primary, "details": text}

    return jsonify(response), 200


@auth_bp.route("/logout")
def logout() -> Any:
    """Log the user out and redirect to the login page."""

    user = get_current_user()
    if user is not None:
        record_session_event("logout", user=user)
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for("auth.login"))


@auth_bp.route("/settings", methods=["GET", "POST"])
def settings() -> Any:
    """Administrative configuration dashboard for application owners."""

    user = ensure_logged_in()
    if user is None:
        return redirect(url_for("auth.login"))

    if user.role_enum is not Role.ADMIN:
        flash("Administrator access is required to view settings.", "error")
        return redirect(url_for("auth.dashboard"))

    record_session_event("view_settings", user=user)

    settings_defaults = {
        "application_name": "Reporting Software",
        "tagline": "Executive Insights Platform",
        "data_source": "sqlite:///instance/app.db",
        "warehouse_connection": "Not configured",
        "refresh_interval": "Hourly",
        "analysis_focus": "Quality & Throughput",
    }

    if request.method == "POST":
        action = request.form.get("action", "").strip()

        if action == "update_general":
            application_name = request.form.get("application_name", "").strip()
            tagline = request.form.get("tagline", "").strip()
            ApplicationSetting.set_value(
                "application_name", application_name or settings_defaults["application_name"]
            )
            ApplicationSetting.set_value(
                "tagline", tagline or settings_defaults["tagline"]
            )
            db.session.commit()
            flash("General configuration updated.", "success")

        elif action == "update_database":
            data_source = request.form.get("data_source", "").strip()
            warehouse_connection = request.form.get("warehouse_connection", "").strip()
            refresh_interval = request.form.get("refresh_interval", "").strip() or settings_defaults[
                "refresh_interval"
            ]

            ApplicationSetting.set_value(
                "data_source", data_source or settings_defaults["data_source"]
            )
            ApplicationSetting.set_value(
                "warehouse_connection",
                warehouse_connection or settings_defaults["warehouse_connection"],
            )
            ApplicationSetting.set_value("refresh_interval", refresh_interval)
            db.session.commit()
            flash("Database connectivity preferences saved.", "success")

        elif action == "update_analysis":
            analysis_focus = request.form.get("analysis_focus", "").strip() or settings_defaults[
                "analysis_focus"
            ]
            ApplicationSetting.set_value("analysis_focus", analysis_focus)
            db.session.commit()
            flash("Analysis mode preferences updated.", "success")

        elif action == "add_user":
            username = request.form.get("new_username", "").strip()
            password = request.form.get("new_password", "")
            role_value = request.form.get("new_role", Role.STAFF.value)

            if not username or not password:
                flash("A username and password are required to create a user.", "error")
            else:
                try:
                    role = Role(role_value)
                except ValueError:
                    flash("Invalid role selected.", "error")
                else:
                    existing = User.query.filter_by(username=username).first()
                    if existing is not None:
                        flash("A user with that username already exists.", "error")
                    else:
                        new_user = User(username=username, role=role.value)
                        new_user.set_password(password)
                        db.session.add(new_user)
                        db.session.commit()
                        flash(f"User '{username}' created successfully.", "success")

        elif action == "update_user_role":
            target_id = request.form.get("user_id")
            role_value = request.form.get("role", Role.STAFF.value)

            try:
                role = Role(role_value)
            except ValueError:
                flash("Invalid role selected.", "error")
            else:
                if target_id is None:
                    flash("Unable to identify the user to update.", "error")
                else:
                    try:
                        target_pk = int(target_id)
                    except (TypeError, ValueError):
                        flash("Unable to identify the user to update.", "error")
                    else:
                        target_user = db.session.get(User, target_pk)
                        if target_user is None:
                            flash("The selected user could not be found.", "error")
                        else:
                            if (
                                target_user.role == Role.ADMIN.value
                                and role is not Role.ADMIN
                                and User.query.filter_by(role=Role.ADMIN.value).count() <= 1
                            ):
                                flash(
                                    "At least one administrator must remain in the system.",
                                    "error",
                                )
                            else:
                                target_user.role = role.value
                                db.session.commit()
                                flash("User access level updated.", "success")

        elif action == "delete_user":
            target_id = request.form.get("user_id")
            if target_id is None:
                flash("Unable to identify the user to remove.", "error")
            else:
                try:
                    target_pk = int(target_id)
                except (TypeError, ValueError):
                    flash("Unable to identify the user to remove.", "error")
                else:
                    target_user = db.session.get(User, target_pk)
                    if target_user is None:
                        flash("The selected user could not be found.", "error")
                    elif target_user.id == user.id:
                        flash("You cannot remove your own account while signed in.", "error")
                    elif (
                        target_user.role == Role.ADMIN.value
                        and User.query.filter_by(role=Role.ADMIN.value).count() <= 1
                    ):
                        flash("At least one administrator must remain in the system.", "error")
                    else:
                        db.session.delete(target_user)
                        db.session.commit()
                        flash(f"User '{target_user.username}' removed.", "success")

        else:
            flash("The requested action is not recognised.", "error")

    settings_values = {
        key: ApplicationSetting.get_value(key, default)
        for key, default in settings_defaults.items()
    }

    users = User.query.order_by(User.username).all()
    role_labels = {role.value: role.label for role in Role}
    admin_users = [u for u in users if u.role == Role.ADMIN.value]

    return render_template(
        "auth/settings.html",
        user=user,
        settings_values=settings_values,
        users=users,
        role_labels=role_labels,
        roles=list(Role),
        admin_users=admin_users,
    )


@auth_bp.route("/analysis")
def analysis() -> Any:
    """Advanced analytics view for leadership roles."""

    user = ensure_logged_in()
    if user is None:
        return redirect(url_for("auth.login"))

    if user.role_enum not in {Role.ADMIN, Role.MANAGER}:
        flash("Analysis mode is available to managers and administrators only.", "error")
        return redirect(url_for("auth.dashboard"))

    record_session_event("view_analysis", user=user)

    total_entries = EmployeeSubmission.query.count()
    average_score = db.session.query(func.avg(EmployeeSubmission.performance_score)).scalar() or 0
    latest_submission = db.session.query(func.max(EmployeeSubmission.submitted_at)).scalar()

    department_breakdown = (
        db.session.query(
            EmployeeSubmission.department,
            func.count(EmployeeSubmission.id).label("total"),
            func.avg(EmployeeSubmission.performance_score).label("avg_score"),
        )
        .group_by(EmployeeSubmission.department)
        .order_by(func.count(EmployeeSubmission.id).desc())
        .all()
    )

    top_performers = (
        db.session.query(
            EmployeeSubmission.employee_name,
            func.avg(EmployeeSubmission.performance_score).label("avg_score"),
            func.sum(EmployeeSubmission.value).label("total_value"),
            func.count(EmployeeSubmission.id).label("entries"),
        )
        .group_by(EmployeeSubmission.employee_name)
        .order_by(func.avg(EmployeeSubmission.performance_score).desc())
        .limit(5)
        .all()
    )

    recent_entries = (
        EmployeeSubmission.query.order_by(EmployeeSubmission.submitted_at.desc()).limit(6).all()
    )

    settings_snapshot = {
        "analysis_focus": ApplicationSetting.get_value("analysis_focus", "Quality & Throughput"),
        "data_source": ApplicationSetting.get_value("data_source", "sqlite:///instance/app.db"),
        "refresh_interval": ApplicationSetting.get_value("refresh_interval", "Hourly"),
    }

    return render_template(
        "auth/analysis.html",
        user=user,
        total_entries=total_entries,
        average_score=average_score,
        latest_submission=latest_submission,
        department_breakdown=department_breakdown,
        top_performers=top_performers,
        recent_entries=recent_entries,
        settings_snapshot=settings_snapshot,
        role_labels={role.value: role.label for role in Role},
        Role=Role,
    )


@auth_bp.route("/admin/session-log")
def session_log() -> Any:
    """Administrative view summarising recorded interaction data."""

    user = ensure_logged_in()
    if user is None:
        return redirect(url_for("auth.login"))

    if user.role_enum is not Role.ADMIN:
        flash("The session log is restricted to administrators.", "error")
        return redirect(url_for("auth.dashboard"))

    record_session_event("view_session_log", user=user)

    area_usage = (
        db.session.query(
            SessionEvent.context_value,
            func.count(SessionEvent.id).label("total"),
        )
        .filter(
            SessionEvent.event_type == "area_selected",
            SessionEvent.context_value.isnot(None),
        )
        .group_by(SessionEvent.context_value)
        .order_by(func.count(SessionEvent.id).desc())
        .all()
    )

    backtrack_usage = (
        db.session.query(
            SessionEvent.context_value,
            func.count(SessionEvent.id).label("total"),
        )
        .filter(SessionEvent.event_type == "return_to_area_selection")
        .group_by(SessionEvent.context_value)
        .order_by(func.count(SessionEvent.id).desc())
        .all()
    )

    report_preferences = (
        db.session.query(
            SessionEvent.context_value,
            func.count(SessionEvent.id).label("total"),
        )
        .filter(SessionEvent.event_type == "report_selected")
        .group_by(SessionEvent.context_value)
        .order_by(func.count(SessionEvent.id).desc())
        .all()
    )

    report_by_area: dict[str, int] = {}
    for event in SessionEvent.query.filter_by(event_type="report_selected"):
        details = load_event_details(event)
        area = str(details.get("area") or "").strip()
        if not area:
            continue
        report_by_area[area] = report_by_area.get(area, 0) + 1

    distinct_sessions = db.session.query(SessionEvent.session_id).distinct().count()
    total_events = SessionEvent.query.count()

    recent_events = [
        {
            "timestamp": event.created_at,
            "session_id": event.session_id,
            "username": event.username or "Unknown",
            "event_type": event.event_type,
            "context": event.context_value,
            "details": load_event_details(event),
            "path": event.path,
        }
        for event in SessionEvent.query.order_by(SessionEvent.created_at.desc()).limit(200)
    ]

    return render_template(
        "auth/session_log.html",
        user=user,
        area_usage=area_usage,
        backtrack_usage=backtrack_usage,
        report_preferences=report_preferences,
        report_by_area=report_by_area,
        recent_events=recent_events,
        distinct_sessions=distinct_sessions,
        total_events=total_events,
    )

"""Authentication and administration routes."""
from __future__ import annotations

from collections.abc import Iterable
from datetime import date
from typing import Any

from flask import (
    Blueprint,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from sqlalchemy import func

from ..extensions import db
from ..models import ApplicationSetting, EmployeeSubmission, Role, User


auth_bp = Blueprint("auth", __name__)


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

    return render_template(
        "auth/report_inspection_sheet.html",
        user=user,
        page_title="TH Data Inspection Sheet",
        report_type="TH",
        report_date=date.today(),
        defect_rows=range(1, 11),
        rejection_rows=range(1, 11),
    )


@auth_bp.route("/logout")
def logout() -> Any:
    """Log the user out and redirect to the login page."""

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

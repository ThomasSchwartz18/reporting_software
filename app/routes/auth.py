"""Authentication routes."""
from __future__ import annotations

from flask import Blueprint, flash, redirect, render_template, request, session, url_for

from ..models import User


auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/", methods=["GET", "POST"])
@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    """Render the login form and handle submissions."""
    users = User.query.order_by(User.username).all()

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            session["user_id"] = user.id
            session["username"] = user.username
            flash("Logged in successfully.", "success")
            return redirect(url_for("auth.dashboard"))

        flash("Invalid username or password.", "error")

    return render_template("auth/login.html", users=users)


@auth_bp.route("/dashboard")
def dashboard():
    """Display a simple dashboard for authenticated users."""
    if session.get("user_id") is None:
        flash("Please log in to continue.", "error")
        return redirect(url_for("auth.login"))

    return render_template("auth/dashboard.html", username=session.get("username"))


@auth_bp.route("/reports/aoi/smt")
def report_aoi_smt():
    """Render the SMT AOI report selection."""
    if session.get("user_id") is None:
        flash("Please log in to continue.", "error")
        return redirect(url_for("auth.login"))

    return render_template("auth/report_aoi_smt.html")


@auth_bp.route("/reports/aoi/th")
def report_aoi_th():
    """Render the TH AOI report selection."""
    if session.get("user_id") is None:
        flash("Please log in to continue.", "error")
        return redirect(url_for("auth.login"))

    return render_template("auth/report_aoi_th.html")


@auth_bp.route("/logout")
def logout():
    """Log the user out and redirect to the login page."""
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for("auth.login"))

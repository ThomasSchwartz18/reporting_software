"""Database models for the reporting software."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from sqlalchemy import inspect, text
from werkzeug.security import check_password_hash, generate_password_hash

from .extensions import db


class Role(str, Enum):
    """Enumeration of user roles within the platform."""

    ADMIN = "admin"
    MANAGER = "manager"
    STAFF = "staff"

    @property
    def label(self) -> str:
        """Return a human-readable label for the role."""

        return {
            Role.ADMIN: "Administrator",
            Role.MANAGER: "Manager",
            Role.STAFF: "Team Member",
        }[self]


@dataclass
class User(db.Model):
    """Represents an authenticated user."""

    id: int = db.Column(db.Integer, primary_key=True)
    username: str = db.Column(db.String(64), unique=True, nullable=False)
    password_hash: str = db.Column(db.String(255), nullable=False)
    role: str = db.Column(db.String(32), nullable=False, default=Role.STAFF.value)

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

    @property
    def role_enum(self) -> Role:
        """Return the role as an enum instance."""

        return Role(self.role)


@dataclass
class ApplicationSetting(db.Model):
    """Represents configurable application-wide settings."""

    key: str = db.Column(db.String(64), primary_key=True)
    value: str = db.Column(db.String(255), nullable=False)

    @staticmethod
    def get_value(key: str, default: str = "") -> str:
        """Fetch the stored value for ``key`` or return ``default``."""

        setting = ApplicationSetting.query.filter_by(key=key).first()
        return setting.value if setting else default

    @staticmethod
    def set_value(key: str, value: str) -> None:
        """Persist ``value`` for ``key`` in the database."""

        setting = ApplicationSetting.query.filter_by(key=key).first()
        if setting is None:
            setting = ApplicationSetting(key=key, value=value)
            db.session.add(setting)
        else:
            setting.value = value


@dataclass
class EmployeeSubmission(db.Model):
    """Represents operational data submitted by employees."""

    id: int = db.Column(db.Integer, primary_key=True)
    employee_name: str = db.Column(db.String(120), nullable=False)
    department: str = db.Column(db.String(120), nullable=False)
    metric_name: str = db.Column(db.String(120), nullable=False)
    value: float = db.Column(db.Float, nullable=False, default=0.0)
    performance_score: float = db.Column(db.Float, nullable=False, default=0.0)
    status: str = db.Column(db.String(64), nullable=False, default="On Track")
    submitted_at: datetime = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)


DEFAULT_USERS: tuple[dict[str, str | Role], ...] = (
    {"username": "2276", "password": "2278!", "role": Role.MANAGER},
    {"username": "Schwartz", "password": "2276", "role": Role.ADMIN},
)


def ensure_user_role_column() -> None:
    """Ensure the ``role`` column exists on the ``user`` table."""

    inspector = inspect(db.engine)
    if "user" not in inspector.get_table_names():
        return

    columns = {column_info["name"] for column_info in inspector.get_columns("user")}
    if "role" in columns:
        return

    default_role = Role.STAFF.value
    escaped_default_role = default_role.replace("'", "''")
    with db.engine.begin() as connection:
        connection.execute(
            text(
                "ALTER TABLE user ADD COLUMN role TEXT NOT NULL DEFAULT "
                f"'{escaped_default_role}'"
            )
        )
        connection.execute(
            text("UPDATE user SET role = :default_role WHERE role IS NULL OR role = ''"),
            {"default_role": default_role},
        )


def ensure_default_user() -> None:
    """Ensure the default user roster exists and has the correct roles."""

    changed = False
    for default_user in DEFAULT_USERS:
        username = str(default_user["username"])
        password = str(default_user["password"])
        role = Role(default_user["role"])

        user = User.query.filter_by(username=username).first()
        if user is None:
            user = User(username=username, role=role.value)
            user.set_password(password)
            db.session.add(user)
            changed = True
        else:
            if user.role != role.value:
                user.role = role.value
                changed = True

    if changed:
        db.session.commit()

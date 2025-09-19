"""Database models for the reporting software."""
from __future__ import annotations

from dataclasses import dataclass

from werkzeug.security import check_password_hash, generate_password_hash

from .extensions import db


@dataclass
class User(db.Model):
    """Represents an authenticated user."""

    id: int = db.Column(db.Integer, primary_key=True)
    username: str = db.Column(db.String(64), unique=True, nullable=False)
    password_hash: str = db.Column(db.String(255), nullable=False)

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)


DEFAULT_USERS: tuple[tuple[str, str], ...] = (
    ("2276", "2278!"),
    ("Schwartz", "2276"),
)


def ensure_default_user() -> None:
    """Ensure the default user exists in the database."""
    created_user = False
    for username, password in DEFAULT_USERS:
        user = User.query.filter_by(username=username).first()
        if user is None:
            user = User(username=username)
            user.set_password(password)
            db.session.add(user)
            created_user = True

    if created_user:
        db.session.commit()

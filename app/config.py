"""Configuration objects for the Flask application."""
from __future__ import annotations

import os
from pathlib import Path


def _int_from_env(name: str, default: int) -> int:
    """Return an integer value from ``name`` or ``default`` when missing/invalid."""

    raw_value = os.environ.get(name)
    if raw_value is None:
        return default
    try:
        return int(raw_value)
    except ValueError:
        return default


class Config:
    """Base configuration."""

    SECRET_KEY = os.environ.get("FLASK_SECRET_KEY", "dev-secret-key")
    SQLALCHEMY_DATABASE_URI = (
        os.environ.get("DATABASE_URL")
        or f"sqlite:///{Path(os.environ.get('FLASK_INSTANCE_PATH', 'instance')).absolute() / 'app.db'}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SUPABASE_URL = os.environ.get("SUPABASE_URL")
    SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
    SUPABASE_TIMEOUT = _int_from_env("SUPABASE_TIMEOUT", 10)

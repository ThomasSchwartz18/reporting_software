"""Configuration objects for the Flask application."""
from __future__ import annotations

import os
from pathlib import Path


class Config:
    """Base configuration."""

    SECRET_KEY = os.environ.get("FLASK_SECRET_KEY", "dev-secret-key")
    SQLALCHEMY_DATABASE_URI = (
        os.environ.get("DATABASE_URL")
        or f"sqlite:///{Path(os.environ.get('FLASK_INSTANCE_PATH', 'instance')).absolute() / 'app.db'}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

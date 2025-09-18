"""Application factory for the reporting software."""
from __future__ import annotations

from pathlib import Path

from flask import Flask

from .config import Config
from .extensions import db
from .models import ensure_default_user
from .routes.auth import auth_bp


def create_app(config_object: type[Config] | None = None) -> Flask:
    """Application factory used by Flask.

    Parameters
    ----------
    config_object: type[Config] | None
        Optional configuration object to allow overriding defaults when
        creating the application.
    """
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(config_object or Config())

    register_extensions(app)
    register_blueprints(app)
    initialize_database(app)

    @app.route("/health")
    def health() -> tuple[str, int]:
        """Simple healthcheck endpoint."""
        return "OK", 200

    return app


def register_extensions(app: Flask) -> None:
    """Register Flask extensions."""
    db.init_app(app)


def register_blueprints(app: Flask) -> None:
    """Register Flask blueprints."""
    app.register_blueprint(auth_bp)


def initialize_database(app: Flask) -> None:
    """Ensure the database is ready to use."""
    with app.app_context():
        Path(app.instance_path).mkdir(parents=True, exist_ok=True)
        db.create_all()
        ensure_default_user()

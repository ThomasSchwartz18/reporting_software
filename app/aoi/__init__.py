"""AOI inspection blueprint setup."""
from __future__ import annotations

from flask import Blueprint


aoi_bp = Blueprint(
    "aoi",
    __name__,
    template_folder="templates",
    static_folder="static",
)


from . import routes  # noqa: E402  # pylint: disable=wrong-import-position
from .service import ensure_problem_codes  # noqa: E402

__all__ = ["aoi_bp", "ensure_problem_codes"]

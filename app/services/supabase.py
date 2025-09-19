"""Helper for interacting with the Supabase REST API."""
from __future__ import annotations

import json
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from flask import current_app

__all__ = [
    "SupabaseError",
    "SupabaseConfigurationError",
    "SupabaseRequestError",
    "fetch_defect_definitions",
]


class SupabaseError(Exception):
    """Base exception for Supabase related errors."""


class SupabaseConfigurationError(SupabaseError):
    """Raised when required Supabase configuration is missing."""


class SupabaseRequestError(SupabaseError):
    """Raised when a Supabase API call fails."""


def _build_request(path: str) -> Request:
    """Return a configured :class:`urllib.request.Request` for ``path``."""

    base_url: str | None = current_app.config.get("SUPABASE_URL")
    api_key: str | None = current_app.config.get("SUPABASE_KEY")

    if not base_url or not api_key:
        raise SupabaseConfigurationError(
            "Supabase configuration is incomplete; set SUPABASE_URL and SUPABASE_KEY"
        )

    url = f"{base_url.rstrip('/')}/{path.lstrip('/')}"
    headers = {
        "apikey": api_key,
        "Authorization": f"Bearer {api_key}",
        "Accept": "application/json",
        "User-Agent": "reporting-software/1.0",
    }

    return Request(url, headers=headers)


def _execute(request: Request) -> Any:
    """Execute ``request`` and return the decoded JSON payload."""

    timeout: int = current_app.config.get("SUPABASE_TIMEOUT", 10)

    try:
        with urlopen(request, timeout=timeout) as response:  # noqa: S310 (trusted URL)
            payload = response.read()
    except HTTPError as exc:  # pragma: no cover - exercised via integration tests
        detail = ""
        if exc.fp is not None:
            try:
                detail = exc.fp.read().decode("utf-8")
            except Exception:  # pragma: no cover - defensive
                detail = ""
        raise SupabaseRequestError(f"HTTP {exc.code}: {detail or exc.reason}") from exc
    except URLError as exc:  # pragma: no cover - network failure
        raise SupabaseRequestError(str(exc.reason)) from exc

    try:
        return json.loads(payload)
    except json.JSONDecodeError as exc:  # pragma: no cover - defensive
        raise SupabaseRequestError("Supabase response could not be decoded as JSON") from exc


def fetch_defect_definitions() -> list[dict[str, int | str | None]]:
    """Return defect definitions from Supabase as ``id``/``name`` pairs."""

    request = _build_request("rest/v1/defects?select=*&order=id.asc")
    payload = _execute(request)

    if not isinstance(payload, list):
        raise SupabaseRequestError("Unexpected Supabase response shape for defects table")

    defects: list[dict[str, int | str | None]] = []

    for item in payload:
        if not isinstance(item, dict):
            continue

        raw_id = item.get("id")
        raw_name = item.get("name")
        raw_part_type = item.get("part_type")

        try:
            code = int(raw_id)
        except (TypeError, ValueError):
            current_app.logger.warning(
                "Skipping Supabase defect with invalid id: %r", raw_id
            )
            continue

        name = str(raw_name).strip() if raw_name is not None else ""
        if not name:
            current_app.logger.warning(
                "Skipping Supabase defect %s with missing name", code
            )
            continue

        part_type = (
            str(raw_part_type).strip() if raw_part_type not in {None, ""} else None
        )

        defects.append({"id": code, "name": name, "part_type": part_type})

    return defects

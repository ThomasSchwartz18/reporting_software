from __future__ import annotations

import os
from typing import Optional

from dotenv import load_dotenv

from ui.app import create_app


def _is_debug_enabled(flag: Optional[str]) -> bool:
    if not flag:
        return False
    return flag.lower() in {"1", "true", "yes", "on"}


def main() -> None:
    load_dotenv()

    app = create_app()

    host = os.getenv("FLASK_RUN_HOST", "0.0.0.0")
    port = int(os.getenv("FLASK_RUN_PORT", "5000"))
    debug = _is_debug_enabled(os.getenv("FLASK_DEBUG"))

    app.run(host=host, port=port, debug=debug, use_reloader=debug)


if __name__ == "__main__":
    main()

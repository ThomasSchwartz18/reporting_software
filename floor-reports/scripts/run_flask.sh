#!/usr/bin/env bash
set -euo pipefail

# Start the Flask UI for the AOI reporting system.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="${SCRIPT_DIR}/.."

cd "$PROJECT_ROOT"

export PYTHONPATH="${PROJECT_ROOT}:${PYTHONPATH:-}"
export FLASK_APP="ui.app:create_app"
export FLASK_RUN_PORT="5000"
export FLASK_RUN_HOST="0.0.0.0"

flask run "$@"

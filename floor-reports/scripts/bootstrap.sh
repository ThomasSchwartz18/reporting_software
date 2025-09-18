#!/usr/bin/env bash
set -euo pipefail

# Create venv
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# Start Postgres if docker-compose present and DATABASE_URL looks like Postgres
if grep -q "postgresql+psycopg" .env 2>/dev/null; then
  docker compose up -d db adminer
  echo "Waiting for Postgres..."; sleep 3
fi

# Initialize Alembic (idempotent)
if [ ! -d migrations ]; then
  alembic init migrations
fi

# Overwrite migrations/env.py with our config
cat > migrations/env.py <<'PY'
from __future__ import annotations
import os
from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context

# Interpret the config file for Python logging.
config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Set URL from env; fallback to SQLite file
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./app.db")
config.set_main_option("sqlalchemy.url", DATABASE_URL)

# Import metadata
from app.models import Base  # noqa: E402

target_metadata = Base.metadata

def run_migrations_offline():
    url = config.get_main_option("sqlalchemy.url")
    context.configure(url=url, target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online():
    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
PY

# Create initial migration from models
alembic revision --autogenerate -m "init"
alembic upgrade head

# Make output dir for reports
mkdir -p reports/out

echo "Bootstrap complete."

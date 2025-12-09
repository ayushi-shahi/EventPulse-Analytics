from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context

import os
import sys

# Add backend folder to PYTHONPATH
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

# Import Base metadata AFTER fixing path
from app.models.base import Base
# Import all model modules so Alembic sees the tables
from app.models import (
    user,
    event,
    alert,
    aggregate,
    api_key,
    audit_log,
    event_batch,
)


# Get Alembic Config
config = context.config

# Load .env settings
from app.config import settings

# OVERRIDE DATABASE URL with sync URL (REQUIRED)
sync_url = settings.DATABASE_URL.replace("+asyncpg", "")
config.set_main_option("sqlalchemy.url", sync_url)

# Logging
if config.config_file_name:
    fileConfig(config.config_file_name)

# Metadata for autogenerate
target_metadata = Base.metadata


def run_migrations_offline():
    """Run migrations in offline mode."""
    context.configure(
        url=sync_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    """Run migrations in online (sync) mode."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

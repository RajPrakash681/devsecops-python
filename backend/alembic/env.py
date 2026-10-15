from logging.config import fileConfig

from alembic import context
from sqlalchemy import create_engine, pool, text

from app import models  # noqa: F401 - registers the tables on Base.metadata
from app.config import database_url
from app.db import Base

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

# Every backend pod runs `alembic upgrade head` before it starts serving. Two pods starting
# together would both try to create the same tables, so they take a Postgres advisory lock:
# the second pod waits for the first, then finds the schema current and has nothing to do.
MIGRATION_LOCK_ID = 2_110_328  # any constant shared by all pods


def run_migrations_offline() -> None:
    context.configure(url=database_url(), target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    engine = create_engine(database_url(), poolclass=pool.NullPool)
    with engine.connect() as connection:
        is_pg = connection.dialect.name == "postgresql"
        if is_pg:
            print("migration lock: waiting", flush=True)
            connection.execute(text("SELECT pg_advisory_lock(:id)"), {"id": MIGRATION_LOCK_ID})
            connection.commit()
            print("migration lock: acquired", flush=True)
        try:
            context.configure(connection=connection, target_metadata=target_metadata)
            with context.begin_transaction():
                context.run_migrations()
        finally:
            if is_pg:
                connection.execute(text("SELECT pg_advisory_unlock(:id)"), {"id": MIGRATION_LOCK_ID})
                connection.commit()
                print("migration lock: released", flush=True)


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

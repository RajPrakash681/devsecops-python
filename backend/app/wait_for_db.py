"""Block until the database accepts connections (container start-up ordering)."""
import sys
import time

from sqlalchemy import create_engine, text

from .config import database_url


def main(timeout: int = 90) -> int:
    engine = create_engine(database_url(), pool_pre_ping=True)
    deadline = time.monotonic() + timeout
    while True:
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            print("database is reachable", flush=True)
            return 0
        except Exception as exc:  # noqa: BLE001
            if time.monotonic() > deadline:
                print(f"database not reachable after {timeout}s: {type(exc).__name__}", file=sys.stderr)
                return 1
            print("waiting for database...", flush=True)
            time.sleep(2)


if __name__ == "__main__":
    sys.exit(main())

from sqlalchemy import inspect, text

from app.database import Base, engine
import app.models  # noqa: F401 — register models with Base.metadata


def init_database() -> None:
    Base.metadata.create_all(bind=engine)
    _apply_postgres_migrations()


def _apply_postgres_migrations() -> None:
    """Add columns/tables for existing databases without Alembic."""
    insp = inspect(engine)
    tables = insp.get_table_names()

    with engine.begin() as conn:
        if "users" not in tables:
            return

        if "study_sessions" in tables:
            cols = {c["name"] for c in insp.get_columns("study_sessions")}
            if "user_id" not in cols:
                conn.execute(
                    text(
                        "ALTER TABLE study_sessions "
                        "ADD COLUMN user_id INTEGER REFERENCES users(id) ON DELETE CASCADE"
                    )
                )
            if "content_difficulty" not in cols:
                conn.execute(
                    text(
                        "ALTER TABLE study_sessions "
                        "ADD COLUMN content_difficulty VARCHAR(32) DEFAULT 'intermediate'"
                    )
                )
            if "output_language" not in cols:
                conn.execute(
                    text(
                        "ALTER TABLE study_sessions "
                        "ADD COLUMN output_language VARCHAR(8) DEFAULT 'en'"
                    )
                )

        if "quiz_attempts" not in tables:
            Base.metadata.tables["quiz_attempts"].create(bind=conn, checkfirst=True)

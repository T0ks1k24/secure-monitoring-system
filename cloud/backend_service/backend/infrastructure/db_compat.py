from __future__ import annotations

from sqlalchemy import text

from infrastructure.database import engine


def ensure_events_schema_compat() -> None:
    """
    Bring legacy `events` table shape in sync with current model.
    Safe to run on every startup.
    """
    if engine.dialect.name != "postgresql":
        return

    statements = [
        "ALTER TABLE IF EXISTS events ADD COLUMN IF NOT EXISTS event_type VARCHAR",
        "ALTER TABLE IF EXISTS events ADD COLUMN IF NOT EXISTS object_class VARCHAR",
        "ALTER TABLE IF EXISTS events ADD COLUMN IF NOT EXISTS track_id INTEGER",
        "ALTER TABLE IF EXISTS events ADD COLUMN IF NOT EXISTS confidence DOUBLE PRECISION",
        "ALTER TABLE IF EXISTS events ADD COLUMN IF NOT EXISTS timestamp TIMESTAMP",
        "ALTER TABLE IF EXISTS events ADD COLUMN IF NOT EXISTS zone_id VARCHAR",
        "ALTER TABLE IF EXISTS events ADD COLUMN IF NOT EXISTS zone_name VARCHAR",
        "ALTER TABLE IF EXISTS events ADD COLUMN IF NOT EXISTS risk VARCHAR",
        "ALTER TABLE IF EXISTS events ADD COLUMN IF NOT EXISTS bbox JSONB",
        "ALTER TABLE IF EXISTS events ADD COLUMN IF NOT EXISTS metadata JSON DEFAULT '{}'::json",
    ]

    with engine.begin() as conn:
        for sql in statements:
            conn.execute(text(sql))

        # If old schema had `type`, keep data by copying into `event_type`.
        conn.execute(
            text(
                """
                DO $$
                BEGIN
                    IF EXISTS (
                        SELECT 1
                        FROM information_schema.columns
                        WHERE table_name = 'events' AND column_name = 'type'
                    ) THEN
                        UPDATE events
                        SET event_type = COALESCE(event_type, type)
                        WHERE event_type IS NULL;
                    END IF;
                END $$;
                """
            )
        )

        conn.execute(
            text(
                """
                UPDATE events
                SET event_type = COALESCE(event_type, 'unknown'),
                    risk = COALESCE(risk, 'low'),
                    metadata = COALESCE(metadata, '{}'::json)
                WHERE event_type IS NULL OR risk IS NULL OR metadata IS NULL
                """
            )
        )

        # Legacy schema may include `persons INTEGER NOT NULL`.
        # New events don't send this field, so make it optional/safe.
        conn.execute(
            text(
                """
                DO $$
                BEGIN
                    IF EXISTS (
                        SELECT 1
                        FROM information_schema.columns
                        WHERE table_name = 'events' AND column_name = 'persons'
                    ) THEN
                        EXECUTE 'ALTER TABLE events ALTER COLUMN persons SET DEFAULT 0';
                        EXECUTE 'UPDATE events SET persons = 0 WHERE persons IS NULL';
                        EXECUTE 'ALTER TABLE events ALTER COLUMN persons DROP NOT NULL';
                    END IF;
                END $$;
                """
            )
        )

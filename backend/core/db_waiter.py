import time
from sqlalchemy import text
from infrastructure.database import engine


def wait_for_db():

    print("⏳ Waiting for PostgreSQL...")

    while True:
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            print("✅ PostgreSQL is ready!")
            break
        except Exception as e:
            print("DB not ready, retrying...")
            time.sleep(5)

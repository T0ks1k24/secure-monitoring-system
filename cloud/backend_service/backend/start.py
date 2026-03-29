import time
import socket
import subprocess
from urllib.parse import urlparse

from core.config import settings


def wait_for_database():
    database_url = settings.DATABASE_URL

    if database_url.startswith("sqlite"):
        print("SQLite configured, skipping database wait")
        return

    parsed = urlparse(database_url)
    host = parsed.hostname
    port = parsed.port or 5432

    if not host:
        print("Database host is not configured, skipping wait")
        return

    print(f"Waiting for database {host}:{port}...")

    while True:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            s.connect((host, port))
            s.close()
            print("Database READY")
            break
        except Exception:
            time.sleep(2)


if __name__ == "__main__":

    wait_for_database()

    print("Starting Uvicorn...")

    subprocess.run([
        "uv",
        "run",
        "uvicorn",
        "main:app",
        "--host",
        "0.0.0.0",
        "--port",
        "8000"
    ])

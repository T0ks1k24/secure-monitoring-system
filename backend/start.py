import time
import socket
import subprocess


def wait_for_postgres():

    print("Waiting for PostgreSQL...")

    while True:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            s.connect(("postgres", 5432))
            s.close()
            print("PostgreSQL READY")
            break
        except:
            time.sleep(2)


if __name__ == "__main__":

    wait_for_postgres()

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

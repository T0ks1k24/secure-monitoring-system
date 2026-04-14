# Backend Service

## Run in Git Bash

From `cloud/backend_service/backend`:

```bash
export DATABASE_URL="sqlite:///./local.db"
uv run uvicorn main:app --host 127.0.0.1 --port 8000
```

This is the same local start command I used to run the service without the external `postgres` host from `.env`.

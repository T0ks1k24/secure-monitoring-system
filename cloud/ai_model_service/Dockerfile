FROM python:3.12-slim

WORKDIR /app

# Install system dependencies for OpenCV and YOLO
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libgl1 \
    libglib2.0-0 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Copy project configuration
COPY pyproject.toml uv.lock ./

# Install dependencies
RUN uv sync --frozen --no-dev

# Copy application code and models
COPY . .

# Pre-download YOLOv8n weights at build time so runtime не потребує інтернету.
# Модель зберігається в /root/.cache/ultralytics/
ENV PATH="/app/.venv/bin:$PATH"
RUN python -c "from ultralytics import YOLO; YOLO('yolov8n.pt')" \
    && echo "YOLOv8n downloaded OK"

ENV PYTHONUNBUFFERED=1

EXPOSE 5000

CMD ["uv", "run", "--no-sync", "python", "main.py"]

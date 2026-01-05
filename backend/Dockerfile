FROM python:3.11-slim

# System deps needed by this repo
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libimage-exiftool-perl \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Poetry
RUN pip install --no-cache-dir poetry

# Copy dependency manifests first (better layer caching)
COPY pyproject.toml poetry.lock* /app/

# Install deps (no venv inside container)
RUN poetry config virtualenvs.create false \
 && poetry install --no-interaction --no-ansi

# Copy the rest of the backend code
COPY . /app

# Render sets PORT; expose is optional but nice
EXPOSE 10000

# Start FastAPI
CMD ["uvicorn", "gpx_helper.api.main:app", "--host", "0.0.0.0", "--port", "${PORT}"]

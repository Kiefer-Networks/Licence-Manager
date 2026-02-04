FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy application code first (required for package installation)
COPY pyproject.toml .
COPY src/ ./src/
COPY alembic.ini .
COPY alembic/ ./alembic/

# Install Python package with dependencies
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install .

# Copy entrypoint script
COPY docker-entrypoint.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

# Create non-root user
RUN useradd --create-home --shell /bin/bash app

# Create data directory base (will be mounted as volume)
RUN mkdir -p /app/data && chown app:app /app/data

USER app

EXPOSE 8000

ENTRYPOINT ["docker-entrypoint.sh"]
CMD ["uvicorn", "licence_api.main:app", "--host", "0.0.0.0", "--port", "8000"]

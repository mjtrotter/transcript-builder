# Transcript Builder API - Dockerfile
# Multi-stage build for smaller production image

# =============================================================================
# BUILD STAGE
# =============================================================================
FROM python:3.11-slim as builder

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    libffi-dev \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libgdk-pixbuf2.0-0 \
    libcairo2 \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install Python dependencies
COPY pyproject.toml ./
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir .

# =============================================================================
# PRODUCTION STAGE
# =============================================================================
FROM python:3.11-slim as production

# Install runtime dependencies for WeasyPrint PDF generation
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libgdk-pixbuf2.0-0 \
    libcairo2 \
    libffi8 \
    fonts-liberation \
    && rm -rf /var/lib/apt/lists/*

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Create non-root user
RUN useradd --create-home --shell /bin/bash appuser

# Set working directory
WORKDIR /app

# Copy application code
COPY --chown=appuser:appuser . .

# Create directories for uploads and output
RUN mkdir -p /app/uploads /app/output && \
    chown -R appuser:appuser /app/uploads /app/output

# Switch to non-root user
USER appuser

# Environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    ENVIRONMENT=production

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

# Run the application
CMD ["uvicorn", "transcript_builder.api.main:app", "--host", "0.0.0.0", "--port", "8000"]

# =============================================================================
# DEVELOPMENT STAGE
# =============================================================================
FROM production as development

USER root

# Install development dependencies
RUN pip install --no-cache-dir pytest pytest-asyncio pytest-cov httpx black ruff mypy

USER appuser

# Enable reload for development
CMD ["uvicorn", "transcript_builder.api.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

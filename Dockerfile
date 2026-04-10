# ============================================================================
# Stage 1: Build frontend
# ============================================================================
FROM node:20-slim AS frontend-build

WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --ignore-scripts
COPY frontend/ ./
RUN npm run build

# ============================================================================
# Stage 2: Python runtime
# ============================================================================
FROM python:3.11-slim AS runtime

WORKDIR /app

# System deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Python deps (install before copying code for layer caching)
COPY agent/requirements.txt agent/requirements.txt
RUN pip install --no-cache-dir -r agent/requirements.txt

# Copy project
COPY pyproject.toml LICENSE README.md ./
COPY agent/ agent/

# Copy built frontend
COPY --from=frontend-build /app/frontend/dist frontend/dist

# Install CLI entrypoint
RUN pip install --no-cache-dir -e .

# Default port
EXPOSE 8899

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8899/health')" || exit 1

# Run API server (serves frontend/dist as static files)
CMD ["vibe-trading", "serve", "--host", "0.0.0.0", "--port", "8899"]

# ============================================
# Build stage - compile dependencies
# ============================================
FROM python:3.12-slim as builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy production requirements only
COPY requirements_deploy.txt requirements.txt

# Install to /root/local for clean copy
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# ============================================
# Runtime stage - minimal production image
# ============================================
FROM python:3.12-slim

WORKDIR /app

# Install runtime dependencies only (for image processing)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Copy installed packages from builder
COPY --from=builder /install /usr/local
ENV PATH=/usr/local/bin:$PATH

# Copy application code
COPY health_butler/ ./health_butler/
COPY src/ ./src/

# Create directories for image processing and data persistence
RUN mkdir -p /tmp /app/data && chmod 777 /tmp /app/data

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8080

# Health check for Cloud Run
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8080/health').read()"

# Expose Cloud Run port
EXPOSE 8080

# Run Discord Bot with health check
CMD ["python", "-m", "health_butler.discord_bot.bot"]

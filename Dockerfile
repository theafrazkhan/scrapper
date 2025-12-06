# Use Python 3.10 slim as base image
FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Set environment variables early
ENV PYTHONUNBUFFERED=1 \
    FLASK_APP=frontend/app.py \
    PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=0 \
    PLAYWRIGHT_BROWSERS_PATH=/ms-playwright

# Copy requirements files
COPY frontend/requirements.txt /app/frontend/requirements.txt
COPY backend/requirements.txt /app/backend/requirements.txt

# Install Python dependencies
RUN pip install --no-cache-dir -r frontend/requirements.txt && \
    pip install --no-cache-dir -r backend/requirements.txt

# Install Playwright browser only (skip system deps, we'll install manually)
RUN playwright install chromium

# Install system dependencies manually for Debian
RUN apt-get update && apt-get install -y \
    libnss3 \
    libnspr4 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libdbus-1-3 \
    libxkbcommon0 \
    libatspi2.0-0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libasound2 \
    libpango-1.0-0 \
    libcairo2 \
    && rm -rf /var/lib/apt/lists/*

# Copy application code
COPY frontend/ /app/frontend/
COPY backend/ /app/backend/

# Create necessary directories
RUN mkdir -p /app/frontend/instance \
    /app/backend/data/results \
    /app/backend/logs

# Copy initialization script
COPY docker-init.sh /app/docker-init.sh
RUN chmod +x /app/docker-init.sh

# Expose Flask port
EXPOSE 5000

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV FLASK_APP=frontend/app.py

# Command to run the application
CMD ["/app/docker-init.sh"]
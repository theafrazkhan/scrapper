# Use Python 3.10 slim as base image
FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    FLASK_APP=frontend/app.py \
    PLAYWRIGHT_BROWSERS_PATH=/ms-playwright \
    CHROME_BIN=/usr/bin/chromium \
    CHROMEDRIVER_PATH=/usr/bin/chromedriver

# Install system dependencies for Chrome/Chromium and Playwright
RUN apt-get update && apt-get install -y \
    # Chrome/Chromium for Selenium
    chromium \
    chromium-driver \
    # Playwright dependencies
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
    # Utilities
    curl \
    wget \
    gnupg \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements files
COPY frontend/requirements.txt /app/frontend/requirements.txt
COPY backend/requirements.txt /app/backend/requirements.txt

# Install Python dependencies
RUN pip install --no-cache-dir -r frontend/requirements.txt && \
    pip install --no-cache-dir -r backend/requirements.txt && \
    pip install --no-cache-dir webdriver-manager

# Install Playwright browser (for any scripts that use it)
RUN playwright install chromium || true

# Copy application code
COPY frontend/ /app/frontend/
COPY backend/ /app/backend/

# Create necessary directories
RUN mkdir -p /app/backend/data/results \
    /app/backend/data/cookie \
    /app/backend/data/html \
    /app/backend/data/categories \
    /app/backend/logs \
    /app/backend/web

# Expose Flask port
EXPOSE 5000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:5000/ || exit 1

# Start the application
CMD ["python", "frontend/app.py"]
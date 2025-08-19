# Use Python 3.10 slim image for better performance
FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Install system dependencies required for Playwright and SQL Server
RUN apt-get update && apt-get install -y \
    # System dependencies
    wget \
    gnupg \
    ca-certificates \
    curl \
    unixodbc-dev \
    g++ \
    # Required for Playwright browsers (manually install instead of playwright install-deps)
    libnss3 \
    libnspr4 \
    libatk-bridge2.0-0 \
    libdrm2 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxrandr2 \
    libgbm1 \
    libxss1 \
    libasound2 \
    libatspi2.0-0 \
    libgtk-3-0 \
    # Font packages (replacements for missing ARM64 fonts)
    fonts-liberation \
    fonts-noto-color-emoji \
    fonts-dejavu-core \
    fontconfig \
    # Virtual display for headless mode
    xvfb \
    # Cleanup
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better Docker layer caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright browsers ONLY (skip install-deps to avoid font conflicts)
RUN playwright install chromium

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p "Financial Reports" "RO Reports" logs

# Set environment variables for Playwright
ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright
ENV DISPLAY=:99
ENV PYTHONUNBUFFERED=1

# Create non-root user for security
RUN useradd -m -u 1000 automation && \
    chown -R automation:automation /app && \
    chown -R automation:automation /ms-playwright
USER automation

# Expose port if needed (optional)
EXPOSE 8080

# Default command - can be overridden in docker-compose
CMD ["python", "scheduler.py"]

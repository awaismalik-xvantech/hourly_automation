FROM python:3.10-slim

# Set timezone to Arizona
ENV TZ=America/Phoenix
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# Install system dependencies for Playwright and SQL Server
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    ca-certificates \
    unixodbc-dev \
    gcc \
    g++ \
    # Playwright browser dependencies (fixed package names)
    libglib2.0-0 \
    libgobject-2.0-0 \
    libnspr4 \
    libnss3 \
    libdbus-1-3 \
    libgio-2.0-0 \
    libatk1.0-0 \
    libexpat1 \
    libatspi2.0-0 \
    libx11-6 \
    libxcomposite1 \
    libxdamage1 \
    libxext6 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libxcb1 \
    libxkbcommon0 \
    libasound2 \
    # Additional libraries for better compatibility
    libdrm2 \
    libxss1 \
    libgtk-3-0 \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright browsers only (NO install-deps to avoid ARM64 font issues)
RUN playwright install chromium

# Copy application files
COPY . .

# Create directories for reports
RUN mkdir -p "Financial Reports" "RO Reports" logs

# Set permissions
RUN chmod +x /app

# Default command runs the hourly scheduler
CMD ["python", "scheduler.py"]

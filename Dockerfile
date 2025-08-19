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

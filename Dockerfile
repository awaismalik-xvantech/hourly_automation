FROM python:3.10-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    fonts-liberation \
    libasound2 \
    libatk-bridge2.0-0 \
    libatk1.0-0 \
    libatspi2.0-0 \
    libcups2 \
    libdbus-1-3 \
    libdrm2 \
    libgbm1 \
    libgtk-3-0 \
    libnspr4 \
    libnss3 \
    libpango-1.0-0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    xdg-utils \
    libu2f-udev \
    libvulkan1 \
    chromium \
    fonts-noto-color-emoji \
    fonts-noto-core \
    fonts-noto-mono \
    xvfb \
    && rm -rf /var/lib/apt/lists/*

# Set up Chrome environment
ENV CHROME_PATH=/usr/bin/chromium \
    CHROMIUM_PATH=/usr/bin/chromium

# Copy and install Python requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Configure Playwright to use system Chromium
ENV PLAYWRIGHT_BROWSERS_PATH=0 \
    PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=1 \
    PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH=/usr/bin/chromium

# Set up Xvfb for headless browser
ENV DISPLAY=:99

COPY . .

ENV TZ=America/Phoenix
ENV PYTHONUNBUFFERED=1

EXPOSE 8000

# Start Xvfb and run the application
CMD Xvfb :99 -screen 0 1024x768x16 & python scheduler.py

FROM python:3.10-slim

WORKDIR /app

# Install essential system dependencies for Playwright
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    libglib2.0-0 \
    libgobject-2.0-0 \
    libnspr4 \
    libnss3 \
    libnssutil3 \
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
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

RUN playwright install chromium
RUN playwright install-deps chromium || echo "Some dependencies failed but continuing..."

COPY . .

ENV TZ=America/Phoenix
ENV PYTHONUNBUFFERED=1

EXPOSE 8000

CMD ["python", "scheduler.py"]

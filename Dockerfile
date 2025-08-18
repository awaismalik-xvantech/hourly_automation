FROM python:3.10-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

RUN playwright install chromium
RUN playwright install-deps chromium

COPY . .

ENV TZ=America/Phoenix
ENV PYTHONUNBUFFERED=1

EXPOSE 8000

CMD ["python", "scheduler.py"]

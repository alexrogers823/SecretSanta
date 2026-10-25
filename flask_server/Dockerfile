FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Cloud Run sets $PORT. One worker with threads suits a small, I/O-bound API.
CMD exec gunicorn --bind :$PORT --workers 1 --threads 8 "server:create_app()"

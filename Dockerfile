FROM python:3.12-slim

WORKDIR /app

# Install dependencies first for better layer caching.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

# Persisted ratings/results live here; mount a volume to keep them.
RUN mkdir -p /app/.data /app/.cache
ENV CACHE_TTL_MINUTES=30

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

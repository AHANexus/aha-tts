FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY aha_tts ./aha_tts

ENV HF_HOME=/app/.cache
RUN mkdir -p /app/.cache && chmod -R 777 /app/.cache

# Render خودش شماره پورت رو از طریق متغیر محیطی PORT می‌ده
CMD ["sh", "-c", "uvicorn aha_tts.server:app --host 0.0.0.0 --port ${PORT:-8000}"]

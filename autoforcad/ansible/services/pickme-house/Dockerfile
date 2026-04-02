FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY web/ ./web/

WORKDIR /app/web

ENV PYTHONUNBUFFERED=1

CMD ["python3", "app.py"]


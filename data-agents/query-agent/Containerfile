FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ app/

ENV PYTHONUNBUFFERED=1
ENV SQLITE_DB_PATH=/tmp/data/residential_energy.db

RUN mkdir -p /tmp/data

EXPOSE 8003

CMD ["python", "-m", "app.main"]

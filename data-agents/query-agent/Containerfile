FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ app/

ENV PYTHONUNBUFFERED=1
ENV SQLITE_DB_PATH=/tmp/residential_energy.db

EXPOSE 8003

CMD ["python", "-m", "app.main"]

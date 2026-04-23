FROM python:3.11-slim

WORKDIR /app

COPY init_db.py .

ENV SQLITE_DB_PATH=/data/residential_energy.db
ENV PYTHONUNBUFFERED=1

RUN mkdir -p /data

CMD ["python", "init_db.py"]

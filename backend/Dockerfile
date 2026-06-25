FROM python:3.12-slim
WORKDIR /app
ENV PYTHONPATH=/app/src \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    APPLICATION_PROPERTIES=/app/application.properties

COPY application.properties /app/application.properties
COPY backend/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY backend/src /app/src
COPY scripts /app/scripts
RUN python3 /app/scripts/seed_local_demo.py
WORKDIR /app/src

COPY backend/docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

ENTRYPOINT ["/docker-entrypoint.sh"]

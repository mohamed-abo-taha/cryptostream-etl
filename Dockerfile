# CryptoStream — container image for the pipeline + API + dashboard.
FROM python:3.12-slim

WORKDIR /app

# Install deps first for better layer caching.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV CRYPTOSTREAM_DB=/app/data/cryptostream.db \
    PYTHONUNBUFFERED=1

# Seed the warehouse at build time so the API/dashboard have data on first run.
RUN python run_pipeline.py --source mock

EXPOSE 5000 8501

# Default: serve the REST API. Override `command:` in compose for other roles.
CMD ["python", "run_api.py"]

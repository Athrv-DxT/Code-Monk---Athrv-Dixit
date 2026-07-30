FROM python:3.11-slim

# System dependencies (libsndfile1 is required by soundfile, curl for healthcheck)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    libsndfile1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Pre-download the lightweight embedding model to avoid startup delays and keep image size small
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('BAAI/bge-small-en-v1.5')"

# Copy application source code
COPY . .

# Expose backend port
EXPOSE 8000

# Start FastAPI application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

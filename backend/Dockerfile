# ===========================
# RezumAI Backend Dockerfile
# Build from /backend folder
# ===========================

FROM python:3.11-slim

WORKDIR /app

# Install system deps required by your code (PDF parsing, SSL, etc.)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxrender1 \
    libxext6 \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency manifest
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend code
COPY . /app

# Environment variables (FastAPI port)
ENV PORT=8000

# Expose container port
EXPOSE 8000

# Run FastAPI server (main.py lives inside /api/)
CMD ["sh", "-c", "uvicorn api.main:app --host 0.0.0.0 --port ${PORT}"]

FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Copy dependencies first for caching
COPY requirements.txt .

# Install dependencies, adding gunicorn for the server
RUN pip install --no-cache-dir -r requirements.txt gunicorn

# Copy your app code
COPY . .

# Expose the port Cloud Run expects
EXPOSE 8080

# Set a sensible default for the number of workers
# You can override this at runtime, e.g., in Cloud Run
ENV WEB_CONCURRENCY 2

# Start Gunicorn, which will manage Uvicorn workers
# -w: number of worker processes
# -k: the worker class to use (Uvicorn)
# --bind: the address and port to bind to
CMD ["gunicorn", "-w", "$WEB_CONCURRENCY", "-k", "uvicorn.workers.UvicornWorker", "api.main:app", "--bind", "0.0.0.0:8080"]
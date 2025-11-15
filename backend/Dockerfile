FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Copy dependencies first for caching
COPY requirements.txt .

# Install dependencies
# Make sure 'uvicorn' and 'gunicorn' are in your requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy your app code
COPY . .

# Expose the port (metadata only)
EXPOSE 8080

# Start Gunicorn using the shell form to sub $PORT
# -k uvicorn.workers.UvicornWorker is required for FastAPI
CMD gunicorn -k uvicorn.workers.UvicornWorker "api.main:app" --bind 0.0.0.0:$PORT
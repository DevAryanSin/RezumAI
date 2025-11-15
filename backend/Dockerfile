FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Copy dependencies
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt gunicorn

# Copy your app code
COPY . .

# Expose the port (metadata only)
EXPOSE 8080

# Set a default for the number of workers
ENV WEB_CONCURRENCY 2

# Start Gunicorn using the "shell form"
# This ensures $WEB_CONCURRENCY and $PORT are substituted
CMD gunicorn -w $WEB_CONCURRENCY "api.main:app" --bind 0.0.0.0:$PORT
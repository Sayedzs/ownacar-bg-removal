FROM python:3.10-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY main.py .

# Set environment variable for model download location
ENV U2NET_HOME=/app/.u2net
ENV PORT=8000

# Expose port
EXPOSE 8000

# Run the application - use shell form to expand $PORT
CMD uvicorn main:app --host 0.0.0.0 --port $PORT

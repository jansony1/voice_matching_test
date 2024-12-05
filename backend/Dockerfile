FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy all backend files
COPY backend/main.py .
COPY backend/services/ ./services/

# Create shared config directory first
RUN mkdir -p shared/config

# Then copy shared configuration
COPY shared/config/models_config.json shared/config/

# Expose the application port
EXPOSE 8000

# Use the full module path for uvicorn
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

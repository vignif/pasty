FROM python:3.9-slim

# Set working directory
WORKDIR /app

# Install system dependencies (if needed for db or builds)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

RUN rm -rf store.db

# Copy project files
COPY . .

# Expose app port
EXPOSE 6001

# Run with uvicorn
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "6001", "--workers", "4"]

# docker/Dockerfile (Corrected)

# Use Python 3.11 slim image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY src ./src
COPY wait_for_temporal.py .

# Default command (can be overridden)
# THIS IS THE CORRECTED LINE:
CMD ["python", "-m", "src.generic_worker"]
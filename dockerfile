FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libpcap-dev \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements from project root
COPY pyproject.toml poetry.lock ./

# Install Python dependencies
RUN pip install poetry && \
    poetry config virtualenvs.create false && \
    poetry install --only=main --no-root

# Copy application code from project root
COPY app/ app/

# Expose ports
EXPOSE 8080 4789/udp

# Variables de entorno por defecto
ENV PYTHONPATH=/app

# Run the application
CMD ["poetry", "run", "python", "app/sensor/run.py"]
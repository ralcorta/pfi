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
    poetry install --no-dev

# Copy application code from project root
COPY app/ .

# Run as root for simplicity (remove for production)
# RUN useradd -m -u 1000 sensor && \
#     chown -R sensor:sensor /app
# USER sensor

# Expose ports
EXPOSE 8080 4789/udp

# Variables de entorno por defecto
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1
ENV INTERFACE=eth0
ENV FILTER=tcp
ENV MODEL_PATH=/app/models/training/detection/convlstm_model.keras

# Health check (for local Docker - ECS handles its own health checks)
# HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
#     CMD curl -f http://localhost:8080/healthz || exit 1

# Run the application
CMD ["python", "-m", "app.sensor.run"]

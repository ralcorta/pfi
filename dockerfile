FROM python:3.11-slim

# Instalar dependencias del sistema
RUN apt-get update && apt-get install -y \
    tshark \
    tcpdump \
    libpcap-dev \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Configurar directorio de trabajo
WORKDIR /app

# Copiar archivos de dependencias
COPY pyproject.toml poetry.lock ./

# Instalar Poetry y dependencias
RUN pip install poetry && \
    poetry config virtualenvs.create false && \
    poetry install --no-dev

# Copiar código de la aplicación
COPY app/ ./app/
COPY models/ ./models/

# Crear usuario no-root
RUN useradd -m -u 1000 sensor && \
    chown -R sensor:sensor /app

# Cambiar a usuario no-root
USER sensor

# Exponer puerto para health checks
EXPOSE 8080

# Variables de entorno por defecto
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1
ENV NETWORK_INTERFACE=eth0
ENV CAPTURE_FILTER="udp port 4789"
ENV BUFFER_SIZE=100
ENV CONFIDENCE_THRESHOLD=0.7
ENV LOG_LEVEL=INFO
ENV SNS_ENABLED=false

# Comando por defecto
CMD ["python", "-m", "app.sensor.src.main"]
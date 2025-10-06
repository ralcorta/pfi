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
    poetry install --no-root

# Copiar todo el proyecto
COPY . .


# Variables de entorno por defecto
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Variables de entorno para AWS
# En ECS, las credenciales se obtienen automáticamente del IAM role
# Solo configuramos la región por defecto
ENV AWS_DEFAULT_REGION=us-east-1

# Comando por defecto
CMD ["python", "-m", "app.sensor.src.main", "--udp-port", "4789", "--http-port", "8080"]
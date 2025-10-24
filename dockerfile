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

# Crear directorios necesarios
RUN mkdir -p models/training/detection

# Copiar solo el código de la aplicación
COPY app/ ./app/
COPY .env .
COPY models/data/small/Malware ./models/data/small/Malware/
COPY models/training/detection/convlstm_model_advtrained.keras ./models/training/detection/
COPY models/training/detection/convlstm_model.keras ./models/training/detection/
COPY pyproject.toml poetry.lock ./


# Variables de entorno por defecto
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1
ENV INTERFACE=eth0
ENV FILTER=tcp
ENV MODEL_PATH=/app/models/training/detection/convlstm_model.keras

# Variables de entorno para AWS
# En ECS, las credenciales se obtienen automáticamente del IAM role
# Solo configuramos la región por defecto
ENV AWS_DEFAULT_REGION=us-east-1

# Comando por defecto
CMD ["python", "-m", "app.sensor.src.main", "--udp-port", "4789", "--http-port", "8080"]
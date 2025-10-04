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

# Copiar código de la aplicación
COPY app/ ./app/
COPY models/ ./models/

# Variables de entorno por defecto
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Variables AWS - usar AWS Academy si existen, sino dummy para local
ARG AWS_ACCESS_KEY_ID=${AWS_ACCESS_KEY_ID:-dummy}
ARG AWS_SECRET_ACCESS_KEY=${AWS_SECRET_ACCESS_KEY:-dummy}
ARG AWS_DEFAULT_REGION=${AWS_DEFAULT_REGION:-us-east-1}

ENV AWS_ACCESS_KEY_ID=${AWS_ACCESS_KEY_ID}
ENV AWS_SECRET_ACCESS_KEY=${AWS_SECRET_ACCESS_KEY}
ENV AWS_DEFAULT_REGION=${AWS_DEFAULT_REGION}

# Comando por defecto
CMD ["python", "-m", "app.sensor.src.main", "--port", "4789"]
# Sensor de Tráfico TCP con IA

Capturador de tráfico de red TCP con análisis de IA para detección de ransomware.

## Requisitos

- Python 3.11
- Poetry
- Permisos de administrador (sudo)

## Instalación

```bash
# Instalar dependencias
poetry install
```

## Uso

### Ejecución básica

```bash
sudo poetry run sensor --interface en0 --filter tcp
```

### Con modelo de IA

```bash
sudo poetry run sensor --interface en0 --filter tcp --model models/training/detection/convlstm_model_advtrained.keras
```

### Parámetros

- `--interface`: Interfaz de red (en macOS: `en0`, en Linux: `eth0`)
- `--filter`: Filtro de captura (por defecto: `tcp`)
- `--model`: Ruta al modelo .keras (opcional)

### Ejemplos

```bash
# Solo captura TCP
sudo poetry run sensor --interface en0

# Captura HTTPS con modelo
sudo poetry run sensor --interface en0 --filter "tcp and port 443" --model models/training/detection/convlstm_model_advtrained.keras

# Captura específica
sudo poetry run sensor --interface en0 --filter "tcp and host 8.8.8.8"
```

## Detener

Presiona `Ctrl+C` para detener la captura de forma segura.

## Interfaces de red

### macOS

```bash
ifconfig -l  # Ver interfaces disponibles
ifconfig en0 # Ver detalles de en0
```

### Linux

```bash
ip link show  # Ver interfaces disponibles
ip addr show  # Ver detalles
```

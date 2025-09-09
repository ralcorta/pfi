# AI for Ransomware Detection

```sh
poetry run pip install tensorflow==2.15.0 scikit-learn
```

## Configuración del Proyecto

Este proyecto utiliza Poetry para la gestión de dependencias y entornos virtuales.

### Prerrequisitos

- Python 3.11+
- Poetry (instalar desde [poetry.python.org](https://python-poetry.org/docs/#installation))

### Instalación

1. **Instalar Poetry** (si no está instalado):

```sh
curl -sSL https://install.python-poetry.org | python3 -
```

2. **Instalar dependencias del proyecto**:

```sh
poetry install
```

3. **Instalar dependencias de desarrollo** (opcional):

```sh
poetry install --with dev
```

### Uso

**Activar el entorno virtual**:

```sh
poetry shell
```

**Ejecutar comandos sin activar el shell**:

```sh
poetry run python script.py
```

**Usar Makefile para comandos comunes**:

```sh
make install          # Instalar dependencias
make shell            # Activar entorno virtual
make sensor-live      # Monitoreo en vivo de ransomware
make train-all        # Entrenar modelo completo
make format           # Formatear código
make lint             # Verificar estilo de código
```

### Estructura del Proyecto

```
pfi/
├── models/                    # Modelos y entrenamiento
│   ├── convlstm_model.keras   # Modelo principal
│   ├── data/                  # Datos de entrenamiento
│   └── training/              # Scripts de entrenamiento
│       ├── detection/         # Entrenamiento normal
│       └── ofuscacion/        # Entrenamiento adversarial
├── app/                       # Aplicaciones
│   └── sensor/                # Sensor de ransomware
└── pyproject.toml             # Configuración única
```

### Comandos Disponibles

- `make install` - Instalar dependencias
- `make shell` - Activar entorno virtual
- `make sensor-live` - Monitoreo en vivo de ransomware
- `make sensor-pcap` - Análisis de archivos PCAP
- `make train` - Entrenar modelo
- `make evaluate` - Evaluar modelo
- `make train-all` - Pipeline completo de entrenamiento
- `make train-adversarial-all` - Pipeline completo adversarial
- `make format` - Formatear código con Black
- `make lint` - Verificar estilo con Flake8
- `make type-check` - Verificar tipos con MyPy
- `make test` - Ejecutar tests
- `make help` - Mostrar ayuda completa

### Configuración con pyenv (opcional)

Si usas pyenv para gestionar versiones de Python:

```sh
echo -e 'export PYENV_ROOT="$HOME/.pyenv"\nexport PATH="$PYENV_ROOT/bin:$PATH"\neval "$(pyenv init --path)"\neval "$(pyenv init -)"\neval "$(pyenv virtualenv-init -)"' >> ~/.zshrc
source ~/.zshrc
pyenv install 3.11.0
pyenv local 3.11.0
```

---

# USTC-TFC2016

[yungshenglu/USTC-TK2016](https://github.com/yungshenglu/USTC-TK2016).

> **NOTICE:** This repository credits to [echowei/DeepTraffic](https://github.com/echowei/DeepTraffic)

## Description

```
Benign/
    ├── BitTorrent.pcap
    ├── Facetime.pcap
    ├── FTP.7z
    ├── Gmail.pcap
    ├── MySQL.pcap
    ├── Outlook.pcap
    ├── Skype.pcap
    ├── SMB.7z
    ├── Weibo.7z
    └── WorldOfWarcraft.pcap
Malware/
    ├── Cridex.7z
    ├── Geodo.7z
    ├── Htbot.7z
    ├── Miuref.pcap
    ├── Neris.7z
    ├── Nsis-ay.7z
    ├── Shifu.7z
    ├── Tinba.pcap
    ├── Virut.7z
    └── Zeus.pcap
```

---

## Ejecutar DEMOs

Para ejecutar una demo sobre los malware podemos uar el demo_detector.py:

```bash
poetry run python demo_detector.py --benign models/data/backup/Benign/Gmail.pcap --malicious models/data/backup/Malware/Zeus.pcap --delay 0
```

O si queremos sniffear la red local podemos usar:

```bash
sudo poetry run python simple_sniffer.py
```

---

## Contributor

- [Wei Wang](https://github.com/echowei) - ww8137@mail.ustc.edu.cn
- [David Lu](https://github.com/yungshenglu)

---

## License

[Mozilla Public License Version 2.0](LICENSE)

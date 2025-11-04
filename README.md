# Sistema de Detección de Ransomware con IA

Sistema de análisis de tráfico de red en tiempo real para la detección de ransomware y malware mediante aprendizaje automático. Utiliza AWS Traffic Mirroring para capturar tráfico de red sin afectar la operación de los servicios del cliente.

## 📦 Recursos Adicionales

- **Repositorio GitHub**: https://github.com/ralcorta/pfi
- **Videos de demostración y archivos del proyecto**: https://drive.google.com/drive/folders/1xqW6cRqagOp2BbrXrzVPfCTuTyXFAqAH?usp=sharing

## Documentación

### Documentación de Despliegue

La guía completa para desplegar la infraestructura en AWS se encuentra en:

**📄 [`docs/GUIA_DEPLOY.md`](docs/GUIA_DEPLOY.md)**

Esta guía incluye:

- Prerrequisitos y configuración inicial
- Métodos de despliegue (automatizado con scripts o manual con Terraform)
- Instrucciones paso a paso para desplegar el analizador y los clientes
- Configuración de variables y outputs importantes
- Troubleshooting y consideraciones adicionales

### Documentación de Arquitectura

La documentación completa de la arquitectura del sistema, componentes y flujo de datos se encuentra en:

**📄 [`docs/ARQUITECTURA.md`](docs/ARQUITECTURA.md)**

Este documento explica:

- Visión general del sistema y componentes principales
- Flujo de comunicación entre VPCs del analizador y clientes
- Tecnologías utilizadas (VXLAN, AWS Traffic Mirroring, ECS Fargate)
- Seguridad y aislamiento por cliente
- Escalabilidad y consideraciones de rendimiento

## Estructura del Proyecto

```
pfi/
├── app/
│   └── sensor/                    # Código del sensor de análisis
│       ├── model/                 # Modelos de ML pre-entrenados
│       ├── src/                   # Código fuente de la Aplicación
│       └── run.py                 # Punto de entrada del sensor
│
├── dashboard/                      # Frontend Vue.js
│   ├── src/                       # Código fuente del dashboard
│   ├── dist/                      # Build de producción
│   └── package.json               # Dependencias Node.js
│
├── models/                         # Modelos de Machine Learning
│   ├── training/
│   │   ├── detection/             # Scripts de entrenamiento del detector
│   │   ├── ofuscacion/            # Entrenamiento adversarial
│   │   └── adversarial-reinforcement/  # Reinforcement learning adversarial
│   ├── data/                      # Datasets y scripts de procesamiento
│   └── *.keras                    # Modelos entrenados
│
├── terraform/                     # Infraestructura como código
│   ├── analizer/                  # Módulo Terraform para el analizador
│   │   ├── main.tf
│   │   ├── variables.tf
│   │   └── terraform.tfvars
│   └── client/                    # Módulo Terraform para clientes
│       ├── main.tf
│       ├── variables.tf
│       └── terraform.tfvars
│
├── scripts/                        # Scripts de automatización
│
├── docs/                          # Documentación
│   ├── GUIA_DEPLOY.md             # Guía de despliegue
│   └── ARQUITECTURA.md            # Documentación de arquitectura
│
├── dockerfile                      # Dockerfile para el contenedor del sensor
├── docker-compose.yml              # Configuración Docker Compose (desarrollo)
├── Makefile                        # Comandos útiles para desarrollo
├── pyproject.toml                  # Configuración Poetry y dependencias Python
└── README.md
```

### Componentes Principales

#### 1. **Sensor de Análisis** (`app/sensor/`)

Aplicación FastAPI que:

- Recibe tráfico espejado encapsulado en VXLAN (puerto UDP 4789)
- Desencapsula el tráfico y analiza paquetes de red
- Detecta patrones de ransomware/malware usando modelos de ML
- Almacena detecciones en DynamoDB
- Expone API REST para consultas y gestión (puerto 8080)

#### 2. **Dashboard Frontend** (`dashboard/`)

Aplicación web Vue.js que:

- Visualiza detecciones
- Gestiona usuarios y autenticación (JWT)
- Permite registro de nuevos clientes
- Se sirve estáticamente desde S3

#### 3. **Modelos de ML** (`models/`)

- Scripts de entrenamiento de modelos de detección
- Entrenamiento adversarial para robustez
- Modelos pre-entrenados en formato Keras (.keras)

#### 4. **Infraestructura** (`terraform/`)

- Módulo Analizador
- Módulo Cliente

#### 5. **Scripts de Automatización** (`scripts/`)

Scripts Bash que automatizan:

- Despliegue de infraestructura con Terraform
- Construcción y push de imágenes Docker
- Despliegue del dashboard
- Configuración de Traffic Mirroring

## Inicio Rápido

### Prerrequisitos

- Python 3.10-3.11
- Poetry (gestor de dependencias)
- Docker
- AWS CLI configurado
- Terraform >= 1.0
- Node.js y npm (para el dashboard)

### Instalación

```bash
# Instalar dependencias Python
poetry install

# Activar entorno virtual
poetry shell
```

### Despliegue

Para más detalles, consulta la [Guía de Despliegue](docs/GUIA_DEPLOY.md).

## Tecnologías Utilizadas

- **Backend**: Python, FastAPI, Scapy, TensorFlow/Keras
- **Frontend**: Vue.js, TypeScript
- **Infraestructura**: AWS (ECS Fargate, VPC, Traffic Mirroring, Transit Gateway, S3, DynamoDB)
- **IaC**: Terraform
- **Contenedores**: Docker
- **Protocolos**: VXLAN, TCP/UDP

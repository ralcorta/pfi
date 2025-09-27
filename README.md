# 🛡️ AI Ransomware Detection System

Sistema avanzado de detección de ransomware basado en inteligencia artificial que utiliza análisis de tráfico de red en tiempo real con modelos de deep learning.

## 📋 Tabla de Contenidos

- [Características](#-características)
- [Prerrequisitos](#-prerrequisitos)
- [Instalación](#-instalación)
- [Configuración](#-configuración)
- [Uso Local](#-uso-local)
- [Despliegue en AWS](#-despliegue-en-aws)
- [Comandos Disponibles](#-comandos-disponibles)
- [Estructura del Proyecto](#-estructura-del-proyecto)
- [Monitoreo y Logs](#-monitoreo-y-logs)
- [Troubleshooting](#-troubleshooting)
- [Contribución](#-contribución)
- [Licencia](#-licencia)

## ✨ Características

- **🔍 Detección en Tiempo Real**: Análisis de tráfico de red en vivo
- **🤖 Modelos de Deep Learning**: Convolutional LSTM para detección avanzada
- **☁️ Despliegue en AWS**: Infraestructura escalable con ECS, SageMaker y Terraform
- **📊 Monitoreo Completo**: Logs, métricas y alertas integradas
- **🔄 CI/CD Automatizado**: Pipeline completo con GitHub Actions
- **🐳 Containerización**: Docker para despliegue consistente
- **📈 Auto-scaling**: Escalado automático basado en CPU
- **🔒 Seguridad**: VPC privada, security groups y encriptación

## 🔧 Prerrequisitos

### Sistema Local

- **Python 3.11+**
- **Poetry** ([poetry.python.org](https://python-poetry.org/docs/#installation))
- **Docker** (para containerización)
- **AWS CLI** (para despliegue)
- **Terraform 1.6+** (para infraestructura)
- **Git** (para control de versiones)

### AWS Academy

- **Cuenta de AWS Academy** con créditos disponibles
- **Permisos IAM** para crear recursos ECS, SageMaker, ECR, etc.
- **Región**: us-east-1 (recomendado)

## 📦 Instalación

### 1. Clonar el Repositorio

```bash
git clone <repository-url>
cd pfi
```

### 2. Instalar Poetry

```bash
# macOS/Linux
curl -sSL https://install.python-poetry.org | python3 -

# Windows (PowerShell)
(Invoke-WebRequest -Uri https://install.python-poetry.org -UseBasicParsing).Content | python -
```

### 3. Instalar Dependencias

```bash
# Instalar dependencias básicas
poetry install

# Instalar dependencias de desarrollo
poetry install --with dev
```

### 4. Configuración Inicial

```bash
# Configuración completa
make setup

# O paso a paso
make check-dependencies
make install-dev
make setup-aws
```

## ⚙️ Configuración

### Variables de Entorno

Crea un archivo `.env` en la raíz del proyecto:

```bash
# AWS Configuration
AWS_REGION=us-east-1
AWS_ACCOUNT_ID=339712899854

# ECR Configuration
ECR_REPOSITORY=mirror-sensor

# ECS Configuration
ECS_CLUSTER=mirror-cluster
ECS_SERVICE=mirror-sensor

# SageMaker Configuration
SAGEMAKER_ENDPOINT=sm-detector
MODEL_PATH=models/convlstm_model_ransomware_final.keras

# Environment
ENVIRONMENT=academy
```

### Configuración del Sensor

Edita `app/sensor/configs/sensor.yaml`:

```yaml
sensor:
  name: "ransomware-detector"
  version: "1.0.0"

capture:
  interface: "eth0"
  filter: "udp port 4789"
  buffer_size: 65536
  timeout: 1.0

model:
  endpoint_name: "sm-detector"
  region: "us-east-1"
  timeout: 30
  max_retries: 3

detection:
  threshold: 0.80
  batch_size: 100
  window_size: 1000

alerts:
  stdout:
    enabled: true
    format: "json"

  sqs:
    enabled: false
    queue_url: ""
    region: "us-east-1"

  sns:
    enabled: false
    topic_arn: ""
    region: "us-east-1"

logging:
  level: "INFO"
  format: "json"
  file: "/var/log/sensor.log"
```

## 🚀 Uso Local

### Desarrollo y Testing

```bash
# Activar entorno virtual
poetry shell

# Entrenar modelo
make train-all

# Ejecutar demo
make demo

# Monitoreo en vivo
make sensor-live

# Análisis de PCAP
make sensor-pcap PCAP_FILE=models/data/backup/Benign/Gmail.pcap

# Verificar código
make check-all
```

### Comandos de Desarrollo

```bash
# Formatear código
make format

# Linting
make lint

# Tests
make test

# Tests con coverage
make test-coverage
```

## ☁️ Despliegue en AWS

### 1. Configuración de AWS

```bash
# Configurar perfil AWS
export AWS_PROFILE=default
export AWS_DEFAULT_REGION=us-east-1

# Verificar identidad
aws sts get-caller-identity
```

### 2. Obtener Información de Infraestructura

```bash
# Obtener VPC por defecto
VPC_ID=$(aws ec2 describe-vpcs --filters "Name=is-default,Values=true" --query 'Vpcs[0].VpcId' --output text)
echo "VPC ID: $VPC_ID"

# Obtener subnets
aws ec2 describe-subnets --filters "Name=vpc-id,Values=$VPC_ID" --query 'Subnets[*].[SubnetId,AvailabilityZone,MapPublicIpOnLaunch]' --output table

# Obtener IP pública
MY_IP=$(curl -s ifconfig.me)
echo "Tu IP pública: $MY_IP"
```

### 3. Configurar Terraform

Edita `terraform/env/terraform.tfvars`:

```hcl
region = "us-east-1"
analyzer_vpc_id = "vpc-04f3ea9a31c5074e6"  # Tu VPC ID
analyzer_subnets = [
  "subnet-08183d25308a7b30d",
  "subnet-0dc22891c19569ebb",
  "subnet-0f5a6094224b28196",
  "subnet-0a51ede7059f05a4d",
  "subnet-06eea1669cf32203c",
  "subnet-00d8a8a7f5e57e86e"
]
container_image = "123456789012.dkr.ecr.us-east-1.amazonaws.com/mirror-sensor:latest"
sagemaker_endpoint = "sm-detector"
allowed_ingress_cidr = "131.229.145.26/32"  # Tu IP pública

tags = {
  Project = "NetMirror-ML"
  Env     = "academy"
}
```

### 4. Despliegue Completo

#### Opción A: Pipeline Automático

```bash
# Pipeline completo
make pipeline
```

#### Opción B: Paso a Paso

```bash
# 1. Desplegar infraestructura
make tf-init
make tf-apply

# 2. Crear y subir imagen Docker
make docker-build
make ecr-create
make ecr-push

# 3. Desplegar modelo a SageMaker
make deploy-model

# 4. Actualizar servicio ECS
make ecs-update
```

### 5. Verificar Despliegue

```bash
# Verificar estado del sistema
make health-check

# Ver logs
make logs

# Ver métricas
make metrics

# Verificar endpoint de SageMaker
make check-endpoint
```

## 📋 Comandos Disponibles

### Configuración y Entorno

```bash
make setup                    # Configuración inicial completa
make install                  # Instalar dependencias
make info                     # Ver información del proyecto
make help                     # Ver ayuda completa
```

### Entrenamiento de Modelos

```bash
make train-all                # Flujo completo de entrenamiento
make train                    # Solo entrenar modelo
make evaluate                 # Evaluar modelo
make train-adversarial-all    # Entrenamiento adversarial
```

### Detección y Sensor

```bash
make sensor-live              # Monitoreo en vivo
make sensor-pcap PCAP_FILE=archivo.pcap  # Análisis PCAP
make demo                     # Demo con archivos de ejemplo
make run-model                # Modelo standalone
```

### Docker y ECR

```bash
make docker-build             # Construir imagen
make ecr-push                 # Subir a ECR
make docker-run               # Ejecutar localmente
```

### SageMaker

```bash
make deploy-model             # Desplegar modelo
make check-endpoint           # Verificar endpoint
make test-endpoint            # Probar endpoint
```

### Terraform

```bash
make tf-apply                 # Desplegar infraestructura
make tf-plan                  # Ver plan
make tf-graph                 # Generar diagrama
```

### ECS

```bash
make ecs-update               # Actualizar servicio
make ecs-status               # Ver estado
make ecs-logs                 # Ver logs
```

### Pipelines

```bash
make pipeline                 # Pipeline completo
make pipeline-quick           # Pipeline rápido
make pipeline-model-only      # Solo modelo
```

### Testing y Calidad

```bash
make test                     # Ejecutar tests
make check-all                # Verificación completa
make format                   # Formatear código
make lint                     # Linting
```

### Monitoreo

```bash
make health-check             # Verificar salud del sistema
make logs                     # Ver logs
make metrics                  # Ver métricas
```

## 📁 Estructura del Proyecto

```
pfi/
├── app/ # Aplicaciones
│ └── sensor/ # Sensor de ransomware
│ ├── configs/ # Configuraciones
│ ├── src/ # Código fuente
│ │ ├── alerts/ # Sistemas de alertas
│ │ ├── core/ # Lógica principal
│ │ └── utils/ # Utilidades
│ └── test_sensor.py # Tests del sensor
├── models/ # Modelos y entrenamiento
│ ├── convlstm_model_ransomware_final.keras # Modelo principal
│ ├── data/ # Datos de entrenamiento
│ │ ├── backup/ # Datos de respaldo
│ │ └── traffic_dataset_full.csv
│ └── training/ # Scripts de entrenamiento
│ ├── detection/ # Entrenamiento normal
│ └── ofuscacion/ # Entrenamiento adversarial
├── terraform/ # Infraestructura como código
│ ├── env/ # Entorno de despliegue
│ │ ├── main.tf # Configuración principal
│ │ ├── variables.tf # Variables
│ │ ├── terraform.tfvars # Valores de variables
│ │ └── versions.tf # Versiones de providers
│ └── modules/ # Módulos de Terraform
│ ├── analyzer_service/ # Servicio de análisis
│ └── client_vpc/ # VPC cliente
├── scripts/ # Scripts de automatización
│ ├── deploy_model.py # Despliegue de modelo
│ └── test_endpoint.py # Pruebas de endpoint
├── .github/ # GitHub Actions
│ └── workflows/
│ └── ci-cd.yml # Pipeline CI/CD
├── Dockerfile # Imagen Docker
├── Makefile # Comandos automatizados
├── pyproject.toml # Configuración de Poetry
└── README.md # Este archivo
```

## 📊 Monitoreo y Logs

### CloudWatch Logs

```bash
# Ver logs en tiempo real
make logs

# Ver logs específicos
aws logs tail /aws/ecs/net-mirror-sensor --follow --region us-east-1
```

### Métricas de ECS

```bash
# Ver métricas de CPU
make metrics

# Ver estado del servicio
make ecs-status
```

### SageMaker Endpoint

```bash
# Verificar estado del endpoint
make check-endpoint

# Probar endpoint
make test-endpoint
```

### Health Check

```bash
# Verificar salud completa del sistema
make health-check
```

## 🔧 Troubleshooting

### Problemas Comunes

#### 1. Error de VPC Endpoint

```bash
# Error: InvalidServiceName
# Solución: Verificar que el servicio existe
aws ec2 describe-vpc-endpoint-services --region us-east-1 --query 'ServiceNames[?contains(@, `sagemaker`)]'
```

#### 2. Error de Permisos IAM

```bash
# Verificar permisos
aws sts get-caller-identity
aws iam list-attached-role-policies --role-name LabRole
```

#### 3. Error de Docker Build

```bash
# Limpiar cache de Docker
make docker-clean
make docker-build
```

#### 4. Error de Terraform

```bash
# Re-inicializar Terraform
make tf-destroy
make tf-init
make tf-apply
```

#### 5. Error de SageMaker

```bash
# Verificar que el modelo existe
make list-models

# Re-desplegar modelo
make delete-endpoint
make deploy-model
```

### Logs de Debugging

```bash
# Logs detallados del sensor
make sensor-live  # Con verbose logging

# Logs de ECS
make ecs-logs

# Logs de Terraform
cd terraform/env && terraform apply -var-file="terraform.tfvars" -auto-approve
```

### Comandos de Limpieza

```bash
# Limpiar Docker
make clean-docker

# Limpiar Terraform
make clean-terraform

# Limpiar SageMaker
make clean-sagemaker

# Limpiar todo (¡CUIDADO!)
make clean-all
```

## 💰 Costos Estimados

### Recursos AWS (por mes)

| Recurso               | Costo Estimado | Descripción                   |
| --------------------- | -------------- | ----------------------------- |
| ECS Fargate (1 task)  | ~$9            | CPU: 256, Memory: 512MB       |
| Network Load Balancer | ~$4.50         | Internal NLB                  |
| VPC Endpoint          | ~$7.50         | SageMaker Interface           |
| SageMaker Endpoint    | ~$50-200       | ml.t2.medium                  |
| CloudWatch Logs       | ~$1-2          | 7 días retención              |
| **Total**             | **~$72-223**   | Depende del tipo de instancia |

### Optimización de Costos

```bash
# Usar instancias más pequeñas
make deploy-model  # Usa ml.t2.medium por defecto

# Reducir retención de logs
# Editar terraform/modules/analyzer_service/main.tf
# retention_in_days = 1  # En lugar de 7

# Escalar a 0 cuando no se use
make ecs-scale COUNT=0
```

## 🤝 Contribución

### Flujo de Contribución

1. **Fork** el repositorio
2. **Crear** una rama para tu feature (`git checkout -b feature/nueva-funcionalidad`)
3. **Commit** tus cambios (`git commit -am 'Agregar nueva funcionalidad'`)
4. **Push** a la rama (`git push origin feature/nueva-funcionalidad`)
5. **Crear** un Pull Request

### Estándares de Código

```bash
# Verificar código antes de commit
make check-all

# Formatear código
make format

# Ejecutar tests
make test
```

### Estructura de Commits

feat: agregar nueva funcionalidad
fix: corregir bug en sensor
docs: actualizar documentación
test: agregar tests para nueva feature
refactor: refactorizar código existente

## 📄 Licencia

[Mozilla Public License Version 2.0](LICENSE)

---

## 🙏 Agradecimientos

- **Wei Wang** - [echowei/DeepTraffic](https://github.com/echowei/DeepTraffic)
- **David Lu** - [yungshenglu/USTC-TK2016](https://github.com/yungshenglu/USTC-TK2016)
- **USTC-TFC2016 Dataset** - Universidad de Ciencia y Tecnología de China

---

## 📞 Soporte

Para soporte técnico o preguntas:

1. **Issues**: Crear un issue en GitHub
2. **Documentación**: Revisar este README
3. **Logs**: Usar `make logs` para debugging
4. **Health Check**: Usar `make health-check` para diagnóstico

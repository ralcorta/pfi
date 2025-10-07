# 🚀 Guía de Deployment - Sistema de Detección de Malware

## 📋 Prerrequisitos

### 1. Herramientas Necesarias

```bash
# Instalar AWS CLI
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
sudo ./aws/install

# Instalar Terraform
wget https://releases.hashicorp.com/terraform/1.6.0/terraform_1.6.0_linux_amd64.zip
unzip terraform_1.6.0_linux_amd64.zip
sudo mv terraform /usr/local/bin/

# Instalar Poetry (Python)
curl -sSL https://install.python-poetry.org | python3 -
```

### 2. Configurar AWS CLI

```bash
aws configure
# AWS Access Key ID: [TU_ACCESS_KEY]
# AWS Secret Access Key: [TU_SECRET_KEY]
# Default region name: us-east-1
# Default output format: json
```

## 🔧 Configuración por Cuenta AWS

### Para AWS Academy (Temporal)

```bash
# Variables en terraform/env/terraform.tfvars
region          = "us-east-1"
analyzer_vpc_id = "vpc-01c47e35bacf9d921"  # VPC por defecto de Academy
analyzer_subnets = [
  "subnet-0394f1c697668afb6",
  "subnet-016ef34ab9b5d64f0",
  "subnet-0f84a9edb6e6164d3",
  "subnet-096dc00a35a9ebe82",
  "subnet-09de370d51e9b9b18",
  "subnet-00377007e619fdad5"
]
```

### Para Cuenta Personal/Producción

```bash
# 1. Obtener VPC y Subnets
aws ec2 describe-vpcs --query 'Vpcs[?IsDefault==`true`].[VpcId,CidrBlock]' --output table
aws ec2 describe-subnets --filters "Name=vpc-id,Values=vpc-XXXXXXXX" --query 'Subnets[*].[SubnetId,AvailabilityZone]' --output table

# 2. Actualizar terraform/env/terraform.tfvars
region          = "us-east-1"  # o tu región preferida
analyzer_vpc_id = "vpc-XXXXXXXX"  # Tu VPC por defecto
analyzer_subnets = [
  "subnet-XXXXXXXX",  # Tus subnets
  "subnet-YYYYYYYY",
  # ... más subnets
]
```

## 🏗️ Proceso de Deployment

### Paso 1: Preparar el Código

```bash
# Clonar el repositorio
git clone [TU_REPO_URL]
cd pfi

# Instalar dependencias
poetry install
```

### Paso 2: Configurar Variables de Entorno

```bash
# Crear archivo .env
cat > .env << EOF
AWS_DEFAULT_REGION=us-east-1
AWS_ACCESS_KEY_ID=tu_access_key
AWS_SECRET_ACCESS_KEY=tu_secret_key
ENVIRONMENT=aws
MODEL_PATH=/app/models/training/detection/convlstm_model_ransomware_final.keras
SAGEMAKER_ENDPOINT=sm-detector
ECS_CLUSTER=mirror-cluster
ECS_SERVICE=mirror-sensor
DYNAMODB_TABLE=demo-pcap-control
EOF
```

### Paso 3: Obtener Account ID y Configurar ECR

```bash
# Obtener Account ID
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
echo "Account ID: $ACCOUNT_ID"

# Crear repositorio ECR
aws ecr create-repository --repository-name mirror-sensor --region us-east-1

# Login a ECR
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin $ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com
```

### Paso 4: Actualizar Configuración de Terraform

```bash
# Actualizar terraform/env/terraform.tfvars con tu Account ID
container_image = "$ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/mirror-sensor:latest"
```

### Paso 5: Build y Push de la Imagen Docker

```bash
# Build de la imagen
make build

# Push a ECR
make push-ecr
```

### Paso 6: Deploy de la Infraestructura

```bash
# Inicializar Terraform
cd terraform/env
terraform init

# Plan de deployment
terraform plan

# Aplicar cambios
terraform apply -auto-approve
```

### Paso 7: Inicializar la Aplicación

```bash
# Volver al directorio raíz
cd ../..

# Configurar registros base en DynamoDB
ENVIRONMENT=aws poetry run python scripts/setup_aws_records.py
```

### Paso 8: Verificar Deployment

```bash
# Verificar estado de ECS
make check-aws-status

# Obtener URL del ALB
terraform output alb_dns
```

## 🌐 Acceso a la Aplicación

### URLs Públicas (después del deploy)

```bash
# Health Check
http://[ALB_DNS]/health

# Ver detecciones
http://[ALB_DNS]/detections

# Configuración demo
http://[ALB_DNS]/demo
```

## 🔄 Cambios Entre Cuentas AWS

### 1. Cambiar Account ID

```bash
# Obtener nuevo Account ID
NEW_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

# Actualizar terraform/env/terraform.tfvars
sed -i "s/[0-9]*\.dkr\.ecr\.us-east-1\.amazonaws\.com/$NEW_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/g" terraform/env/terraform.tfvars
```

### 2. Cambiar VPC y Subnets

```bash
# Obtener VPC por defecto
aws ec2 describe-vpcs --query 'Vpcs[?IsDefault==`true`].VpcId' --output text

# Obtener subnets
aws ec2 describe-subnets --filters "Name=vpc-id,Values=vpc-XXXXXXXX" --query 'Subnets[*].SubnetId' --output text
```

### 3. Recrear ECR Repository

```bash
# Eliminar repositorio anterior (si existe)
aws ecr delete-repository --repository-name mirror-sensor --force

# Crear nuevo repositorio
aws ecr create-repository --repository-name mirror-sensor
```

## 🧹 Limpieza (Destroy)

### Para AWS Academy (antes de que expire)

```bash
cd terraform/env
terraform destroy -auto-approve
```

### Para Cuenta Personal

```bash
# Eliminar recursos de ECR
aws ecr delete-repository --repository-name mirror-sensor --force

# Destroy de Terraform
cd terraform/env
terraform destroy -auto-approve
```

## 📝 Checklist de Deployment

- [ ] AWS CLI configurado
- [ ] Terraform instalado
- [ ] Poetry instalado
- [ ] Variables de entorno configuradas
- [ ] VPC y subnets identificadas
- [ ] ECR repository creado
- [ ] Imagen Docker build y push
- [ ] Terraform apply exitoso
- [ ] Aplicación inicializada
- [ ] Endpoints accesibles

## 🚨 Troubleshooting

### Error: "VPC not found"

```bash
# Verificar VPC ID
aws ec2 describe-vpcs --query 'Vpcs[*].[VpcId,IsDefault]' --output table
```

### Error: "ECR repository not found"

```bash
# Crear repositorio ECR
aws ecr create-repository --repository-name mirror-sensor
```

### Error: "ECS task not starting"

```bash
# Verificar logs
aws logs tail /aws/ecs/net-mirror-sensor --follow
```

### Error: "ALB not accessible"

```bash
# Verificar que el ALB sea público
aws elbv2 describe-load-balancers --query 'LoadBalancers[?LoadBalancerName==`sensor-api-alb`].Scheme' --output text
```

## 📞 Comandos Útiles

```bash
# Ver estado de ECS
aws ecs describe-services --cluster mirror-cluster --services mirror-sensor

# Ver logs en tiempo real
aws logs tail /aws/ecs/net-mirror-sensor --follow

# Ver outputs de Terraform
terraform output

# Forzar nuevo deployment de ECS
aws ecs update-service --cluster mirror-cluster --service mirror-sensor --force-new-deployment
```

---

**Nota:** Esta guía asume que estás usando la VPC por defecto de AWS. Para producción, considera crear una VPC dedicada con subnets públicas y privadas apropiadas.

#!/bin/bash

# 🚀 Script de Configuración Automática para Nueva Cuenta AWS
# Este script automatiza la configuración inicial para una nueva cuenta AWS

set -e

echo "🚀 Configurando infraestructura para nueva cuenta AWS..."

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Función para imprimir mensajes
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Verificar que AWS CLI esté configurado
check_aws_cli() {
    print_status "Verificando configuración de AWS CLI..."
    
    if ! aws sts get-caller-identity > /dev/null 2>&1; then
        print_error "AWS CLI no está configurado o las credenciales son inválidas"
        print_status "Ejecuta: aws configure"
        exit 1
    fi
    
    print_success "AWS CLI configurado correctamente"
}

# Obtener información de la cuenta
get_account_info() {
    print_status "Obteniendo información de la cuenta AWS..."
    
    ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
    REGION=$(aws configure get region)
    
    if [ -z "$REGION" ]; then
        REGION="us-east-1"
        print_warning "Región no configurada, usando us-east-1 por defecto"
    fi
    
    print_success "Account ID: $ACCOUNT_ID"
    print_success "Región: $REGION"
}

# Obtener VPC por defecto
get_default_vpc() {
    print_status "Obteniendo VPC por defecto..."
    
    VPC_ID=$(aws ec2 describe-vpcs --query 'Vpcs[?IsDefault==`true`].VpcId' --output text)
    
    if [ -z "$VPC_ID" ]; then
        print_error "No se encontró VPC por defecto"
        print_status "Creando VPC por defecto..."
        aws ec2 create-default-vpc
        VPC_ID=$(aws ec2 describe-vpcs --query 'Vpcs[?IsDefault==`true`].VpcId' --output text)
    fi
    
    print_success "VPC ID: $VPC_ID"
}

# Obtener subnets
get_subnets() {
    print_status "Obteniendo subnets de la VPC..."
    
    SUBNETS=$(aws ec2 describe-subnets --filters "Name=vpc-id,Values=$VPC_ID" --query 'Subnets[*].SubnetId' --output text)
    SUBNET_ARRAY=($SUBNETS)
    
    if [ ${#SUBNET_ARRAY[@]} -eq 0 ]; then
        print_error "No se encontraron subnets en la VPC"
        exit 1
    fi
    
    print_success "Subnets encontradas: ${#SUBNET_ARRAY[@]}"
    for subnet in "${SUBNET_ARRAY[@]}"; do
        print_status "  - $subnet"
    done
}

# Crear repositorio ECR
create_ecr_repository() {
    print_status "Creando repositorio ECR..."
    
    if aws ecr describe-repositories --repository-names mirror-sensor > /dev/null 2>&1; then
        print_warning "Repositorio ECR 'mirror-sensor' ya existe"
    else
        aws ecr create-repository --repository-name mirror-sensor --region $REGION
        print_success "Repositorio ECR creado"
    fi
}

# Actualizar archivo de configuración de Terraform
update_terraform_config() {
    print_status "Actualizando configuración de Terraform..."
    
    # Crear backup del archivo original
    cp terraform/env/terraform.tfvars terraform/env/terraform.tfvars.backup
    
    # Crear nuevo archivo de configuración
    cat > terraform/env/terraform.tfvars << EOF
region          = "$REGION"
analyzer_vpc_id = "$VPC_ID"
analyzer_subnets = [
$(for subnet in "${SUBNET_ARRAY[@]}"; do echo "  \"$subnet\","; done)
]
container_image      = "$ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/mirror-sensor:latest"
sagemaker_endpoint   = "sm-detector"
allowed_ingress_cidr = "0.0.0.0/0"

tags = {
  Project = "NetMirror-ML"
  Env     = "production"
}
EOF
    
    print_success "Configuración de Terraform actualizada"
}

# Actualizar archivo .env
update_env_file() {
    print_status "Actualizando archivo .env..."
    
    cat > .env << EOF
AWS_DEFAULT_REGION=$REGION
ENVIRONMENT=aws
MODEL_PATH=/app/models/training/detection/convlstm_model_ransomware_final.keras
SAGEMAKER_ENDPOINT=sm-detector
ECS_CLUSTER=mirror-cluster
ECS_SERVICE=mirror-sensor
DYNAMODB_TABLE=demo-pcap-control
EOF
    
    print_success "Archivo .env actualizado"
}

# Login a ECR
login_ecr() {
    print_status "Haciendo login a ECR..."
    
    aws ecr get-login-password --region $REGION | docker login --username AWS --password-stdin $ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com
    
    print_success "Login a ECR exitoso"
}

# Build y push de la imagen
build_and_push() {
    print_status "Construyendo y subiendo imagen Docker..."
    
    # Build
    docker build -t mirror-sensor .
    
    # Tag
    docker tag mirror-sensor:latest $ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/mirror-sensor:latest
    
    # Push
    docker push $ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/mirror-sensor:latest
    
    print_success "Imagen Docker construida y subida"
}

# Inicializar Terraform
init_terraform() {
    print_status "Inicializando Terraform..."
    
    cd terraform/env
    terraform init
    cd ../..
    
    print_success "Terraform inicializado"
}

# Deploy de la infraestructura
deploy_infrastructure() {
    print_status "Desplegando infraestructura..."
    
    cd terraform/env
    terraform plan
    echo ""
    read -p "¿Continuar con el deployment? (y/N): " -n 1 -r
    echo ""
    
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        terraform apply -auto-approve
        print_success "Infraestructura desplegada"
    else
        print_warning "Deployment cancelado"
        exit 0
    fi
    
    cd ../..
}

# Inicializar aplicación
init_application() {
    print_status "Inicializando aplicación..."
    
    ENVIRONMENT=aws poetry run python scripts/setup_aws_records.py
    
    print_success "Aplicación inicializada"
}

# Mostrar información final
show_final_info() {
    print_success "🎉 Configuración completada!"
    echo ""
    echo "📋 Información de la cuenta:"
    echo "  - Account ID: $ACCOUNT_ID"
    echo "  - Región: $REGION"
    echo "  - VPC ID: $VPC_ID"
    echo ""
    echo "🌐 URLs de acceso:"
    ALB_DNS=$(cd terraform/env && terraform output -raw alb_dns 2>/dev/null || echo "No disponible")
    if [ "$ALB_DNS" != "No disponible" ]; then
        echo "  - Health Check: http://$ALB_DNS/health"
        echo "  - Detecciones: http://$ALB_DNS/detections"
        echo "  - Demo: http://$ALB_DNS/demo"
    else
        echo "  - Ejecuta 'terraform output alb_dns' para obtener la URL"
    fi
    echo ""
    echo "🔧 Comandos útiles:"
    echo "  - Ver estado: make check-aws-status"
    echo "  - Ver logs: aws logs tail /aws/ecs/net-mirror-sensor --follow"
    echo "  - Destroy: cd terraform/env && terraform destroy"
}

# Función principal
main() {
    echo "🚀 Configuración Automática para Nueva Cuenta AWS"
    echo "=================================================="
    echo ""
    
    check_aws_cli
    get_account_info
    get_default_vpc
    get_subnets
    create_ecr_repository
    update_terraform_config
    update_env_file
    login_ecr
    build_and_push
    init_terraform
    deploy_infrastructure
    init_application
    show_final_info
}

# Ejecutar script
main "$@"
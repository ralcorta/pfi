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


# Actualizar archivo de configuración de Terraform
update_terraform_config() {
    print_status "Verificando configuración de Terraform..."
    
    # Verificar que terraform.tfvars existe y está configurado
    if [ ! -f "terraform/terraform.tfvars" ]; then
        print_error "terraform/terraform.tfvars no encontrado"
        exit 1
    fi
    
    # Verificar que la cuenta sea la correcta
    if ! grep -q "339712899854" terraform/terraform.tfvars; then
        print_warning "terraform/terraform.tfvars no está configurado para la cuenta 339712899854"
    fi
    
    print_success "Configuración de Terraform verificada"
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
build_docker() {
    print_status "Construyendo y subiendo imagen Docker..."
    
    # El repositorio se crea con Terraform, pero necesitamos esperar a que esté listo
    # Por ahora solo construimos la imagen localmente
    docker build -t mirror-sensor .
    
    print_success "Imagen Docker construida (push se hará después del deployment de Terraform)"
}

# Inicializar Terraform
init_terraform() {
    print_status "Inicializando Terraform..."
    
    cd terraform
    terraform init
    cd ..
    
    print_success "Terraform inicializado"
}

# Deploy de la infraestructura
deploy_infrastructure() {
    print_status "Desplegando infraestructura..."
    
    cd terraform
    terraform plan -var-file="terraform.tfvars"
    echo ""
    read -p "¿Continuar con el deployment? (y/N): " -n 1 -r
    echo ""
    
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        terraform apply -var-file="terraform.tfvars" -auto-approve
        print_success "Infraestructura desplegada"
    else
        print_warning "Deployment cancelado"
        exit 0
    fi
    
    cd ..
}

# Push de la imagen después del deployment
push_image_after_terraform() {
    print_status "Subiendo imagen Docker al ECR..."
    
    # Obtener la URL del repositorio desde Terraform
    ECR_URL=$(cd terraform && terraform output -raw ecr_repository_url 2>/dev/null || echo "")
    
    if [ -z "$ECR_URL" ]; then
        print_error "No se pudo obtener la URL del repositorio ECR"
        return 1
    fi
    
    # Tag y push
    docker tag mirror-sensor:latest $ECR_URL:latest
    docker push $ECR_URL:latest
    
    print_success "Imagen Docker subida al ECR"
}

# Inicializar aplicación
init_application() {
    print_status "Inicializando aplicación..."
    
    # Configurar variables de entorno para AWS
    export AWS_DEFAULT_REGION=us-east-1
    export DDB_TABLE=detections
    
    # Ejecutar setup de la aplicación
    python app/sensor/setup.py
    
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
    ALB_DNS=$(cd terraform && terraform output -raw alb_dns 2>/dev/null || echo "No disponible")
    if [ "$ALB_DNS" != "No disponible" ]; then
        echo "  - Health Check: http://$ALB_DNS/health"
        echo "  - Stats: http://$ALB_DNS/stats"
        echo "  - Detecciones: http://$ALB_DNS/detections/{tenant_id}"
    else
        echo "  - Ejecuta 'cd terraform && terraform output' para obtener las URLs"
    fi
    echo ""
    echo "🔧 Comandos útiles:"
    echo "  - Ver estado: cd terraform && terraform output"
    echo "  - Ver logs: aws logs tail /aws/ecs/sensor-app --follow"
    echo "  - Destroy: cd terraform && terraform destroy -var-file=\"terraform.tfvars\""
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
    update_terraform_config
    update_env_file
    login_ecr
    build_docker
    init_terraform
    deploy_infrastructure
    push_image_after_terraform
    # init_application
    show_final_info
}

# Ejecutar script
main "$@"
#!/bin/bash

# 🔄 Script de Reset Completo
# Este script borra TODO y lo vuelve a crear desde cero

set -e

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
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

print_step() {
    echo -e "${PURPLE}[STEP]${NC} $1"
}

# Verificar que estamos en el directorio correcto
check_directory() {
    if [ ! -f "pyproject.toml" ] || [ ! -d "terraform" ]; then
        print_error "Este script debe ejecutarse desde el directorio raíz del proyecto"
        exit 1
    fi
    print_success "Directorio correcto detectado"
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
    
    ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text 2>/dev/null)
    REGION=$(aws configure get region 2>/dev/null || echo "")
    
    if [ -z "$REGION" ]; then
        REGION="us-east-1"
        print_warning "Región no configurada, usando us-east-1 por defecto"
    fi
    
    if [ -z "$ACCOUNT_ID" ]; then
        print_error "No se pudo obtener Account ID"
        exit 1
    fi
    
    print_success "Account ID: $ACCOUNT_ID"
    print_success "Región: $REGION"
}

# Paso 1: Limpiar todo lo existente
cleanup_existing() {
    print_step "🧹 PASO 1: Limpiando recursos existentes..."
    
    # Obtener región para usar en cleanup
    local REGION=$(aws configure get region || echo "us-east-1")
    
    # Verificar si hay infraestructura desplegada
    if [ -d "terraform/env" ] && [ -f "terraform/env/terraform.tfstate" ]; then
        print_warning "Infraestructura existente detectada, destruyendo..."
        cd terraform/env
        
        # Inicializar Terraform si es necesario
        if [ ! -d ".terraform" ]; then
            print_status "Inicializando Terraform..."
            terraform init
        fi
        
        terraform destroy -auto-approve
        cd ../..
        print_success "Infraestructura destruida"
    else
        print_status "No se encontró infraestructura existente"
    fi
    
    # Eliminar repositorio ECR si existe
    if aws ecr describe-repositories --repository-names mirror-sensor > /dev/null 2>&1; then
        print_warning "Repositorio ECR existente detectado, eliminando..."
        aws ecr delete-repository --repository-name mirror-sensor --force --region $REGION
        print_success "Repositorio ECR eliminado"
    else
        print_status "No se encontró repositorio ECR existente"
    fi
    
    # Limpiar archivos de configuración
    if [ -f ".env" ]; then
        rm .env
        print_success "Archivo .env eliminado"
    fi
    
    if [ -f "terraform/env/terraform.tfvars.backup" ]; then
        rm terraform/env/terraform.tfvars.backup
        print_success "Backup de terraform.tfvars eliminado"
    fi
    
    if [ -d "terraform/env/.terraform" ]; then
        rm -rf terraform/env/.terraform
        print_success "Archivos temporales de Terraform eliminados"
    fi
    
    print_success "✅ Limpieza completada"
}

# Paso 2: Configurar nueva cuenta
setup_new_account() {
    print_step "🚀 PASO 2: Configurando nueva cuenta..."
    
    # Obtener VPC por defecto
    VPC_ID=$(aws ec2 describe-vpcs --query 'Vpcs[?IsDefault==`true`].VpcId' --output text)
    
    if [ -z "$VPC_ID" ]; then
        print_error "No se encontró VPC por defecto"
        print_status "Creando VPC por defecto..."
        aws ec2 create-default-vpc
        VPC_ID=$(aws ec2 describe-vpcs --query 'Vpcs[?IsDefault==`true`].VpcId' --output text)
    fi
    
    print_success "VPC ID: $VPC_ID"
    
    # Obtener subnets
    SUBNETS=$(aws ec2 describe-subnets --filters "Name=vpc-id,Values=$VPC_ID" --query 'Subnets[*].SubnetId' --output text)
    SUBNET_ARRAY=($SUBNETS)
    
    if [ ${#SUBNET_ARRAY[@]} -eq 0 ]; then
        print_error "No se encontraron subnets en la VPC"
        exit 1
    fi
    
    print_success "Subnets encontradas: ${#SUBNET_ARRAY[@]}"
    
    # Crear repositorio ECR
    print_status "Creando repositorio ECR..."
    aws ecr create-repository --repository-name mirror-sensor --region $REGION
    print_success "Repositorio ECR creado"
    
    # Actualizar configuración de Terraform
    print_status "Actualizando configuración de Terraform..."
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
    
    # Actualizar archivo .env
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
    
    print_success "✅ Configuración de cuenta completada"
}

# Paso 3: Build y push de imagen
build_and_push() {
    print_step "🐳 PASO 3: Construyendo y subiendo imagen Docker..."
    
    # Login a ECR
    print_status "Haciendo login a ECR..."
    aws ecr get-login-password --region $REGION | docker login --username AWS --password-stdin $ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com
    print_success "Login a ECR exitoso"
    
    # Build de la imagen
    print_status "Construyendo imagen Docker..."
    docker build -t mirror-sensor .
    print_success "Imagen construida"
    
    # Tag de la imagen
    print_status "Etiquetando imagen..."
    docker tag mirror-sensor:latest $ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/mirror-sensor:latest
    print_success "Imagen etiquetada"
    
    # Push de la imagen
    print_status "Subiendo imagen a ECR..."
    docker push $ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/mirror-sensor:latest
    print_success "Imagen subida a ECR"
    
    print_success "✅ Build y push completados"
}

# Paso 4: Deploy de infraestructura
deploy_infrastructure() {
    print_step "🏗️  PASO 4: Desplegando infraestructura..."
    
    # Inicializar Terraform
    print_status "Inicializando Terraform..."
    cd terraform/env
    terraform init
    print_success "Terraform inicializado"
    
    # Plan de deployment
    print_status "Generando plan de deployment..."
    terraform plan
    print_success "Plan generado"
    
    # Aplicar cambios
    print_status "Aplicando cambios de infraestructura..."
    terraform apply -auto-approve
    print_success "Infraestructura desplegada"
    
    cd ../..
    print_success "✅ Deploy de infraestructura completado"
}

# Paso 5: Inicializar aplicación
init_application() {
    print_step "⚙️  PASO 5: Inicializando aplicación..."
    
    # Esperar un poco para que ECS se estabilice
    print_status "Esperando que ECS se estabilice..."
    sleep 30
    
    # Inicializar registros base
    print_status "Configurando registros base en DynamoDB..."
    ENVIRONMENT=aws poetry run python scripts/setup_aws_records.py
    print_success "Registros base configurados"
    
    print_success "✅ Inicialización de aplicación completada"
}

# Paso 6: Verificar deployment
verify_deployment() {
    print_step "✅ PASO 6: Verificando deployment..."
    
    # Verificar estado de ECS
    print_status "Verificando estado de ECS..."
    ECS_STATUS=$(aws ecs describe-services --cluster mirror-cluster --services mirror-sensor --query 'services[0].runningCount' --output text)
    
    if [ "$ECS_STATUS" = "1" ]; then
        print_success "ECS Service ejecutándose correctamente"
    else
        print_warning "ECS Service no está ejecutándose correctamente (runningCount: $ECS_STATUS)"
    fi
    
    # Obtener URL del ALB
    print_status "Obteniendo URL del ALB..."
    ALB_DNS=$(cd terraform/env && terraform output -raw alb_dns 2>/dev/null || echo "No disponible")
    
    if [ "$ALB_DNS" != "No disponible" ]; then
        print_success "ALB DNS: $ALB_DNS"
        
        # Probar endpoint de health
        print_status "Probando endpoint de health..."
        sleep 10  # Esperar un poco más para que el ALB se propague
        
        if curl -s "http://$ALB_DNS/health" > /dev/null; then
            print_success "Endpoint de health respondiendo"
        else
            print_warning "Endpoint de health no responde aún (puede tardar unos minutos)"
        fi
    else
        print_warning "No se pudo obtener DNS del ALB"
    fi
    
    print_success "✅ Verificación completada"
}

# Mostrar información final
show_final_info() {
    echo ""
    echo "🎉 ¡RESET COMPLETO EXITOSO!"
    echo "=========================="
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
        echo "  - Info: http://$ALB_DNS/info"
    else
        echo "  - Ejecuta 'terraform output alb_dns' para obtener la URL"
    fi
    echo ""
    echo "🔧 Comandos útiles:"
    echo "  - Ver estado: make check-aws-status"
    echo "  - Ver logs: aws logs tail /aws/ecs/net-mirror-sensor --follow"
    echo "  - Reset completo: make reset-complete"
    echo "  - Limpiar todo: make cleanup-account"
    echo ""
    echo "⚠️  Nota: Los endpoints pueden tardar 2-3 minutos en estar completamente disponibles"
}

# Función principal
main() {
    echo ""
    echo "🔄 RESET COMPLETO DEL SISTEMA"
    echo "============================="
    echo ""
    echo "Este script va a:"
    echo "  1. 🧹 Borrar TODA la infraestructura existente"
    echo "  2. 🚀 Configurar la cuenta AWS desde cero"
    echo "  3. 🐳 Construir y subir nueva imagen Docker"
    echo "  4. 🏗️  Desplegar nueva infraestructura"
    echo "  5. ⚙️  Inicializar la aplicación"
    echo "  6. ✅ Verificar que todo funcione"
    echo ""
    print_warning "⚠️  ADVERTENCIA: Esto eliminará TODOS los recursos existentes"
    echo ""
    read -p "¿Continuar con el reset completo? (y/N): " -n 1 -r
    echo ""
    
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        print_warning "Reset cancelado"
        exit 0
    fi
    
    echo ""
    print_status "🚀 Iniciando reset completo..."
    echo ""
    
    check_directory
    check_aws_cli
    get_account_info
    
    cleanup_existing
    setup_new_account
    build_and_push
    deploy_infrastructure
    init_application
    verify_deployment
    show_final_info
}

# Ejecutar script
main "$@"

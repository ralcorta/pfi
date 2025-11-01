#!/bin/bash

# ========================================
# Script para actualizar terraform.tfvars con recursos existentes
# ========================================
# Este script busca recursos existentes y actualiza terraform.tfvars

set -e  # Exit on any error

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuración
PROJECT_NAME="pfi-sensor"
AWS_REGION="us-east-1"
ACCOUNT_ID="339712899854"
ENVIRONMENT="academy"

# Archivo de configuración
TFVARS_FILE="terraform/academy/terraform.tfvars"

# Función para logging
log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

success() {
    echo -e "${GREEN}✅ $1${NC}"
}

warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

error() {
    echo -e "${RED}❌ $1${NC}"
    exit 1
}

# Función para buscar VPC por nombre
find_vpc_by_name() {
    local vpc_name=$1
    local vpc_id=$(aws ec2 describe-vpcs \
        --filters "Name=tag:Name,Values=$vpc_name" "Name=state,Values=available" \
        --query 'Vpcs[0].VpcId' --output text 2>/dev/null)
    
    if [ "$vpc_id" = "None" ] || [ -z "$vpc_id" ]; then
        error "No se encontró VPC con nombre: $vpc_name"
    fi
    
    echo "$vpc_id"
}

# Función para buscar subnet por nombre y VPC
find_subnet_by_name() {
    local subnet_name=$1
    local vpc_id=$2
    local subnet_id=$(aws ec2 describe-subnets \
        --filters "Name=tag:Name,Values=$subnet_name" "Name=vpc-id,Values=$vpc_id" \
        --query 'Subnets[0].SubnetId' --output text 2>/dev/null)
    
    if [ "$subnet_id" = "None" ] || [ -z "$subnet_id" ]; then
        error "No se encontró subnet con nombre: $subnet_name en VPC: $vpc_id"
    fi
    
    echo "$subnet_id"
}

# Función para buscar ECR repository
find_ecr_repository() {
    local repo_name=$1
    if aws ecr describe-repositories --repository-names "$repo_name" &> /dev/null; then
        echo "$repo_name"
    else
        error "No se encontró ECR repository: $repo_name"
    fi
}

# Función para buscar ECS cluster
find_ecs_cluster() {
    local cluster_name=$1
    if aws ecs describe-clusters --clusters "$cluster_name" --query 'clusters[0].status' --output text 2>/dev/null | grep -q "ACTIVE"; then
        echo "$cluster_name"
    else
        error "No se encontró ECS cluster: $cluster_name"
    fi
}

# Función para buscar CloudWatch Log Group
find_log_group() {
    local log_group_name=$1
    local found=$(aws logs describe-log-groups --log-group-name-prefix "$log_group_name" --query 'logGroups[0].logGroupName' --output text 2>/dev/null)
    
    if [ "$found" = "None" ] || [ -z "$found" ]; then
        error "No se encontró CloudWatch Log Group: $log_group_name"
    fi
    
    echo "$found"
}

# Función para buscar Traffic Mirror Filter
find_traffic_mirror_filter() {
    local filter_name=$1
    local filter_id=$(aws ec2 describe-traffic-mirror-filters \
        --filters "Name=tag:Name,Values=$filter_name" \
        --query 'TrafficMirrorFilters[0].TrafficMirrorFilterId' --output text 2>/dev/null)
    
    if [ "$filter_id" = "None" ] || [ -z "$filter_id" ]; then
        error "No se encontró Traffic Mirror Filter: $filter_name"
    fi
    
    echo "$filter_id"
}

# Función para actualizar terraform.tfvars
update_tfvars() {
    local vpc_analizador_id=$1
    local vpc_cliente_id=$2
    local subnet_analizador_public_id=$3
    local subnet_analizador_private_id=$4
    local subnet_cliente_public_id=$5
    local subnet_cliente_private_id=$6
    local ecr_repo_name=$7
    local ecs_cluster_name=$8
    local log_group_name=$9
    local traffic_filter_id=${10}
    
    log "Actualizando terraform.tfvars..."
    
    # Crear backup
    cp "$TFVARS_FILE" "${TFVARS_FILE}.backup.$(date +%Y%m%d_%H%M%S)"
    
    # Actualizar archivo
    cat > "$TFVARS_FILE" << EOF
# Configuración para AWS Academy (Voclabs)
# Actualizado automáticamente el $(date)
# Usa recursos existentes encontrados en AWS

# Configuración general
aws_region   = "$AWS_REGION"
project_name = "$PROJECT_NAME"
environment  = "$ENVIRONMENT"
account_id   = "$ACCOUNT_ID"

# IDs de VPCs existentes (encontrados automáticamente)
existing_vpc_analizador_id = "$vpc_analizador_id"
existing_vpc_cliente_id    = "$vpc_cliente_id"

# IDs de subnets existentes (encontrados automáticamente)
existing_subnet_analizador_public_id  = "$subnet_analizador_public_id"
existing_subnet_analizador_private_id = "$subnet_analizador_private_id"
existing_subnet_cliente_public_id     = "$subnet_cliente_public_id"
existing_subnet_cliente_private_id    = "$subnet_cliente_private_id"

# Recursos existentes (encontrados automáticamente)
existing_ecr_repository_name      = "$ecr_repo_name"
existing_ecs_cluster_name         = "$ecs_cluster_name"
existing_cloudwatch_log_group_name = "$log_group_name"

# Availability Zones
availability_zone_1 = "us-east-1a"
availability_zone_2 = "us-east-1b"

# Configuración del sensor
sensor_instance_type = "t3.medium"
enable_public_access = false

# Tags
tags = {
  Project     = "PFI-Sensor"
  Environment = "$ENVIRONMENT"
  Owner       = "rodrigo"
  Account     = "$ACCOUNT_ID"
  Purpose     = "Ransomware Detection"
  Academy     = "AWS Academy"
  UpdatedBy   = "update_tfvars_from_existing.sh"
  UpdatedAt   = "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
}
EOF
    
    success "terraform.tfvars actualizado"
}

# Función principal
main() {
    log "🔍 Buscando recursos existentes en AWS..."
    
    # Verificar AWS CLI
    if ! command -v aws &> /dev/null; then
        error "AWS CLI no está instalado"
    fi
    
    if ! aws sts get-caller-identity &> /dev/null; then
        error "AWS CLI no está configurado o las credenciales no son válidas"
    fi
    
    success "AWS CLI configurado correctamente"
    
    # Buscar VPCs
    log "🔍 Buscando VPCs..."
    VPC_ANALIZADOR_ID=$(find_vpc_by_name "${PROJECT_NAME}-analizador-vpc")
    VPC_CLIENTE_ID=$(find_vpc_by_name "${PROJECT_NAME}-cliente-vpc")
    success "VPCs encontradas"
    
    # Buscar Subnets
    log "🔍 Buscando Subnets..."
    SUBNET_ANALIZADOR_PUBLIC_ID=$(find_subnet_by_name "${PROJECT_NAME}-analizador-public" "$VPC_ANALIZADOR_ID")
    SUBNET_ANALIZADOR_PRIVATE_ID=$(find_subnet_by_name "${PROJECT_NAME}-analizador-private" "$VPC_ANALIZADOR_ID")
    SUBNET_CLIENTE_PUBLIC_ID=$(find_subnet_by_name "${PROJECT_NAME}-cliente-public" "$VPC_CLIENTE_ID")
    SUBNET_CLIENTE_PRIVATE_ID=$(find_subnet_by_name "${PROJECT_NAME}-cliente-private" "$VPC_CLIENTE_ID")
    success "Subnets encontradas"
    
    # Buscar otros recursos
    log "🔍 Buscando otros recursos..."
    ECR_REPO_NAME=$(find_ecr_repository "mirror-sensor")
    ECS_CLUSTER_NAME=$(find_ecs_cluster "${PROJECT_NAME}-sensor-cluster")
    LOG_GROUP_NAME=$(find_log_group "/ecs/${PROJECT_NAME}-sensor")
    TRAFFIC_FILTER_ID=$(find_traffic_mirror_filter "${PROJECT_NAME}-cliente-filter")
    success "Otros recursos encontrados"
    
    # Actualizar terraform.tfvars
    update_tfvars \
        "$VPC_ANALIZADOR_ID" \
        "$VPC_CLIENTE_ID" \
        "$SUBNET_ANALIZADOR_PUBLIC_ID" \
        "$SUBNET_ANALIZADOR_PRIVATE_ID" \
        "$SUBNET_CLIENTE_PUBLIC_ID" \
        "$SUBNET_CLIENTE_PRIVATE_ID" \
        "$ECR_REPO_NAME" \
        "$ECS_CLUSTER_NAME" \
        "$LOG_GROUP_NAME" \
        "$TRAFFIC_FILTER_ID"
    
    # Resumen final
    log "🎉 ¡Actualización completada exitosamente!"
    echo ""
    echo "📋 Recursos encontrados:"
    echo "  • VPC Analizador: $VPC_ANALIZADOR_ID"
    echo "  • VPC Cliente: $VPC_CLIENTE_ID"
    echo "  • Subnets: 4 subnets encontradas"
    echo "  • ECR Repository: $ECR_REPO_NAME"
    echo "  • ECS Cluster: $ECS_CLUSTER_NAME"
    echo "  • CloudWatch Log Group: $LOG_GROUP_NAME"
    echo "  • Traffic Mirror Filter: $TRAFFIC_FILTER_ID"
    echo ""
    echo "🚀 Próximos pasos:"
    echo "  1. cd terraform/academy"
    echo "  2. terraform init"
    echo "  3. terraform plan"
    echo "  4. terraform apply"
    echo ""
    echo "📁 Backup de terraform.tfvars guardado como: ${TFVARS_FILE}.backup.*"
}

# Ejecutar función principal
main "$@"

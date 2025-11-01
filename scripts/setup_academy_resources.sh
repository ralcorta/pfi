#!/bin/bash

# ========================================
# Script para configurar recursos AWS Academy
# ========================================
# Este script crea los recursos necesarios manualmente y actualiza terraform.tfvars

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

# CIDR blocks
VPC_ANALIZADOR_CIDR="10.0.0.0/16"
VPC_CLIENTE_CIDR="10.1.0.0/16"
SUBNET_ANALIZADOR_PUBLIC_CIDR="10.0.1.0/24"
SUBNET_ANALIZADOR_PRIVATE_CIDR="10.0.2.0/24"
SUBNET_CLIENTE_PUBLIC_CIDR="10.1.1.0/24"
SUBNET_CLIENTE_PRIVATE_CIDR="10.1.2.0/24"

# Availability Zones
AZ1="us-east-1a"
AZ2="us-east-1b"

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

# Función para verificar si AWS CLI está configurado
check_aws_cli() {
    log "Verificando configuración de AWS CLI..."
    
    if ! command -v aws &> /dev/null; then
        error "AWS CLI no está instalado"
    fi
    
    if ! aws sts get-caller-identity &> /dev/null; then
        error "AWS CLI no está configurado o las credenciales no son válidas"
    fi
    
    success "AWS CLI configurado correctamente"
}

# Función para crear VPC
create_vpc() {
    local vpc_name=$1
    local cidr_block=$2
    local vpc_type=$3
    
    log "Creando VPC: $vpc_name ($cidr_block)"
    
    # Verificar si la VPC ya existe
    local existing_vpc=$(aws ec2 describe-vpcs \
        --filters "Name=tag:Name,Values=$vpc_name" "Name=state,Values=available" \
        --query 'Vpcs[0].VpcId' --output text 2>/dev/null)
    
    if [ "$existing_vpc" != "None" ] && [ -n "$existing_vpc" ]; then
        warning "VPC $vpc_name ya existe: $existing_vpc"
        echo "$existing_vpc"
        return
    fi
    
    # Crear VPC
    local vpc_id=$(aws ec2 create-vpc \
        --cidr-block "$cidr_block" \
        --tag-specifications "ResourceType=vpc,Tags=[{Key=Name,Value=$vpc_name},{Key=Environment,Value=$ENVIRONMENT},{Key=Project,Value=$PROJECT_NAME},{Key=Type,Value=$vpc_type},{Key=Purpose,Value=Ransomware-Detection}]" \
        --query 'Vpc.VpcId' --output text)
    
    # Habilitar DNS
    aws ec2 modify-vpc-attribute --vpc-id "$vpc_id" --enable-dns-hostnames
    aws ec2 modify-vpc-attribute --vpc-id "$vpc_id" --enable-dns-support
    
    success "VPC creada: $vpc_id"
    echo "$vpc_id"
}

# Función para crear Internet Gateway
create_igw() {
    local vpc_id=$1
    local igw_name=$2
    
    log "Creando Internet Gateway: $igw_name"
    
    # Verificar si ya existe
    local existing_igw=$(aws ec2 describe-internet-gateways \
        --filters "Name=attachment.vpc-id,Values=$vpc_id" \
        --query 'InternetGateways[0].InternetGatewayId' --output text 2>/dev/null)
    
    if [ "$existing_igw" != "None" ] && [ -n "$existing_igw" ]; then
        warning "Internet Gateway ya existe: $existing_igw"
        echo "$existing_igw"
        return
    fi
    
    # Crear IGW
    local igw_id=$(aws ec2 create-internet-gateway \
        --tag-specifications "ResourceType=internet-gateway,Tags=[{Key=Name,Value=$igw_name},{Key=Environment,Value=$ENVIRONMENT},{Key=Project,Value=$PROJECT_NAME},{Key=Type,Value=$vpc_name}]" \
        --query 'InternetGateway.InternetGatewayId' --output text)
    
    # Asociar a VPC
    aws ec2 attach-internet-gateway --vpc-id "$vpc_id" --internet-gateway-id "$igw_id"
    
    success "Internet Gateway creado: $igw_id"
    echo "$igw_id"
}

# Función para crear subnet
create_subnet() {
    local vpc_id=$1
    local subnet_name=$2
    local cidr_block=$3
    local az=$4
    local public=$5
    
    log "Creando subnet: $subnet_name ($cidr_block) en $az"
    
    # Verificar si la subnet ya existe
    local existing_subnet=$(aws ec2 describe-subnets \
        --filters "Name=tag:Name,Values=$subnet_name" "Name=vpc-id,Values=$vpc_id" \
        --query 'Subnets[0].SubnetId' --output text 2>/dev/null)
    
    if [ "$existing_subnet" != "None" ] && [ -n "$existing_subnet" ]; then
        warning "Subnet $subnet_name ya existe: $existing_subnet"
        echo "$existing_subnet"
        return
    fi
    
    # Crear subnet
    local subnet_id=$(aws ec2 create-subnet \
        --vpc-id "$vpc_id" \
        --cidr-block "$cidr_block" \
        --availability-zone "$az" \
        --tag-specifications "ResourceType=subnet,Tags=[{Key=Name,Value=$subnet_name},{Key=Environment,Value=$ENVIRONMENT},{Key=Project,Value=$PROJECT_NAME},{Key=Type,Value=$subnet_name}]" \
        --query 'Subnet.SubnetId' --output text)
    
    # Si es pública, habilitar auto-assign public IP
    if [ "$public" = "true" ]; then
        aws ec2 modify-subnet-attribute --subnet-id "$subnet_id" --map-public-ip-on-launch
    fi
    
    success "Subnet creada: $subnet_id"
    echo "$subnet_id"
}

# Función para crear ECR Repository
create_ecr_repository() {
    local repo_name=$1
    
    log "Creando ECR Repository: $repo_name"
    
    # Verificar si ya existe
    if aws ecr describe-repositories --repository-names "$repo_name" &> /dev/null; then
        warning "ECR Repository $repo_name ya existe"
        local repo_uri=$(aws ecr describe-repositories --repository-names "$repo_name" --query 'repositories[0].repositoryUri' --output text)
        echo "$repo_uri"
        return
    fi
    
    # Crear repository
    aws ecr create-repository \
        --repository-name "$repo_name" \
        --image-scanning-configuration scanOnPush=true \
        --region "$AWS_REGION"
    
    # Aplicar lifecycle policy
    aws ecr put-lifecycle-policy \
        --repository-name "$repo_name" \
        --lifecycle-policy-text '{
            "rules": [{
                "rulePriority": 1,
                "description": "Keep last 10 images",
                "selection": {
                    "tagStatus": "tagged",
                    "tagPrefixList": ["v"],
                    "countType": "imageCountMoreThan",
                    "countNumber": 10
                },
                "action": {
                    "type": "expire"
                }
            }]
        }' \
        --region "$AWS_REGION"
    
    local repo_uri=$(aws ecr describe-repositories --repository-names "$repo_name" --query 'repositories[0].repositoryUri' --output text)
    success "ECR Repository creado: $repo_uri"
    echo "$repo_uri"
}

# Función para crear ECS Cluster
create_ecs_cluster() {
    local cluster_name=$1
    
    log "Creando ECS Cluster: $cluster_name"
    
    # Verificar si ya existe
    if aws ecs describe-clusters --clusters "$cluster_name" --query 'clusters[0].status' --output text 2>/dev/null | grep -q "ACTIVE"; then
        warning "ECS Cluster $cluster_name ya existe"
        echo "$cluster_name"
        return
    fi
    
    # Crear cluster
    aws ecs create-cluster \
        --cluster-name "$cluster_name" \
        --settings name=containerInsights,value=enabled \
        --tags key=Name,value="$cluster_name" key=Environment,value="$ENVIRONMENT" key=Project,value="$PROJECT_NAME" key=Type,value="ECS-Cluster" \
        --region "$AWS_REGION"
    
    success "ECS Cluster creado: $cluster_name"
    echo "$cluster_name"
}

# Función para crear CloudWatch Log Group
create_log_group() {
    local log_group_name=$1
    
    log "Creando CloudWatch Log Group: $log_group_name"
    
    # Verificar si ya existe
    if aws logs describe-log-groups --log-group-name-prefix "$log_group_name" --query 'logGroups[0].logGroupName' --output text 2>/dev/null | grep -q "$log_group_name"; then
        warning "CloudWatch Log Group $log_group_name ya existe"
        echo "$log_group_name"
        return
    fi
    
    # Crear log group
    aws logs create-log-group \
        --log-group-name "$log_group_name" \
        --region "$AWS_REGION"
    
    # Establecer retención de 7 días
    aws logs put-retention-policy \
        --log-group-name "$log_group_name" \
        --retention-in-days 7 \
        --region "$AWS_REGION"
    
    success "CloudWatch Log Group creado: $log_group_name"
    echo "$log_group_name"
}

# Función para crear Traffic Mirror Filter
create_traffic_mirror_filter() {
    local filter_name=$1
    
    log "Creando Traffic Mirror Filter: $filter_name"
    
    # Verificar si ya existe
    local existing_filter=$(aws ec2 describe-traffic-mirror-filters \
        --filters "Name=tag:Name,Values=$filter_name" \
        --query 'TrafficMirrorFilters[0].TrafficMirrorFilterId' --output text 2>/dev/null)
    
    if [ "$existing_filter" != "None" ] && [ -n "$existing_filter" ]; then
        warning "Traffic Mirror Filter $filter_name ya existe: $existing_filter"
        echo "$existing_filter"
        return
    fi
    
    # Crear filter
    local filter_id=$(aws ec2 create-traffic-mirror-filter \
        --description "Traffic filter for client - TCP+UDP ingress/egress" \
        --tag-specifications "ResourceType=traffic-mirror-filter,Tags=[{Key=Name,Value=$filter_name},{Key=Environment,Value=$ENVIRONMENT},{Key=Project,Value=$PROJECT_NAME}]" \
        --query 'TrafficMirrorFilter.TrafficMirrorFilterId' --output text)
    
    # Crear reglas del filtro
    aws ec2 create-traffic-mirror-filter-rule \
        --traffic-mirror-filter-id "$filter_id" \
        --traffic-direction ingress \
        --rule-number 1 \
        --rule-action accept \
        --protocol 6 \
        --source-cidr-block 0.0.0.0/0 \
        --destination-cidr-block 0.0.0.0/0
    
    aws ec2 create-traffic-mirror-filter-rule \
        --traffic-mirror-filter-id "$filter_id" \
        --traffic-direction egress \
        --rule-number 2 \
        --rule-action accept \
        --protocol 6 \
        --source-cidr-block 0.0.0.0/0 \
        --destination-cidr-block 0.0.0.0/0
    
    aws ec2 create-traffic-mirror-filter-rule \
        --traffic-mirror-filter-id "$filter_id" \
        --traffic-direction ingress \
        --rule-number 3 \
        --rule-action accept \
        --protocol 17 \
        --source-cidr-block 0.0.0.0/0 \
        --destination-cidr-block 0.0.0.0/0
    
    aws ec2 create-traffic-mirror-filter-rule \
        --traffic-mirror-filter-id "$filter_id" \
        --traffic-direction egress \
        --rule-number 4 \
        --rule-action accept \
        --protocol 17 \
        --source-cidr-block 0.0.0.0/0 \
        --destination-cidr-block 0.0.0.0/0
    
    success "Traffic Mirror Filter creado: $filter_id"
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
    local ecr_repo_uri=$7
    local ecs_cluster_name=$8
    local log_group_name=$9
    local traffic_filter_id=${10}
    
    log "Actualizando terraform.tfvars..."
    
    # Crear backup
    cp "$TFVARS_FILE" "${TFVARS_FILE}.backup.$(date +%Y%m%d_%H%M%S)"
    
    # Actualizar archivo
    cat > "$TFVARS_FILE" << EOF
# Configuración para AWS Academy (Voclabs)
# Generado automáticamente el $(date)
# Usa recursos existentes creados manualmente en la consola

# Configuración general
aws_region   = "$AWS_REGION"
project_name = "$PROJECT_NAME"
environment  = "$ENVIRONMENT"
account_id   = "$ACCOUNT_ID"

# IDs de VPCs existentes (creados por este script)
existing_vpc_analizador_id = "$vpc_analizador_id"
existing_vpc_cliente_id    = "$vpc_cliente_id"

# IDs de subnets existentes (creados por este script)
existing_subnet_analizador_public_id  = "$subnet_analizador_public_id"
existing_subnet_analizador_private_id = "$subnet_analizador_private_id"
existing_subnet_cliente_public_id     = "$subnet_cliente_public_id"
existing_subnet_cliente_private_id    = "$subnet_cliente_private_id"

# Recursos existentes (creados por este script)
existing_ecr_repository_name      = "mirror-sensor"
existing_ecs_cluster_name         = "$ecs_cluster_name"
existing_cloudwatch_log_group_name = "$log_group_name"

# Availability Zones
availability_zone_1 = "$AZ1"
availability_zone_2 = "$AZ2"

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
  CreatedBy   = "setup_academy_resources.sh"
  CreatedAt   = "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
}
EOF
    
    success "terraform.tfvars actualizado"
}

# Función principal
main() {
    log "🚀 Iniciando configuración de recursos AWS Academy..."
    
    # Verificar AWS CLI
    check_aws_cli
    
    # Crear VPCs
    log "📡 Creando VPCs..."
    VPC_ANALIZADOR_ID=$(create_vpc "${PROJECT_NAME}-analizador-vpc" "$VPC_ANALIZADOR_CIDR" "Analizador")
    VPC_CLIENTE_ID=$(create_vpc "${PROJECT_NAME}-cliente-vpc" "$VPC_CLIENTE_CIDR" "Cliente-Ejemplo")
    
    # Crear Internet Gateways
    log "🌐 Creando Internet Gateways..."
    IGW_ANALIZADOR_ID=$(create_igw "$VPC_ANALIZADOR_ID" "${PROJECT_NAME}-analizador-igw")
    IGW_CLIENTE_ID=$(create_igw "$VPC_CLIENTE_ID" "${PROJECT_NAME}-cliente-igw")
    
    # Crear Subnets
    log "🏗️  Creando Subnets..."
    SUBNET_ANALIZADOR_PUBLIC_ID=$(create_subnet "$VPC_ANALIZADOR_ID" "${PROJECT_NAME}-analizador-public" "$SUBNET_ANALIZADOR_PUBLIC_CIDR" "$AZ1" "true")
    SUBNET_ANALIZADOR_PRIVATE_ID=$(create_subnet "$VPC_ANALIZADOR_ID" "${PROJECT_NAME}-analizador-private" "$SUBNET_ANALIZADOR_PRIVATE_CIDR" "$AZ2" "false")
    SUBNET_CLIENTE_PUBLIC_ID=$(create_subnet "$VPC_CLIENTE_ID" "${PROJECT_NAME}-cliente-public" "$SUBNET_CLIENTE_PUBLIC_CIDR" "$AZ1" "true")
    SUBNET_CLIENTE_PRIVATE_ID=$(create_subnet "$VPC_CLIENTE_ID" "${PROJECT_NAME}-cliente-private" "$SUBNET_CLIENTE_PRIVATE_CIDR" "$AZ2" "false")
    
    # Crear Route Tables y asociaciones
    log "🛣️  Creando Route Tables..."
    
    # Route Table para VPC Analizador (pública)
    RT_ANALIZADOR_PUBLIC_ID=$(aws ec2 create-route-table \
        --vpc-id "$VPC_ANALIZADOR_ID" \
        --tag-specifications "ResourceType=route-table,Tags=[{Key=Name,Value=${PROJECT_NAME}-analizador-public-rt},{Key=Environment,Value=$ENVIRONMENT},{Key=Project,Value=$PROJECT_NAME},{Key=Type,Value=Analizador-Public}]" \
        --query 'RouteTable.RouteTableId' --output text)
    
    # Agregar ruta por defecto
    aws ec2 create-route --route-table-id "$RT_ANALIZADOR_PUBLIC_ID" --destination-cidr-block 0.0.0.0/0 --gateway-id "$IGW_ANALIZADOR_ID"
    
    # Asociar subnet pública
    aws ec2 associate-route-table --subnet-id "$SUBNET_ANALIZADOR_PUBLIC_ID" --route-table-id "$RT_ANALIZADOR_PUBLIC_ID"
    
    # Route Table para VPC Cliente (pública)
    RT_CLIENTE_PUBLIC_ID=$(aws ec2 create-route-table \
        --vpc-id "$VPC_CLIENTE_ID" \
        --tag-specifications "ResourceType=route-table,Tags=[{Key=Name,Value=${PROJECT_NAME}-cliente-public-rt},{Key=Environment,Value=$ENVIRONMENT},{Key=Project,Value=$PROJECT_NAME},{Key=Type,Value=Cliente-Public}]" \
        --query 'RouteTable.RouteTableId' --output text)
    
    # Agregar ruta por defecto
    aws ec2 create-route --route-table-id "$RT_CLIENTE_PUBLIC_ID" --destination-cidr-block 0.0.0.0/0 --gateway-id "$IGW_CLIENTE_ID"
    
    # Asociar subnet pública
    aws ec2 associate-route-table --subnet-id "$SUBNET_CLIENTE_PUBLIC_ID" --route-table-id "$RT_CLIENTE_PUBLIC_ID"
    
    # Crear Route Tables privadas
    RT_ANALIZADOR_PRIVATE_ID=$(aws ec2 create-route-table \
        --vpc-id "$VPC_ANALIZADOR_ID" \
        --tag-specifications "ResourceType=route-table,Tags=[{Key=Name,Value=${PROJECT_NAME}-analizador-private-rt},{Key=Environment,Value=$ENVIRONMENT},{Key=Project,Value=$PROJECT_NAME},{Key=Type,Value=Analizador-Private}]" \
        --query 'RouteTable.RouteTableId' --output text)
    
    RT_CLIENTE_PRIVATE_ID=$(aws ec2 create-route-table \
        --vpc-id "$VPC_CLIENTE_ID" \
        --tag-specifications "ResourceType=route-table,Tags=[{Key=Name,Value=${PROJECT_NAME}-cliente-private-rt},{Key=Environment,Value=$ENVIRONMENT},{Key=Project,Value=$PROJECT_NAME},{Key=Type,Value=Cliente-Private}]" \
        --query 'RouteTable.RouteTableId' --output text)
    
    # Asociar subnets privadas
    aws ec2 associate-route-table --subnet-id "$SUBNET_ANALIZADOR_PRIVATE_ID" --route-table-id "$RT_ANALIZADOR_PRIVATE_ID"
    aws ec2 associate-route-table --subnet-id "$SUBNET_CLIENTE_PRIVATE_ID" --route-table-id "$RT_CLIENTE_PRIVATE_ID"
    
    success "Route Tables creadas y asociadas"
    
    # Crear ECR Repository
    log "🐳 Creando ECR Repository..."
    ECR_REPO_URI=$(create_ecr_repository "mirror-sensor")
    
    # Crear ECS Cluster
    log "☸️  Creando ECS Cluster..."
    ECS_CLUSTER_NAME=$(create_ecs_cluster "${PROJECT_NAME}-sensor-cluster")
    
    # Crear CloudWatch Log Group
    log "📊 Creando CloudWatch Log Group..."
    LOG_GROUP_NAME=$(create_log_group "/ecs/${PROJECT_NAME}-sensor")
    
    # Crear Traffic Mirror Filter
    log "🪞 Creando Traffic Mirror Filter..."
    TRAFFIC_FILTER_ID=$(create_traffic_mirror_filter "${PROJECT_NAME}-cliente-filter")
    
    # Actualizar terraform.tfvars
    log "📝 Actualizando terraform.tfvars..."
    update_tfvars \
        "$VPC_ANALIZADOR_ID" \
        "$VPC_CLIENTE_ID" \
        "$SUBNET_ANALIZADOR_PUBLIC_ID" \
        "$SUBNET_ANALIZADOR_PRIVATE_ID" \
        "$SUBNET_CLIENTE_PUBLIC_ID" \
        "$SUBNET_CLIENTE_PRIVATE_ID" \
        "$ECR_REPO_URI" \
        "$ECS_CLUSTER_NAME" \
        "$LOG_GROUP_NAME" \
        "$TRAFFIC_FILTER_ID"
    
    # Resumen final
    log "🎉 ¡Configuración completada exitosamente!"
    echo ""
    echo "📋 Resumen de recursos creados:"
    echo "  • VPC Analizador: $VPC_ANALIZADOR_ID"
    echo "  • VPC Cliente: $VPC_CLIENTE_ID"
    echo "  • Subnets: 4 subnets creadas"
    echo "  • ECR Repository: $ECR_REPO_URI"
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

#!/bin/bash

# 🧹 Script de Limpieza para Cuenta AWS
# Este script elimina todos los recursos creados por el deployment

set -e

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
    fi
    
    print_success "Account ID: $ACCOUNT_ID"
    print_success "Región: $REGION"
}

# Destruir infraestructura con Terraform
destroy_terraform() {
    print_status "Destruyendo infraestructura con Terraform..."
    
    if [ -d "terraform/env" ]; then
        cd terraform/env
        
        if [ -f "terraform.tfstate" ] || [ -f ".terraform/terraform.tfstate" ]; then
            print_warning "⚠️  ADVERTENCIA: Esto eliminará TODA la infraestructura desplegada"
            echo ""
            echo "Recursos que se eliminarán:"
            echo "  - ECS Cluster y Service"
            echo "  - Load Balancers (NLB y ALB)"
            echo "  - DynamoDB Table"
            echo "  - Security Groups"
            echo "  - CloudWatch Log Groups"
            echo "  - VPC Endpoints"
            echo ""
            read -p "¿Estás seguro de que quieres continuar? (y/N): " -n 1 -r
            echo ""
            
            if [[ $REPLY =~ ^[Yy]$ ]]; then
                terraform destroy -auto-approve
                print_success "Infraestructura destruida"
            else
                print_warning "Destrucción cancelada"
                cd ../..
                return 1
            fi
        else
            print_warning "No se encontró estado de Terraform, saltando destrucción"
        fi
        
        cd ../..
    else
        print_warning "Directorio terraform/env no encontrado"
    fi
}

# Eliminar repositorio ECR
delete_ecr_repository() {
    print_status "Eliminando repositorio ECR..."
    
    if aws ecr describe-repositories --repository-names mirror-sensor > /dev/null 2>&1; then
        print_warning "Eliminando repositorio ECR 'mirror-sensor'..."
        aws ecr delete-repository --repository-name mirror-sensor --force --region $REGION
        print_success "Repositorio ECR eliminado"
    else
        print_warning "Repositorio ECR 'mirror-sensor' no encontrado"
    fi
}

# Limpiar archivos de configuración
cleanup_config_files() {
    print_status "Limpiando archivos de configuración..."
    
    # Restaurar backup de terraform.tfvars si existe
    if [ -f "terraform/env/terraform.tfvars.backup" ]; then
        mv terraform/env/terraform.tfvars.backup terraform/env/terraform.tfvars
        print_success "Archivo terraform.tfvars restaurado desde backup"
    fi
    
    # Eliminar archivo .env
    if [ -f ".env" ]; then
        rm .env
        print_success "Archivo .env eliminado"
    fi
    
    # Limpiar archivos temporales de Terraform
    if [ -d "terraform/env/.terraform" ]; then
        rm -rf terraform/env/.terraform
        print_success "Archivos temporales de Terraform eliminados"
    fi
}

# Verificar recursos restantes
check_remaining_resources() {
    print_status "Verificando recursos restantes..."
    
    # Verificar ECS
    ECS_CLUSTERS=$(aws ecs list-clusters --query 'clusterArns[?contains(@, `mirror-cluster`)]' --output text)
    if [ -n "$ECS_CLUSTERS" ]; then
        print_warning "ECS Clusters restantes: $ECS_CLUSTERS"
    fi
    
    # Verificar Load Balancers
    LBS=$(aws elbv2 describe-load-balancers --query 'LoadBalancers[?contains(LoadBalancerName, `mirror`) || contains(LoadBalancerName, `sensor`)].[LoadBalancerName,LoadBalancerArn]' --output text)
    if [ -n "$LBS" ]; then
        print_warning "Load Balancers restantes:"
        echo "$LBS"
    fi
    
    # Verificar DynamoDB
    DYNAMO_TABLES=$(aws dynamodb list-tables --query 'TableNames[?contains(@, `demo-pcap-control`)]' --output text)
    if [ -n "$DYNAMO_TABLES" ]; then
        print_warning "DynamoDB Tables restantes: $DYNAMO_TABLES"
    fi
    
    # Verificar ECR
    ECR_REPOS=$(aws ecr describe-repositories --query 'repositories[?contains(repositoryName, `mirror-sensor`)].[repositoryName,repositoryUri]' --output text)
    if [ -n "$ECR_REPOS" ]; then
        print_warning "ECR Repositories restantes:"
        echo "$ECR_REPOS"
    fi
}

# Mostrar resumen final
show_cleanup_summary() {
    print_success "🧹 Limpieza completada!"
    echo ""
    echo "📋 Resumen de la limpieza:"
    echo "  ✅ Infraestructura Terraform destruida"
    echo "  ✅ Repositorio ECR eliminado"
    echo "  ✅ Archivos de configuración limpiados"
    echo ""
    echo "⚠️  Verifica manualmente que no queden recursos:"
    echo "  - ECS Clusters"
    echo "  - Load Balancers"
    echo "  - DynamoDB Tables"
    echo "  - Security Groups"
    echo "  - CloudWatch Log Groups"
    echo ""
    echo "🔧 Comandos para verificar:"
    echo "  - aws ecs list-clusters"
    echo "  - aws elbv2 describe-load-balancers"
    echo "  - aws dynamodb list-tables"
    echo "  - aws ec2 describe-security-groups"
}

# Función principal
main() {
    echo "🧹 Limpieza de Recursos AWS"
    echo "============================"
    echo ""
    
    check_aws_cli
    get_account_info
    
    echo ""
    print_warning "⚠️  ADVERTENCIA: Este script eliminará TODOS los recursos del proyecto"
    echo ""
    
    destroy_terraform
    delete_ecr_repository
    cleanup_config_files
    check_remaining_resources
    show_cleanup_summary
}

# Ejecutar script
main "$@"
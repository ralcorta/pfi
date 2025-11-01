#!/bin/bash
# ========================================
# SCRIPT DE DESPLIEGUE COMPLETO A AWS
# ========================================

set -e

TERRAFORM_DIR="${1:-terraform/prod}"
SKIP_BUILD="${2:-false}"

echo "🚀 Iniciando despliegue del sensor en AWS..."
echo "📋 Directorio Terraform: ${TERRAFORM_DIR}"

# Cambiar al directorio del proyecto
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${PROJECT_ROOT}"

# 1. Inicializar Terraform
echo ""
echo "📦 Paso 1: Inicializando Terraform..."
cd "${TERRAFORM_DIR}"
terraform init

# 2. Validar configuración de Terraform
echo ""
echo "✅ Paso 2: Validando configuración de Terraform..."
terraform validate

# 3. Plan de despliegue
echo ""
echo "📋 Paso 3: Generando plan de despliegue..."
terraform plan -out=tfplan

# 4. Aplicar infraestructura (crear ECR, ECS, etc.)
echo ""
echo "🏗️  Paso 4: Desplegando infraestructura..."
terraform apply tfplan

# Obtener outputs importantes
ECR_REPO_URL=$(terraform output -raw ecr_repository_url 2>/dev/null || echo "")
CLUSTER_NAME=$(terraform output -raw ecs_cluster_name 2>/dev/null || echo "")

cd "${PROJECT_ROOT}"

# 5. Construir y subir imagen Docker (si no se omite)
if [ "${SKIP_BUILD}" != "true" ]; then
    echo ""
    echo "🐳 Paso 5: Construyendo y subiendo imagen Docker..."
    bash scripts/build-and-push.sh "${TERRAFORM_DIR}" "true"
else
    echo ""
    echo "⏭️  Paso 5: Omitiendo build de imagen (ya existe)"
fi

# 6. Esperar a que el servicio esté estable
if [ -n "${CLUSTER_NAME}" ]; then
    SERVICE_NAME=$(grep -E "^project_name" "${TERRAFORM_DIR}/terraform.tfvars" | cut -d'"' -f2 | head -1 || echo "pfi-sensor")
    SERVICE_NAME="${SERVICE_NAME}-sensor-service"
    AWS_REGION=$(grep -E "^aws_region" "${TERRAFORM_DIR}/terraform.tfvars" | cut -d'"' -f2 | head -1 || echo "us-east-1")
    
    echo ""
    echo "⏳ Paso 6: Esperando a que el servicio ECS esté estable..."
    aws ecs wait services-stable \
        --cluster "${CLUSTER_NAME}" \
        --services "${SERVICE_NAME}" \
        --region "${AWS_REGION}" || echo "⚠️  El servicio puede estar iniciándose..."
fi

# 7. Mostrar información de despliegue
echo ""
echo "✅ Despliegue completado!"
echo ""
echo "📊 Información del despliegue:"
cd "${TERRAFORM_DIR}"
terraform output

echo ""
echo "🔍 Para ver los logs del sensor:"
echo "   aws logs tail /ecs/$(terraform output -raw ecs_cluster_name | sed 's/-sensor-cluster//')-sensor --follow --region $(grep -E '^aws_region' terraform.tfvars | cut -d'"' -f2 | head -1)"


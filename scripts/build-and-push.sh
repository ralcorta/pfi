#!/bin/bash
# ========================================
# SCRIPT PARA BUILD Y PUSH DE IMAGEN DOCKER
# ========================================

set -e

# Leer configuración desde terraform.tfvars si existe
TERRAFORM_DIR="${1:-terraform/prod}"
if [ -f "${TERRAFORM_DIR}/terraform.tfvars" ]; then
    AWS_REGION=$(grep -E "^aws_region" "${TERRAFORM_DIR}/terraform.tfvars" | cut -d'"' -f2 | head -1 || echo "us-east-1")
    PROJECT_NAME=$(grep -E "^project_name" "${TERRAFORM_DIR}/terraform.tfvars" | cut -d'"' -f2 | head -1 || echo "pfi-sensor")
else
    AWS_REGION="us-east-1"
    PROJECT_NAME="pfi-sensor"
fi

ECR_REPO_NAME="mirror-sensor"  # Nombre del repositorio ECR (debe coincidir con Terraform)
IMAGE_TAG="latest"
UPDATE_SERVICE="${2:-true}"  # Por defecto actualiza el servicio

echo "🚀 Iniciando build y push de imagen Docker..."
echo "📋 Configuración:"
echo "   - Región: ${AWS_REGION}"
echo "   - Proyecto: ${PROJECT_NAME}"
echo "   - Repositorio ECR: ${ECR_REPO_NAME}"

# 1. Obtener account ID
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
ECR_URI="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${ECR_REPO_NAME}"

echo "📦 Account ID: ${AWS_ACCOUNT_ID}"
echo "🏷️  ECR URI: ${ECR_URI}"

# 2. Verificar permisos ECR
echo "🔍 Verificando permisos ECR..."
if ! aws ecr describe-repositories --region ${AWS_REGION} --repository-names ${ECR_REPO_NAME} >/dev/null 2>&1; then
    echo "⚠️  El repositorio ECR no existe. Se creará al ejecutar Terraform."
    echo "💡 Ejecuta 'terraform apply' primero para crear el repositorio."
    exit 1
fi

# 3. Login a ECR
echo "🔐 Haciendo login a ECR..."
aws ecr get-login-password --region ${AWS_REGION} | docker login --username AWS --password-stdin ${ECR_URI}

# 4. Build de la imagen
echo "🔨 Construyendo imagen Docker..."
docker build -t ${ECR_REPO_NAME}:${IMAGE_TAG} -f dockerfile .

# 5. Tag para ECR
echo "🏷️  Taggeando imagen para ECR..."
docker tag ${ECR_REPO_NAME}:${IMAGE_TAG} ${ECR_URI}:${IMAGE_TAG}

# 6. Push a ECR
echo "⬆️  Subiendo imagen a ECR..."
if docker push ${ECR_URI}:${IMAGE_TAG}; then
    echo "✅ Imagen subida exitosamente!"
    echo "🔗 URI de la imagen: ${ECR_URI}:${IMAGE_TAG}"
    
    # 7. Actualizar ECS service (opcional)
    if [ "${UPDATE_SERVICE}" = "true" ]; then
        CLUSTER_NAME="${PROJECT_NAME}-sensor-cluster"
        SERVICE_NAME="${PROJECT_NAME}-sensor-service"
        
        echo "🔄 Actualizando ECS service..."
        if aws ecs describe-services --cluster ${CLUSTER_NAME} --services ${SERVICE_NAME} --region ${AWS_REGION} >/dev/null 2>&1; then
            aws ecs update-service \
                --cluster ${CLUSTER_NAME} \
                --service ${SERVICE_NAME} \
                --force-new-deployment \
                --region ${AWS_REGION} >/dev/null
            echo "✅ ECS service actualizado!"
        else
            echo "⚠️  El servicio ECS aún no existe. Ejecuta 'terraform apply' primero."
        fi
    fi
else
    echo "❌ Error al subir imagen a ECR"
    echo "💡 Posibles soluciones:"
    echo "   1. Verificar permisos ECR"
    echo "   2. Verificar que el repositorio existe"
    echo "   3. Contactar al administrador de AWS Academy"
    exit 1
fi

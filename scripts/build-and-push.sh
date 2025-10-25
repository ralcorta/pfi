#!/bin/bash
# ========================================
# SCRIPT PARA BUILD Y PUSH DE IMAGEN DOCKER
# ========================================

set -e

# Variables para AWS Academy
AWS_REGION="us-east-1"
ECR_REPO_NAME="mirror-sensor"  # Nombre del repositorio ECR
IMAGE_TAG="latest"

echo "🚀 Iniciando build y push de imagen Docker..."

# 1. Obtener account ID
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
ECR_URI="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${ECR_REPO_NAME}"

echo "📦 Account ID: ${AWS_ACCOUNT_ID}"
echo "🏷️  ECR URI: ${ECR_URI}"

# 2. Verificar permisos ECR
echo "🔍 Verificando permisos ECR..."
if ! aws ecr describe-repositories --region ${AWS_REGION} >/dev/null 2>&1; then
    echo "❌ Error: No tienes permisos para acceder a ECR"
    echo "💡 Soluciones:"
    echo "   1. Contactar al administrador de AWS Academy para permisos ECR"
    echo "   2. Usar una imagen pública en lugar de ECR"
    echo "   3. Usar una cuenta AWS personal"
    exit 1
fi

# 3. Login a ECR
echo "🔐 Haciendo login a ECR..."
aws ecr get-login-password --region ${AWS_REGION} | docker login --username AWS --password-stdin ${ECR_URI}

# 4. Build de la imagen
echo "🔨 Construyendo imagen Docker..."
docker build -t ${ECR_REPO_NAME}:${IMAGE_TAG} .

# 5. Tag para ECR
echo "🏷️  Taggeando imagen para ECR..."
docker tag ${ECR_REPO_NAME}:${IMAGE_TAG} ${ECR_URI}:${IMAGE_TAG}

# 6. Push a ECR
echo "⬆️  Subiendo imagen a ECR..."
if docker push ${ECR_URI}:${IMAGE_TAG}; then
    echo "✅ Imagen subida exitosamente!"
    echo "🔗 URI de la imagen: ${ECR_URI}:${IMAGE_TAG}"
    
    # 7. Actualizar ECS service
    echo "🔄 Actualizando ECS service..."
    aws ecs update-service --cluster pfi-sensor-sensor-cluster --service pfi-sensor-sensor-service --force-new-deployment --region ${AWS_REGION}
    echo "✅ ECS service actualizado!"
else
    echo "❌ Error al subir imagen a ECR"
    echo "💡 Posibles soluciones:"
    echo "   1. Verificar permisos ECR"
    echo "   2. Usar una imagen pública en lugar de ECR"
    echo "   3. Contactar al administrador de AWS Academy"
    exit 1
fi

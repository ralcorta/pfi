#!/bin/bash
# ========================================
# SCRIPT PARA BUILD Y PUSH DE IMAGEN DOCKER
# ========================================

set -e

# Variables para AWS Academy
AWS_REGION="us-east-1"
ECR_REPO_NAME="pfi-sensor"  # Nombre más corto para AWS Academy
IMAGE_TAG="latest"

echo "🚀 Iniciando build y push de imagen Docker..."

# 1. Obtener account ID
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
ECR_URI="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${ECR_REPO_NAME}"

echo "📦 Account ID: ${AWS_ACCOUNT_ID}"
echo "🏷️  ECR URI: ${ECR_URI}"

# 2. Login a ECR
echo "🔐 Haciendo login a ECR..."
aws ecr get-login-password --region ${AWS_REGION} | docker login --username AWS --password-stdin ${ECR_URI}

# 3. Build de la imagen
echo "🔨 Construyendo imagen Docker..."
docker build -t ${ECR_REPO_NAME}:${IMAGE_TAG} .

# 4. Tag para ECR
echo "🏷️  Taggeando imagen para ECR..."
docker tag ${ECR_REPO_NAME}:${IMAGE_TAG} ${ECR_URI}:${IMAGE_TAG}

# 5. Push a ECR
echo "⬆️  Subiendo imagen a ECR..."
docker push ${ECR_URI}:${IMAGE_TAG}

echo "✅ Imagen subida exitosamente!"
echo "🔗 URI de la imagen: ${ECR_URI}:${IMAGE_TAG}"

# 6. Actualizar ECS service (opcional)
echo "🔄 Para actualizar el ECS service, ejecuta:"
echo "aws ecs update-service --cluster pfi-sensor-cluster --service pfi-sensor-service --force-new-deployment"

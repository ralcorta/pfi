#!/bin/bash

# Script para construir y subir imagen a ECR
set -e

# Variables
AWS_REGION=${AWS_REGION:-us-east-1}
AWS_ACCOUNT_ID=${AWS_ACCOUNT_ID:-$(aws sts get-caller-identity --query Account --output text)}
ECR_REPOSITORY="mirror-sensor"
IMAGE_TAG=${IMAGE_TAG:-latest}

echo "🚀 Desplegando mirror-sensor a ECR..."
echo "📋 Configuración:"
echo "   - AWS Account: $AWS_ACCOUNT_ID"
echo "   - AWS Region: $AWS_REGION"
echo "   - Repository: $ECR_REPOSITORY"
echo "   - Tag: $IMAGE_TAG"

# 1. Crear repositorio ECR si no existe
echo "📦 Creando repositorio ECR..."
aws ecr describe-repositories --repository-names $ECR_REPOSITORY --region $AWS_REGION 2>/dev/null || \
aws ecr create-repository --repository-name $ECR_REPOSITORY --region $AWS_REGION

# 2. Autenticar Docker con ECR
echo "🔐 Autenticando Docker con ECR..."
aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com

# 3. Construir imagen
echo "🔨 Construyendo imagen Docker..."
docker build -t $ECR_REPOSITORY:$IMAGE_TAG .

# 4. Etiquetar imagen para ECR
echo "🏷️ Etiquetando imagen..."
docker tag $ECR_REPOSITORY:$IMAGE_TAG $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$ECR_REPOSITORY:$IMAGE_TAG

# 5. Subir imagen a ECR
echo "⬆️ Subiendo imagen a ECR..."
docker push $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$ECR_REPOSITORY:$IMAGE_TAG

echo "✅ Imagen subida exitosamente!"
echo "📋 URI de la imagen: $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$ECR_REPOSITORY:$IMAGE_TAG"

# 6. Exportar variables para docker-compose
echo "🔧 Configurando variables de entorno..."
export AWS_ACCOUNT_ID=$AWS_ACCOUNT_ID
export AWS_REGION=$AWS_REGION

echo "🎉 Despliegue completado!"
echo "💡 Para usar con docker-compose:"
echo "   export AWS_ACCOUNT_ID=$AWS_ACCOUNT_ID"
echo "   export AWS_REGION=$AWS_REGION"
echo "   docker-compose up mirror-sensor"

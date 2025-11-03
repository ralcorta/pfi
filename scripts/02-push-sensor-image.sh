#!/bin/bash
#
# Script 2: Subir imagen del sensor al ECR
# Construye y sube la imagen Docker del sensor al ECR de AWS
#

set -e

# Colores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

TERRAFORM_DIR="terraform/analizer"

echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}🐳 Paso 2: Subiendo imagen del sensor al ECR${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# Verificar que Docker está instalado
if ! command -v docker &> /dev/null; then
    echo -e "${RED}❌ Error: Docker no está instalado${NC}"
    exit 1
fi

# Obtener configuración desde Terraform
if [ -f "${TERRAFORM_DIR}/terraform.tfvars" ]; then
    AWS_REGION=$(grep -E "^aws_region" "${TERRAFORM_DIR}/terraform.tfvars" | cut -d'"' -f2 | head -1 || echo "us-east-1")
    PROJECT_NAME=$(grep -E "^project_name" "${TERRAFORM_DIR}/terraform.tfvars" | cut -d'"' -f2 | head -1 || echo "sensor-analyzer")
else
    AWS_REGION="us-east-1"
    PROJECT_NAME="sensor-analyzer"
fi

ECR_REPO_NAME="mirror-sensor"
IMAGE_TAG="latest"

echo -e "${BLUE}📋 Configuración:${NC}"
echo -e "   Región: ${AWS_REGION}"
echo -e "   Proyecto: ${PROJECT_NAME}"
echo -e "   Repositorio: ${ECR_REPO_NAME}"
echo ""

# Obtener account ID
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
ECR_URI="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${ECR_REPO_NAME}"

echo -e "${BLUE}🔍 Account ID: ${AWS_ACCOUNT_ID}${NC}"
echo -e "${BLUE}🔗 ECR URI: ${ECR_URI}${NC}"
echo ""

# Verificar que el repositorio existe
echo -e "${BLUE}🔍 Verificando repositorio ECR...${NC}"
if ! aws ecr describe-repositories --region ${AWS_REGION} --repository-names ${ECR_REPO_NAME} >/dev/null 2>&1; then
    echo -e "${RED}❌ El repositorio ECR no existe${NC}"
    echo -e "${YELLOW}💡 Ejecuta primero el script 01-deploy-analizer.sh${NC}"
    exit 1
fi
echo -e "${GREEN}✅ Repositorio encontrado${NC}"
echo ""

# Login a ECR
echo -e "${BLUE}🔐 Haciendo login a ECR...${NC}"
aws ecr get-login-password --region ${AWS_REGION} | docker login --username AWS --password-stdin ${ECR_URI}
echo -e "${GREEN}✅ Login exitoso${NC}"
echo ""

# Build de la imagen
echo -e "${BLUE}🔨 Construyendo imagen Docker...${NC}"
docker build -t ${ECR_REPO_NAME}:${IMAGE_TAG} -f dockerfile .
echo -e "${GREEN}✅ Imagen construida${NC}"
echo ""

# Tag para ECR
echo -e "${BLUE}🏷️  Taggeando imagen para ECR...${NC}"
docker tag ${ECR_REPO_NAME}:${IMAGE_TAG} ${ECR_URI}:${IMAGE_TAG}
echo -e "${GREEN}✅ Imagen taggeada${NC}"
echo ""

# Push a ECR
echo -e "${BLUE}⬆️  Subiendo imagen a ECR...${NC}"
if docker push ${ECR_URI}:${IMAGE_TAG}; then
    echo -e "${GREEN}✅ Imagen subida exitosamente!${NC}"
    echo -e "${BLUE}🔗 URI: ${ECR_URI}:${IMAGE_TAG}${NC}"
    echo ""
    
    # Actualizar ECS service
    CLUSTER_NAME="${PROJECT_NAME}-sensor-cluster"
    SERVICE_NAME="${PROJECT_NAME}-sensor-service"
    
    echo -e "${BLUE}🔄 Actualizando ECS service...${NC}"
    if aws ecs describe-services --cluster ${CLUSTER_NAME} --services ${SERVICE_NAME} --region ${AWS_REGION} >/dev/null 2>&1; then
        aws ecs update-service \
            --cluster ${CLUSTER_NAME} \
            --service ${SERVICE_NAME} \
            --force-new-deployment \
            --region ${AWS_REGION} >/dev/null
        echo -e "${GREEN}✅ ECS service actualizado!${NC}"
        echo -e "${YELLOW}💡 El servicio puede tardar algunos minutos en desplegar la nueva imagen${NC}"
    else
        echo -e "${YELLOW}⚠️  El servicio ECS aún no existe${NC}"
    fi
else
    echo -e "${RED}❌ Error al subir imagen a ECR${NC}"
    exit 1
fi

echo ""
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}✅ Paso 2 completado${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"


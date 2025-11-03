#!/bin/bash
#
# Script 3: Desplegar Dashboard en S3
# Compila y despliega el dashboard frontend a S3 como SPA
#

set -e

# Colores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

TERRAFORM_DIR="terraform/analizer"
DASHBOARD_DIR="dashboard"

echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}🌐 Paso 3: Desplegando Dashboard en S3${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# Verificar que Terraform está disponible
if ! command -v terraform &> /dev/null; then
    echo -e "${RED}❌ Error: terraform no está instalado${NC}"
    exit 1
fi

# Obtener información del bucket desde Terraform
echo -e "${BLUE}📋 Obteniendo información del bucket desde Terraform...${NC}"
cd "${TERRAFORM_DIR}" || exit 1

# Obtener outputs de Terraform
BUCKET_NAME=$(terraform output -raw dashboard_bucket_name 2>/dev/null || echo "")
API_BASE_URL=$(terraform output -raw api_base_url 2>/dev/null || echo "")

# Obtener región
AWS_REGION=$(grep 'variable "aws_region"' "${TERRAFORM_DIR}/variables.tf" | grep -o 'default = "[^"]*"' | sed 's/default = "\(.*\)"/\1/' 2>/dev/null || echo "us-east-1")
if [ -z "$AWS_REGION" ] || [ "$AWS_REGION" = "" ]; then
    if [ -f "${TERRAFORM_DIR}/terraform.tfvars" ]; then
        AWS_REGION=$(grep '^aws_region' "${TERRAFORM_DIR}/terraform.tfvars" | sed 's/.*= *"\(.*\)".*/\1/' || echo "us-east-1")
    fi
    if [ -z "$AWS_REGION" ] || [ "$AWS_REGION" = "" ]; then
        AWS_REGION="us-east-1"
    fi
fi

if [ -z "$BUCKET_NAME" ]; then
    echo -e "${RED}❌ Error: No se pudo obtener el nombre del bucket desde Terraform${NC}"
    echo "💡 Asegúrate de que el analizer está desplegado primero"
    exit 1
fi

if [ -z "$API_BASE_URL" ]; then
    echo -e "${YELLOW}⚠️  No se pudo obtener la URL de la API, usando valor por defecto${NC}"
    API_BASE_URL="http://localhost:8080"
fi

echo -e "${GREEN}✅ Bucket: ${BUCKET_NAME}${NC}"
echo -e "${GREEN}✅ API URL: ${API_BASE_URL}${NC}"
echo -e "${GREEN}✅ Región: ${AWS_REGION}${NC}"
echo ""

# Volver al directorio raíz
cd - > /dev/null

# Compilar el dashboard
echo -e "${BLUE}🔨 Compilando el dashboard...${NC}"
cd "${DASHBOARD_DIR}" || exit 1

# Instalar dependencias si es necesario
if [ ! -d "node_modules" ]; then
    echo "📦 Instalando dependencias..."
    npm install --ignore-scripts
fi

# Compilar con la URL de la API correcta
echo -e "${BLUE}🔨 Construyendo para producción...${NC}"
VITE_API_BASE_URL="${API_BASE_URL}" npm run build:ci

if [ ! -d "dist" ]; then
    echo -e "${RED}❌ Error: La carpeta dist no fue creada${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Build completado!${NC}"
echo ""

# Volver al directorio raíz
cd - > /dev/null

# Sincronizar con S3
echo -e "${BLUE}⬆️  Subiendo archivos a S3...${NC}"
aws s3 sync "${DASHBOARD_DIR}/dist/" "s3://${BUCKET_NAME}" \
    --region "${AWS_REGION}" \
    --delete \
    --exclude "*.map" \
    --cache-control "public, max-age=31536000, immutable"

echo -e "${GREEN}✅ Archivos subidos exitosamente!${NC}"
echo ""

# Mostrar URL del dashboard
echo -e "${BLUE}🔗 URL del dashboard:${NC}"
echo -e "${GREEN}   http://${BUCKET_NAME}.s3-website-${AWS_REGION}.amazonaws.com${NC}"
echo ""

echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}✅ Paso 3 completado${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"


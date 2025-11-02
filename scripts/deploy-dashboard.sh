#!/bin/bash
# ========================================
# SCRIPT PARA BUILD Y DEPLOY DEL DASHBOARD A S3
# ========================================

set -e

# Leer configuración desde terraform.tfvars si existe
TERRAFORM_DIR="${1:-terraform/split/analizer}"
if [ -f "${TERRAFORM_DIR}/terraform.tfvars" ]; then
    AWS_REGION=$(grep -E "^aws_region" "${TERRAFORM_DIR}/terraform.tfvars" | cut -d'"' -f2 | head -1 || echo "us-east-1")
    PROJECT_NAME=$(grep -E "^project_name" "${TERRAFORM_DIR}/terraform.tfvars" | cut -d'"' -f2 | head -1 || echo "sensor-analyzer")
    ACCOUNT_ID=$(grep -E "^account_id" "${TERRAFORM_DIR}/terraform.tfvars" | cut -d'"' -f2 | head -1 || echo "339712899854")
else
    AWS_REGION="us-east-1"
    PROJECT_NAME="sensor-analyzer"
    ACCOUNT_ID="339712899854"
fi

BUCKET_NAME="${PROJECT_NAME}-dashboard-${ACCOUNT_ID}"
API_BASE_URL="${2:-http://localhost:8080}"

echo "🚀 Iniciando build y deploy del dashboard a S3..."
echo "📋 Configuración:"
echo "   - Región: ${AWS_REGION}"
echo "   - Proyecto: ${PROJECT_NAME}"
echo "   - Bucket S3: ${BUCKET_NAME}"
echo "   - API Base URL: ${API_BASE_URL}"

# Cambiar al directorio del proyecto
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${PROJECT_ROOT}"

# 1. Verificar que el bucket existe
echo ""
echo "🔍 Verificando que el bucket S3 existe..."
if ! aws s3 ls "s3://${BUCKET_NAME}" --region ${AWS_REGION} >/dev/null 2>&1; then
    echo "⚠️  El bucket S3 no existe."
    echo "💡 Ejecuta 'terraform apply' primero en ${TERRAFORM_DIR} para crear el bucket."
    exit 1
fi
echo "✅ Bucket S3 encontrado: ${BUCKET_NAME}"

# 2. Construir el dashboard
echo ""
echo "🔨 Construyendo el dashboard..."
cd dashboard

# Verificar que npm esté instalado
if ! command -v npm &> /dev/null; then
    echo "❌ Error: No se encontró npm. Por favor instala Node.js."
    exit 1
fi

PACKAGE_MANAGER="npm"

echo "📦 Instalando dependencias con npm..."
${PACKAGE_MANAGER} install --legacy-peer-deps

echo "🏗️  Construyendo aplicación..."
# Configurar variable de entorno para la API
export VITE_API_BASE_URL="${API_BASE_URL}"
# Usar build:ci que omite el lint para evitar errores en despliegue
${PACKAGE_MANAGER} run build:ci

if [ ! -d "dist" ]; then
    echo "❌ Error: No se generó el directorio dist/"
    exit 1
fi

echo "✅ Build completado!"

# 3. Sincronizar con S3
echo ""
echo "⬆️  Subiendo archivos a S3..."
aws s3 sync dist/ "s3://${BUCKET_NAME}" \
    --region ${AWS_REGION} \
    --delete \
    --exclude "*.map" \
    --cache-control "public, max-age=31536000, immutable"

echo "✅ Archivos subidos exitosamente!"

# 4. Obtener la URL del website
echo ""
echo "🔗 URL del dashboard:"
WEBSITE_URL=$(aws s3api get-bucket-website --bucket ${BUCKET_NAME} --region ${AWS_REGION} --query 'WebsiteConfiguration' --output text 2>/dev/null || echo "")
if [ -n "${WEBSITE_URL}" ]; then
    echo "   http://${BUCKET_NAME}.s3-website-${AWS_REGION}.amazonaws.com"
    echo ""
    echo "💡 Nota: Esta es la URL del website endpoint de S3."
    echo "   Para usar un dominio personalizado, configura CloudFront o un dominio personalizado."
else
    echo "   https://${BUCKET_NAME}.s3.${AWS_REGION}.amazonaws.com"
fi

echo ""
echo "✅ Dashboard desplegado exitosamente!"


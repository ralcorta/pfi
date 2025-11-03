#!/bin/bash
#
# Script 1: Desplegar Terraform del Analizer
# Despliega toda la infraestructura del analizador en AWS
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
echo -e "${BLUE}📦 Paso 1: Desplegando Terraform del Analizer${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# Verificar que Terraform está instalado
if ! command -v terraform &> /dev/null; then
    echo -e "${RED}❌ Error: terraform no está instalado${NC}"
    exit 1
fi

# Cambiar al directorio de Terraform
cd "${TERRAFORM_DIR}" || exit 1

# Inicializar Terraform si es necesario
if [ ! -d ".terraform" ]; then
    echo -e "${BLUE}🔧 Inicializando Terraform...${NC}"
    terraform init
    echo ""
fi

# Validar configuración
echo -e "${BLUE}✅ Validando configuración...${NC}"
terraform validate
echo ""

# Aplicar cambios
echo -e "${BLUE}🚀 Aplicando cambios de infraestructura...${NC}"
echo -e "${YELLOW}⚠️  Esto puede tardar varios minutos...${NC}"
echo ""

terraform apply -auto-approve

if [ $? -eq 0 ]; then
    echo ""
    echo -e "${GREEN}✅ Analizer desplegado exitosamente!${NC}"
    echo ""
    
    # Mostrar outputs importantes
    echo -e "${BLUE}📊 Outputs importantes:${NC}"
    terraform output -json 2>/dev/null | jq -r '
        "API Base URL: " + (.api_base_url.value // "N/A"),
        "Mirror NLB DNS: " + (.mirror_nlb_dns.value // "N/A"),
        "Transit Gateway ID: " + (.transit_gateway_id.value // "N/A"),
        "VPC CIDR: " + (.vpc_analizador_cidr.value // "N/A")
    ' || echo "  No se pudieron obtener los outputs"
    
    echo ""
else
    echo -e "${RED}❌ Error al desplegar el analizer${NC}"
    exit 1
fi

# Volver al directorio raíz
cd - > /dev/null

echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}✅ Paso 1 completado${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"


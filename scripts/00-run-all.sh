#!/bin/bash
#
# Script maestro: Ejecuta todos los scripts de despliegue en secuencia
# Para el video demo
#

set -e

# Colores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}🎬 INICIANDO DESPLIEGUE COMPLETO PARA DEMO${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

cd "$PROJECT_ROOT"

# Scripts en orden
SCRIPTS=(
    "01-deploy-analizer.sh"
    "02-push-sensor-image.sh"
    "03-deploy-dashboard.sh"
    "04-deploy-client.sh"
    "05-send-traffic.sh"
)

for script in "${SCRIPTS[@]}"; do
    SCRIPT_PATH="$SCRIPT_DIR/$script"
    
    if [ ! -f "$SCRIPT_PATH" ]; then
        echo -e "${RED}❌ Error: Script no encontrado: $script${NC}"
        exit 1
    fi
    
    echo ""
    echo -e "${YELLOW}▶️  Ejecutando: $script${NC}"
    echo ""
    
    if bash "$SCRIPT_PATH"; then
        echo ""
        echo -e "${GREEN}✅ $script completado exitosamente${NC}"
        echo ""
        sleep 2  # Pequeña pausa entre scripts para mejor visualización en el video
    else
        echo ""
        echo -e "${RED}❌ Error en $script${NC}"
        echo -e "${RED}   El proceso se detiene aquí${NC}"
        exit 1
    fi
done

echo ""
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}🎉 DESPLIEGUE COMPLETO FINALIZADO${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "${BLUE}📋 Resumen:${NC}"
echo -e "   1. ✅ Analizer desplegado"
echo -e "   2. ✅ Imagen del sensor subida a ECR"
echo -e "   3. ✅ Dashboard desplegado en S3"
echo -e "   4. ✅ Client desplegado"
echo -e "   5. ✅ Tráfico PCAP enviado"
echo ""


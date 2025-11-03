#!/bin/bash
# ========================================
# SCRIPT PARA ENVIAR TRÁFICO PCAP AL SENSOR
# ========================================
# 
# Este script copia un archivo PCAP al EC2 del cliente y lo reproduce usando tcpreplay.
# El tráfico será automáticamente reflejado por AWS Traffic Mirroring al sensor.
#
# Uso: ./scripts/send_pcap_traffic.sh [PCAP_FILE] [CLIENT_IP]
# ========================================

set -e

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Parámetros
PCAP_FILE="${1:-/Users/rodrigo/Documents/uade/tesis/pfi/scripts/Zeus.pcap}"
CLIENT_IP="${2}"
SKIP_CONFIRM="${3:-false}"

# Si el tercer parámetro es "y" o "yes", saltar confirmación
if [ "$CLIENT_IP" = "y" ] || [ "$CLIENT_IP" = "yes" ] || [ "$CLIENT_IP" = "-y" ] || [ "$CLIENT_IP" = "--yes" ]; then
    SKIP_CONFIRM="true"
    CLIENT_IP=""
fi

# Re-evaluar CLIENT_IP si fue usado como flag
if [ "$SKIP_CONFIRM" = "true" ] && [ -z "$CLIENT_IP" ]; then
    CLIENT_IP="${2}"  # No hay segundo parámetro, obtener automáticamente
fi

# Validar que el archivo PCAP existe
if [ ! -f "$PCAP_FILE" ]; then
    echo -e "${RED}❌ Error: Archivo PCAP no encontrado: $PCAP_FILE${NC}"
    exit 1
fi

# Si no se proporciona CLIENT_IP, intentar obtenerlo de Terraform o AWS
if [ -z "$CLIENT_IP" ]; then
    echo -e "${BLUE}🔍 Obteniendo IP del cliente desde AWS...${NC}"
    
    # Obtener desde AWS directamente
    INSTANCE_ID=$(aws ec2 describe-instances \
        --filters "Name=tag:Name,Values=sensor-analyzer-cliente-instance" "Name=instance-state-name,Values=running" \
        --query 'Reservations[0].Instances[0].InstanceId' \
        --output text \
        --region us-east-1 2>/dev/null || echo "")
    
    if [ -n "$INSTANCE_ID" ] && [ "$INSTANCE_ID" != "None" ] && [ "$INSTANCE_ID" != "null" ]; then
        CLIENT_IP=$(aws ec2 describe-instances \
            --instance-ids "$INSTANCE_ID" \
            --query 'Reservations[0].Instances[0].PublicIpAddress' \
            --output text \
            --region us-east-1 2>/dev/null || echo "")
    fi
fi

# Validar que tenemos una IP
if [ -z "$CLIENT_IP" ] || [ "$CLIENT_IP" = "None" ] || [ "$CLIENT_IP" = "null" ]; then
    echo -e "${RED}❌ Error: No se pudo obtener la IP del cliente EC2${NC}"
    echo -e "${YELLOW}💡 Proporciónala manualmente: ./scripts/send_pcap_traffic.sh $PCAP_FILE <IP_CLIENTE>${NC}"
    exit 1
fi

# Buscar clave SSH
SSH_KEY=""
if [ -f ~/.ssh/vockey.pem ]; then
    SSH_KEY=~/.ssh/vockey.pem
elif [ -f ~/Downloads/vockey.pem ]; then
    SSH_KEY=~/Downloads/vockey.pem
elif [ -f ~/Downloads/labsuser.pem ]; then
    SSH_KEY=~/Downloads/labsuser.pem
else
    echo -e "${YELLOW}⚠️  Clave SSH no encontrada. Buscando en ubicaciones comunes...${NC}"
    SSH_KEY=$(find ~ -name "vockey.pem" -o -name "labsuser.pem" 2>/dev/null | head -1)
fi

if [ -z "$SSH_KEY" ] || [ ! -f "$SSH_KEY" ]; then
    echo -e "${RED}❌ Error: No se encontró la clave SSH${NC}"
    echo -e "${YELLOW}💡 Coloca la clave en: ~/.ssh/vockey.pem o ~/Downloads/vockey.pem${NC}"
    exit 1
fi

# Función para ejecutar comandos SSH
ssh_exec() {
    ssh -i "$SSH_KEY" \
        -o StrictHostKeyChecking=no \
        -o UserKnownHostsFile=/dev/null \
        -o ConnectTimeout=10 \
        ec2-user@"$CLIENT_IP" \
        "$@"
}

echo "=========================================="
echo "🚀 Enviando Tráfico PCAP al Sensor"
echo "=========================================="
echo "Archivo PCAP: $PCAP_FILE"
echo "Cliente EC2: ec2-user@$CLIENT_IP"
echo "Clave SSH: $SSH_KEY"
echo ""

# Conectar y verificar
echo -e "${BLUE}📡 Conectando al EC2...${NC}"
if ! ssh_exec "echo 'Conectado'" >/dev/null 2>&1; then
    echo -e "${RED}❌ Error: No se pudo conectar al EC2${NC}"
    exit 1
fi
echo -e "${GREEN}✅ Conectado al EC2${NC}"

# Instalar dependencias si es necesario
echo -e "${BLUE}📦 Verificando dependencias...${NC}"
ssh_exec "sudo yum install -y tcpreplay tcpdump iproute 2>/dev/null || echo 'Dependencias ya instaladas'" >/dev/null 2>&1
echo -e "${GREEN}✅ Dependencias listas${NC}"

# Copiar archivo PCAP
echo -e "${BLUE}📤 Copiando archivo PCAP al EC2...${NC}"
PCAP_BASENAME=$(basename "$PCAP_FILE")
scp -i "$SSH_KEY" \
    -o StrictHostKeyChecking=no \
    -o UserKnownHostsFile=/dev/null \
    "$PCAP_FILE" \
    ec2-user@"$CLIENT_IP":/tmp/"$PCAP_BASENAME" >/dev/null 2>&1

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Archivo PCAP copiado${NC}"
else
    echo -e "${RED}❌ Error copiando archivo PCAP${NC}"
    exit 1
fi

# Obtener nombre de la interfaz de red
echo -e "${BLUE}🔍 Obteniendo interfaz de red...${NC}"
# Método más confiable: usar /sys/class/net (disponible en todos los Linux modernos)
INTERFACE=$(ssh_exec "ls /sys/class/net 2>/dev/null | grep -v lo | grep -v docker | head -1")
if [ -z "$INTERFACE" ] || [ "$INTERFACE" = "" ]; then
    # Fallback: intentar con ip route (si iproute2 está instalado)
    INTERFACE=$(ssh_exec "ip route show default 2>/dev/null | awk '/default/ {print \$5}' | head -1")
fi
if [ -z "$INTERFACE" ] || [ "$INTERFACE" = "" ]; then
    # Fallback: interfaces comunes en EC2
    for common_if in eth0 ens5 ens6 enp0s3; do
        if ssh_exec "test -d /sys/class/net/$common_if" >/dev/null 2>&1; then
            INTERFACE="$common_if"
            break
        fi
    done
fi

if [ -z "$INTERFACE" ] || [ "$INTERFACE" = "" ]; then
    echo -e "${RED}❌ Error: No se pudo detectar la interfaz de red${NC}"
    echo -e "${YELLOW}💡 Interfaces disponibles:${NC}"
    ssh_exec "ls -la /sys/class/net/ 2>/dev/null"
    exit 1
fi

echo -e "${GREEN}✅ Interfaz detectada: $INTERFACE${NC}"

# Información del PCAP
echo -e "${BLUE}📊 Información del PCAP:${NC}"
ssh_exec "capinfos /tmp/$PCAP_BASENAME 2>/dev/null || echo 'capinfos no disponible'" | head -10
echo ""

# Confirmación
echo "=========================================="
echo "🚀 Listo para enviar tráfico"
echo "=========================================="
echo "El tráfico será:"
echo "  1. Enviado desde el EC2 por la interfaz $INTERFACE"
echo "  2. Reflejado automáticamente por AWS Traffic Mirroring"
echo "  3. Capturado por el sensor en el puerto UDP/4789"
echo "  4. Analizado por el modelo de detección"
echo ""
echo -e "${YELLOW}⚠️  Nota: El tráfico se enviará con velocidad original del PCAP${NC}"
echo ""

# Confirmación (saltear si SKIP_CONFIRM=true o si stdin no es terminal)
if [ "$SKIP_CONFIRM" != "true" ] && [ -t 0 ]; then
    read -p "¿Continuar con el envío? (y/N): " -n 1 -r
    echo ""
    
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo -e "${YELLOW}⏭️  Envío cancelado${NC}"
        exit 0
    fi
else
    echo -e "${BLUE}⏭️  Saltando confirmación...${NC}"
fi

# Enviar tráfico con tcpreplay
echo -e "${BLUE}🚀 Enviando tráfico PCAP...${NC}"
echo -e "${BLUE}   Interface: $INTERFACE${NC}"
echo -e "${BLUE}   Archivo: /tmp/$PCAP_BASENAME${NC}"
echo ""

# Opciones de tcpreplay:
# -i: interfaz
# --loop: número de veces a repetir (1 = una sola vez)
# --intf1: interfaz primaria
# --mbps: límite de velocidad (opcional)
ssh_exec "sudo tcpreplay -i $INTERFACE --loop=1 /tmp/$PCAP_BASENAME 2>&1"

REPLAY_EXIT=$?

if [ $REPLAY_EXIT -eq 0 ]; then
    echo ""
    echo -e "${GREEN}✅ Tráfico PCAP enviado exitosamente!${NC}"
    echo ""
    echo "🔍 Verifica los logs del sensor:"
    echo "   aws logs tail /ecs/sensor-analyzer-sensor --since 2m --format short --region us-east-1 | grep -E '(Tráfico UDP|📥|procesando batch|detección)'"
    echo ""
    echo "📊 O verifica las detecciones en la API:"
    ANALYZER_API=$(cd terraform/analizer 2>/dev/null && terraform output -raw api_base_url 2>/dev/null || echo "")
    if [ -n "$ANALYZER_API" ]; then
        echo "   $ANALYZER_API/v1/detections"
    fi
else
    echo ""
    echo -e "${YELLOW}⚠️  tcpreplay terminó con código: $REPLAY_EXIT${NC}"
    echo -e "${YELLOW}   (Esto puede ser normal si el PCAP tiene paquetes que no se pueden enviar)${NC}"
fi

echo ""
echo "=========================================="
echo "✅ Proceso completado"
echo "=========================================="


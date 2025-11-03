#!/bin/bash
#
# Script 5: Enviar tráfico PCAP desde EC2 del cliente
# Copia y reproduce el tráfico de Zeus.pcap para que sea reflejado por AWS Mirroring
#

set -e

# Colores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

PCAP_FILE="${1:-scripts/Zeus.pcap}"
SKIP_CONFIRM="${2:-false}"

echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}🚀 Paso 5: Enviando tráfico PCAP desde EC2 del cliente${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# Validar que el archivo PCAP existe
if [ ! -f "$PCAP_FILE" ]; then
    echo -e "${RED}❌ Error: Archivo PCAP no encontrado: $PCAP_FILE${NC}"
    exit 1
fi

# Obtener IP del cliente desde Terraform o AWS
CLIENT_IP=""
if [ -f "terraform/client/terraform.tfstate" ]; then
    CLIENT_IP=$(cd terraform/client && terraform output -raw ec2_public_ip 2>/dev/null || echo "")
fi

if [ -z "$CLIENT_IP" ]; then
    echo -e "${BLUE}🔍 Obteniendo IP del cliente desde AWS (Elastic IP)...${NC}"
    
    # Primero intentar obtener el Elastic IP directamente
    EIP=$(aws ec2 describe-addresses \
        --filters "Name=tag:Name,Values=sensor-analyzer-cliente-eip" \
        --query 'Addresses[0].PublicIp' \
        --output text \
        --region us-east-1 2>/dev/null || echo "")
    
    if [ -n "$EIP" ] && [ "$EIP" != "None" ] && [ "$EIP" != "null" ]; then
        CLIENT_IP="$EIP"
    else
        # Fallback: obtener desde la instancia
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
fi

# Validar que tenemos una IP
if [ -z "$CLIENT_IP" ] || [ "$CLIENT_IP" = "None" ] || [ "$CLIENT_IP" = "null" ]; then
    echo -e "${RED}❌ Error: No se pudo obtener la IP del cliente EC2${NC}"
    echo -e "${YELLOW}💡 Asegúrate de que el cliente está desplegado${NC}"
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

# Verificar y corregir permisos de la clave SSH
KEY_PERMS=$(stat -f "%OLp" "$SSH_KEY" 2>/dev/null || stat -c "%a" "$SSH_KEY" 2>/dev/null || echo "unknown")
if [ "$KEY_PERMS" != "600" ] && [ "$KEY_PERMS" != "400" ]; then
    echo -e "${YELLOW}⚠️  Corrigiendo permisos de la clave SSH (actualmente: $KEY_PERMS)...${NC}"
    chmod 600 "$SSH_KEY" 2>/dev/null || {
        echo -e "${RED}❌ No se pudieron corregir los permisos. Ejecuta manualmente: chmod 600 $SSH_KEY${NC}"
        exit 1
    }
    echo -e "${GREEN}✅ Permisos corregidos a 600${NC}"
fi

# Función para ejecutar comandos SSH
ssh_exec() {
    ssh -i "$SSH_KEY" \
        -o StrictHostKeyChecking=no \
        -o UserKnownHostsFile=/dev/null \
        -o ConnectTimeout=10 \
        -o ServerAliveInterval=5 \
        -o ServerAliveCountMax=3 \
        ec2-user@"$CLIENT_IP" \
        "$@"
}

echo -e "${BLUE}📋 Configuración:${NC}"
echo -e "   Archivo PCAP: $PCAP_FILE"
echo -e "   Cliente EC2: ec2-user@$CLIENT_IP"
echo -e "   Clave SSH: $SSH_KEY"
echo ""

# Conectar y verificar
echo -e "${BLUE}📡 Conectando al EC2...${NC}"
# Probar conexión (usar ConnectTimeout en SSH en lugar de timeout externo)
TEST_OUTPUT=$(ssh_exec "echo 'Conectado'" 2>&1)
SSH_EXIT=$?

if [ $SSH_EXIT -ne 0 ]; then
    echo -e "${RED}❌ Error: No se pudo conectar al EC2${NC}"
    echo -e "${YELLOW}💡 Verificando conectividad...${NC}"
    
    # Mostrar el error real si hay uno
    if [ -n "$TEST_OUTPUT" ]; then
        echo -e "${BLUE}   Error SSH: ${TEST_OUTPUT}${NC}"
    fi
    
    # Intentar ping o verificar si la IP es accesible
    echo -e "${BLUE}   Probando conectividad con: $CLIENT_IP${NC}"
    
    # Verificar si la clave SSH tiene permisos correctos
    if [ -f "$SSH_KEY" ]; then
        KEY_PERMS=$(stat -f "%OLp" "$SSH_KEY" 2>/dev/null || stat -c "%a" "$SSH_KEY" 2>/dev/null || echo "unknown")
        if [ "$KEY_PERMS" != "600" ] && [ "$KEY_PERMS" != "400" ]; then
            echo -e "${YELLOW}⚠️  La clave SSH debería tener permisos 600 o 400 (actualmente: $KEY_PERMS)${NC}"
            echo -e "${BLUE}   Ejecuta: chmod 600 $SSH_KEY${NC}"
        else
            echo -e "${GREEN}   ✅ Permisos de clave SSH correctos: $KEY_PERMS${NC}"
        fi
    fi
    
    echo -e "${YELLOW}💡 Posibles soluciones:${NC}"
    echo -e "${YELLOW}   1. Verifica que la instancia está en estado 'running'${NC}"
    echo -e "${YELLOW}   2. Verifica que el Security Group permite SSH desde tu IP${NC}"
    echo -e "${YELLOW}   3. Verifica que la clave SSH tiene permisos correctos (chmod 600)${NC}"
    echo -e "${YELLOW}   4. Si estás en AWS Academy, puede que necesites usar Session Manager${NC}"
    echo -e "${YELLOW}   5. Prueba conectarte manualmente: ssh -i $SSH_KEY ec2-user@$CLIENT_IP${NC}"
    exit 1
fi
echo -e "${GREEN}✅ Conectado al EC2${NC}"

# Instalar dependencias si es necesario
echo -e "${BLUE}📦 Verificando dependencias...${NC}"
# Instalar EPEL primero (requerido para tcpreplay)
ssh_exec "sudo amazon-linux-extras install epel -y >/dev/null 2>&1 || true" >/dev/null 2>&1
# Instalar tcpreplay y otras dependencias
DEP_OUTPUT=$(ssh_exec "sudo yum install -y tcpreplay tcpdump iproute 2>&1" 2>&1)
DEP_EXIT=$?
if [ $DEP_EXIT -eq 0 ] || echo "$DEP_OUTPUT" | grep -q "already installed\|Nothing to do"; then
    echo -e "${GREEN}✅ Dependencias verificadas${NC}"
else
    # Si tcpreplay no está disponible, intentar instalar desde EPEL
    if echo "$DEP_OUTPUT" | grep -q "No package tcpreplay available"; then
        echo -e "${YELLOW}⚠️  tcpreplay no está en repositorios, intentando instalar desde EPEL...${NC}"
        ssh_exec "sudo yum install -y epel-release && sudo yum install -y tcpreplay 2>&1" >/dev/null 2>&1 || {
            echo -e "${YELLOW}⚠️  No se pudo instalar tcpreplay, pero continuando...${NC}"
        }
    fi
    echo -e "${GREEN}✅ Dependencias verificadas${NC}"
fi

# Copiar archivo PCAP
echo -e "${BLUE}📤 Copiando archivo PCAP al EC2...${NC}"
PCAP_BASENAME=$(basename "$PCAP_FILE")
if timeout 120 scp -i "$SSH_KEY" \
    -o StrictHostKeyChecking=no \
    -o UserKnownHostsFile=/dev/null \
    -o ConnectTimeout=10 \
    "$PCAP_FILE" \
    ec2-user@"$CLIENT_IP":/tmp/"$PCAP_BASENAME" >/dev/null 2>&1; then
    echo -e "${GREEN}✅ Archivo PCAP copiado${NC}"
else
    echo -e "${RED}❌ Error copiando archivo PCAP${NC}"
    exit 1
fi

# Obtener nombre de la interfaz de red
echo -e "${BLUE}🔍 Obteniendo interfaz de red...${NC}"
# Método más confiable: usar /sys/class/net (disponible en todos los Linux modernos)
INTERFACE=$(ssh_exec "ls /sys/class/net 2>/dev/null | grep -v lo | grep -v docker | head -1" 2>/dev/null)
if [ -z "$INTERFACE" ] || [ "$INTERFACE" = "" ]; then
    # Fallback: intentar con ip route (si iproute2 está instalado)
    INTERFACE=$(ssh_exec "ip route show default 2>/dev/null | awk '/default/ {print \$5}' | head -1" 2>/dev/null)
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
    timeout 10 ssh_exec "ls -la /sys/class/net/ 2>/dev/null" || true
    exit 1
fi

echo -e "${GREEN}✅ Interfaz detectada: $INTERFACE${NC}"
echo ""

# Información del PCAP
echo -e "${BLUE}📊 Información del PCAP:${NC}"
ssh_exec "capinfos /tmp/$PCAP_BASENAME 2>/dev/null | head -5 || echo 'capinfos no disponible'" || echo ""
echo ""

# Confirmación (opcional)
if [ "$SKIP_CONFIRM" != "true" ] && [ -t 0 ]; then
    echo -e "${YELLOW}⚠️  El tráfico será enviado y reflejado automáticamente por AWS Traffic Mirroring${NC}"
    read -p "¿Continuar? (y/N): " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo -e "${YELLOW}⏭️  Envío cancelado${NC}"
        exit 0
    fi
fi

# Enviar tráfico con tcpreplay
echo ""
echo -e "${BLUE}🚀 Enviando tráfico PCAP...${NC}"
echo -e "${BLUE}   Interface: $INTERFACE${NC}"
echo -e "${BLUE}   Archivo: /tmp/$PCAP_BASENAME${NC}"
echo ""

# Opciones de tcpreplay:
# -i: interfaz
# --loop: número de veces a repetir (1 = una sola vez)
# --intf1: interfaz primaria
# --mbps: límite de velocidad (opcional)
echo -e "${BLUE}   Enviando tráfico (esto puede tardar según el tamaño del PCAP)...${NC}"
REPLAY_OUTPUT=$(ssh_exec "sudo tcpreplay -i $INTERFACE --loop=1 /tmp/$PCAP_BASENAME 2>&1" 2>&1)
REPLAY_EXIT=$?

if [ -n "$REPLAY_OUTPUT" ]; then
    echo "$REPLAY_OUTPUT"
fi

echo ""
if [ $REPLAY_EXIT -eq 0 ]; then
    echo -e "${GREEN}✅ Tráfico PCAP enviado exitosamente!${NC}"
    echo ""
    echo -e "${BLUE}🔍 Verifica los logs del sensor:${NC}"
    echo -e "${BLUE}   aws logs tail /ecs/sensor-analyzer-sensor --since 2m --format short --region us-east-1 | grep -E '(Tráfico UDP|📥|procesando batch|detección)'${NC}"
    echo ""
    echo -e "${BLUE}📊 O verifica las detecciones en la API:${NC}"
    ANALYZER_API=$(cd terraform/analizer 2>/dev/null && terraform output -raw api_base_url 2>/dev/null || echo "")
    if [ -n "$ANALYZER_API" ]; then
        echo -e "${BLUE}   $ANALYZER_API/v1/detections${NC}"
    fi
else
    if echo "$REPLAY_OUTPUT" | grep -q "TIMEOUT_OR_ERROR"; then
        echo -e "${YELLOW}⚠️  tcpreplay se agotó el tiempo o tuvo un error${NC}"
    else
        echo -e "${YELLOW}⚠️  tcpreplay terminó con código: $REPLAY_EXIT${NC}"
        echo -e "${YELLOW}   (Esto puede ser normal si el PCAP tiene paquetes que no se pueden enviar)${NC}"
    fi
fi

echo ""

echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}✅ Paso 5 completado${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"


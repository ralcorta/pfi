#!/bin/bash
#
# Script para emular tráfico de red normal desde el EC2 del cliente
# El tráfico será reflejado automáticamente por AWS Traffic Mirroring al sensor
#

set -e

# Configuración
CLIENT_IP="${CLIENT_IP:-34.228.104.92}"
CLIENT_USER="${CLIENT_USER:-ec2-user}"

# Buscar clave PEM en Downloads
SSH_KEY_PATH=""
for pem_file in ~/Downloads/*.pem ~/Downloads/*.PEM ~/Downloads/vockey*.pem; do
    if [ -f "$pem_file" ]; then
        SSH_KEY_PATH="$pem_file"
        break
    fi
done

if [ -z "$SSH_KEY_PATH" ] || [ ! -f "$SSH_KEY_PATH" ]; then
    echo "❌ No se encontró clave PEM en ~/Downloads/"
    echo "   Por favor, especifica la ruta con: SSH_KEY_PATH=/ruta/a/clave.pem"
    exit 1
fi

echo "=========================================="
echo "🚀 Emulando Tráfico de Red Normal"
echo "=========================================="
echo "Cliente EC2: ${CLIENT_USER}@${CLIENT_IP}"
echo "Clave SSH: ${SSH_KEY_PATH}"
echo ""

# Asegurar permisos correctos
chmod 600 "${SSH_KEY_PATH}" 2>/dev/null || true

# Función para ejecutar comandos remotos
ssh_exec() {
    ssh -i "${SSH_KEY_PATH}" \
        -o StrictHostKeyChecking=no \
        -o UserKnownHostsFile=/dev/null \
        -o ConnectTimeout=10 \
        -o LogLevel=ERROR \
        "${CLIENT_USER}@${CLIENT_IP}" \
        "$@"
}

# Verificar conectividad
echo "📡 Conectando al EC2..."
if ! ssh_exec "echo '✅ Conexión exitosa'" > /dev/null 2>&1; then
    echo "❌ No se pudo conectar al EC2"
    echo "   Verifica que:"
    echo "   1. El EC2 esté corriendo"
    echo "   2. La IP sea correcta: ${CLIENT_IP}"
    echo "   3. El Security Group permita SSH desde tu IP"
    exit 1
fi

echo "✅ Conectado al EC2"
echo ""

# Instalar dependencias si es necesario
echo "📦 Verificando dependencias..."
ssh_exec "sudo yum install -y python3 python3-pip curl wget bind-utils > /dev/null 2>&1 || true" > /dev/null 2>&1
ssh_exec "python3 -m pip install --user requests > /dev/null 2>&1 || true" > /dev/null 2>&1

echo "✅ Dependencias listas"
echo ""

# Script Python remoto para generar tráfico
echo "📝 Creando script de generación de tráfico..."
ssh_exec "cat > /tmp/generate_traffic.py << 'PYEOF'
#!/usr/bin/env python3
\"\"\"
Genera tráfico de red normal para probar Traffic Mirroring.
El tráfico será reflejado automáticamente al sensor.
\"\"\"

import subprocess
import time
import socket
import sys
from datetime import datetime

def log(msg):
    print(f\"[{datetime.now().strftime('%H:%M:%S')}] {msg}\")

def http_traffic():
    \"\"\"Genera tráfico HTTP hacia sitios públicos.\"\"\"
    log(\"🌐 Generando tráfico HTTP...\")
    
    sites = [
        \"http://www.google.com\",
        \"http://www.amazon.com\",
        \"http://www.github.com\",
        \"http://www.stackoverflow.com\",
        \"http://www.wikipedia.org\",
    ]
    
    for site in sites:
        try:
            result = subprocess.run(
                [\"curl\", \"-s\", \"-o\", \"/dev/null\", \"-w\", \"%{http_code}\", \"--connect-timeout\", \"5\", site],
                timeout=10,
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                log(f\"  ✓ GET {site} -> {result.stdout.strip()}\")
            else:
                log(f\"  ⚠ GET {site} -> Error\")
        except Exception as e:
            log(f\"  ✗ Error con {site}: {str(e)}\")
        time.sleep(0.5)

def dns_traffic():
    \"\"\"Genera consultas DNS.\"\"\"
    log(\"🔍 Generando tráfico DNS...\")
    
    domains = [
        \"google.com\",
        \"amazon.com\",
        \"github.com\",
        \"wikipedia.org\",
    ]
    
    dns_servers = [\"8.8.8.8\", \"1.1.1.1\", \"208.67.222.222\"]
    
    for domain in domains:
        for dns_server in dns_servers:
            try:
                result = subprocess.run(
                    [\"dig\", f\"@{dns_server}\", domain, \"+short\", \"+timeout=3\"],
                    timeout=5,
                    capture_output=True,
                    text=True
                )
                if result.returncode == 0 and result.stdout.strip():
                    log(f\"  ✓ DNS {domain} @{dns_server} -> {result.stdout.strip()[:50]}\")
                else:
                    log(f\"  ⚠ DNS {domain} @{dns_server} -> Sin respuesta\")
            except Exception as e:
                log(f\"  ✗ Error DNS {domain}: {str(e)}\")
            time.sleep(0.3)

def icmp_traffic():
    \"\"\"Genera tráfico ICMP (ping).\"\"\"
    log(\"📡 Generando tráfico ICMP (ping)...\")
    
    targets = [\"8.8.8.8\", \"1.1.1.1\", \"208.67.222.222\"]
    
    for target in targets:
        try:
            result = subprocess.run(
                [\"ping\", \"-c\", \"2\", \"-W\", \"2\", target],
                timeout=10,
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                log(f\"  ✓ Ping a {target} exitoso\")
            else:
                log(f\"  ⚠ Ping a {target} falló\")
        except Exception as e:
            log(f\"  ✗ Error ping {target}: {str(e)}\")
        time.sleep(1)

def tcp_traffic():
    \"\"\"Genera conexiones TCP hacia puertos comunes.\"\"\"
    log(\"🔌 Generando tráfico TCP...\")
    
    targets = [
        (\"www.google.com\", 80),
        (\"www.github.com\", 443),
    ]
    
    for host, port in targets:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(3)
            result = sock.connect_ex((host, port))
            sock.close()
            
            if result == 0:
                log(f\"  ✓ TCP conexión a {host}:{port} exitosa\")
            else:
                log(f\"  ⚠ TCP conexión a {host}:{port} falló\")
        except Exception as e:
            log(f\"  ✗ Error TCP {host}:{port}: {str(e)}\")
        time.sleep(0.5)

def main():
    print(\"=\" * 60)
    print(\"🚀 Iniciando generación de tráfico normal\")
    print(\"=\" * 60)
    print(\"Este tráfico será reflejado por AWS Traffic Mirroring\")
    print(\"y debería ser capturado por el sensor en el analizador.\")
    print(\"\")
    
    try:
        # Generar diferentes tipos de tráfico
        http_traffic()
        print(\"\")
        
        dns_traffic()
        print(\"\")
        
        icmp_traffic()
        print(\"\")
        
        tcp_traffic()
        print(\"\")
        
        print(\"=\" * 60)
        print(\"✅ Generación de tráfico completada\")
        print(\"=\" * 60)
        print(\"\")
        print(\"💡 Verifica las detecciones en el sensor:\")
        print(\"   http://sensor-analyzer-app-nlb-7ce581641caa78f5.elb.us-east-1.amazonaws.com/detections\")
        print(\"\")
        
    except KeyboardInterrupt:
        print(\"\\n⚠️  Interrupción por usuario\")
        sys.exit(0)
    except Exception as e:
        print(f\"\\n❌ Error: {e}\")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == \"__main__\":
    main()
PYEOF
"

# Hacer ejecutable
ssh_exec "chmod +x /tmp/generate_traffic.py"

# Ejecutar el script
echo "🚀 Ejecutando generación de tráfico normal..."
echo ""

ssh_exec "python3 /tmp/generate_traffic.py"

echo ""
echo "=========================================="
echo "✅ Prueba completada"
echo "=========================================="
echo ""
echo "📊 Para verificar las detecciones:"
echo "   curl http://sensor-analyzer-app-nlb-7ce581641caa78f5.elb.us-east-1.amazonaws.com/health"
echo ""
echo "   O ejecuta:"
echo "   python scripts/test_aws_users.py"
echo ""


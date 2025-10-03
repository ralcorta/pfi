#!/bin/bash

# Script para testear el sensor de ransomware
# Opciones: demo mode, UDP traffic, local testing

set -e

echo "🧪 Test del Sensor de Ransomware"
echo "================================"

# Función para mostrar ayuda
show_help() {
    echo "Uso: $0 [OPCIÓN]"
    echo ""
    echo "Opciones:"
    echo "  demo     - Testear con archivos .pcap (modo demo)"
    echo "  udp      - Testear con tráfico UDP simulado"
    echo "  stop     - Detener todos los contenedores"
    echo "  logs     - Ver logs del sensor"
    echo "  clean    - Limpiar cache de Docker y rebuild"
    echo "  check    - Verificar detecciones de malware en DynamoDB"
    echo "  demo-on  - Habilitar modo demo"
    echo "  demo-off - Deshabilitar modo demo"
    echo "  demo-status - Ver estado del modo demo"
    echo ""
    echo "Ejemplos:"
    echo "  $0 demo    # Testear con Zeus.pcap"
    echo "  $0 udp     # Enviar tráfico UDP simulado"
}

# Función para testear con demo
test_demo() {
    echo "🎭 Activando modo demo..."
    
    # Inicializar DynamoDB si no existe
    echo "⏳ Inicializando DynamoDB..."
    docker-compose up -d dynamodb-local
    sleep 5
    
    # Inicializar tabla DynamoDB
    echo "⏳ Creando tabla DynamoDB..."
    poetry run python scripts/init_local_dynamo.py
    
    echo "🚀 Ejecutando sensor en modo demo..."
    docker-compose up sensor-app-mock
}

# Función para testear con UDP
test_udp() {
    echo "📡 Testeando con tráfico UDP..."
    
    # Enviar tráfico UDP
    echo "🎯 Enviando tráfico UDP simulado..."
    poetry run python scripts/test_udp_traffic.py --host localhost --port 4789 --duration 30
    
    echo "📊 Verificando detecciones en DynamoDB..."
    poetry run python scripts/check_malware_detections.py
}

# Función para ver logs
show_logs() {
    echo "📋 Mostrando logs del sensor..."
    docker-compose logs -f sensor-app-mock
}

# Función para limpiar cache
clean_cache() {
    echo "🧹 Limpiando cache de Docker..."
    docker-compose down
    docker system prune -f
    docker-compose build --no-cache sensor-app-mock
    echo "✅ Cache limpiada y rebuild completado"
}

# Procesar argumentos
case "${1:-help}" in
    "demo")
        test_demo
        ;;
    "udp")
        test_udp
        ;;
    "logs")
        show_logs
        ;;
    "clean")
        clean_cache
        ;;
    "check")
        echo "📊 Verificando detecciones de malware..."
        poetry run python scripts/check_malware_detections.py
        ;;
    "demo-on")
        echo "🎭 Habilitando modo demo..."
        echo "⏳ Asegurando que DynamoDB local esté corriendo..."
        poetry run python scripts/enable_demo.py enable --pcap /app/models/data/small/Malware/Zeus.pcap
        ;;
    "demo-off")
        echo "🛡️ Deshabilitando modo demo..."
        echo "⏳ Asegurando que DynamoDB local esté corriendo..."
        poetry run python scripts/enable_demo.py disable
        ;;
    "demo-status")
        echo "📊 Verificando estado del modo demo..."
        echo "⏳ Asegurando que DynamoDB local esté corriendo..."
        docker-compose up -d dynamodb-local
        sleep 3
        poetry run python scripts/enable_demo.py status
        ;;
    "help"|*)
        show_help
        ;;
esac

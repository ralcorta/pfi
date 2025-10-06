#!/bin/bash

# 🔄 Script de Redeploy de la Aplicación
# Este script hace build, push y redeploy de la aplicación con nuevo código

set -e

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m' # No Color

# Función para imprimir mensajes
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_step() {
    echo -e "${PURPLE}[STEP]${NC} $1"
}

# Obtener información de la cuenta
get_account_info() {
    print_status "Obteniendo información de la cuenta AWS..."
    
    ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text 2>/dev/null)
    REGION=$(aws configure get region 2>/dev/null || echo "us-east-1")
    
    if [ -z "$ACCOUNT_ID" ]; then
        print_error "No se pudo obtener Account ID"
        exit 1
    fi
    
    print_success "Account ID: $ACCOUNT_ID"
    print_success "Región: $REGION"
}

# Paso 1: Build de nueva imagen
build_image() {
    print_step "🐳 PASO 1: Construyendo nueva imagen Docker..."
    
    print_status "Construyendo imagen Docker..."
    docker build -t mirror-sensor .
    print_success "Imagen construida"
    
    # Tag de la imagen
    print_status "Etiquetando imagen..."
    docker tag mirror-sensor:latest $ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/mirror-sensor:latest
    print_success "Imagen etiquetada"
    
    print_success "✅ Build completado"
}

# Paso 2: Login a ECR y Push
push_image() {
    print_step "📤 PASO 2: Subiendo imagen a ECR..."
    
    # Login a ECR
    print_status "Haciendo login a ECR..."
    aws ecr get-login-password --region $REGION | docker login --username AWS --password-stdin $ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com
    print_success "Login a ECR exitoso"
    
    # Push de la imagen
    print_status "Subiendo imagen a ECR..."
    docker push $ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/mirror-sensor:latest
    print_success "Imagen subida a ECR"
    
    print_success "✅ Push completado"
}

# Paso 3: Forzar nuevo deployment de ECS
redeploy_ecs() {
    print_step "🚀 PASO 3: Forzando nuevo deployment de ECS..."
    
    print_status "Forzando nuevo deployment del servicio ECS..."
    aws ecs update-service \
        --cluster mirror-cluster \
        --service mirror-sensor \
        --force-new-deployment \
        --region $REGION
    
    print_success "Nuevo deployment iniciado"
    print_status "El deployment está en progreso. Puedes verificar el estado con:"
    print_status "  aws ecs describe-services --cluster mirror-cluster --services mirror-sensor"
}

# Paso 4: Verificar deployment
verify_deployment() {
    print_step "✅ PASO 4: Verificando deployment..."
    
    # Verificar estado de ECS
    print_status "Verificando estado de ECS..."
    ECS_STATUS=$(aws ecs describe-services --cluster mirror-cluster --services mirror-sensor --query 'services[0].runningCount' --output text)
    
    if [ "$ECS_STATUS" = "1" ]; then
        print_success "ECS Service ejecutándose correctamente"
    else
        print_warning "ECS Service no está ejecutándose correctamente (runningCount: $ECS_STATUS)"
    fi
    
    # Obtener URL del ALB
    print_status "Obteniendo URL del ALB..."
    ALB_DNS=$(cd terraform/env && terraform output -raw alb_dns 2>/dev/null || echo "No disponible")
    
    if [ "$ALB_DNS" != "No disponible" ]; then
        print_success "ALB DNS: $ALB_DNS"
        
        # Probar endpoint de health
        print_status "Probando endpoint de health..."
        sleep 10  # Esperar un poco más para que el ALB se propague
        
        if curl -s "http://$ALB_DNS/health" > /dev/null; then
            print_success "Endpoint de health respondiendo"
        else
            print_warning "Endpoint de health no responde aún (puede tardar unos minutos)"
        fi
        
        # Probar nuevo endpoint de demo
        print_status "Probando nuevo endpoint de demo..."
        if curl -s "http://$ALB_DNS/demo/status" > /dev/null; then
            print_success "Endpoint de demo respondiendo"
        else
            print_warning "Endpoint de demo no responde aún"
        fi
    else
        print_warning "No se pudo obtener DNS del ALB"
    fi
    
    print_success "✅ Verificación completada"
}

# Mostrar información final
show_final_info() {
    echo ""
    echo "🎉 ¡REDEPLOY EXITOSO!"
    echo "===================="
    echo ""
    echo "📋 Información del deployment:"
    echo "  - Account ID: $ACCOUNT_ID"
    echo "  - Región: $REGION"
    echo "  - Nueva imagen: $ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/mirror-sensor:latest"
    echo ""
    echo "🌐 URLs de acceso:"
    ALB_DNS=$(cd terraform/env && terraform output -raw alb_dns 2>/dev/null || echo "No disponible")
    if [ "$ALB_DNS" != "No disponible" ]; then
        echo "  - Health Check: http://$ALB_DNS/health"
        echo "  - Detecciones: http://$ALB_DNS/detections"
        echo "  - Demo Status: http://$ALB_DNS/demo/status"
        echo "  - Demo Start: POST http://$ALB_DNS/demo/start"
        echo "  - Demo Stop: POST http://$ALB_DNS/demo/stop"
        echo "  - Demo Toggle: POST http://$ALB_DNS/demo/toggle"
    else
        echo "  - Ejecuta 'terraform output alb_dns' para obtener la URL"
    fi
    echo ""
    echo "🔧 Comandos útiles:"
    echo "  - Ver estado: make check-aws-status"
    echo "  - Ver logs: aws logs tail /aws/ecs/net-mirror-sensor --follow"
    echo "  - Demo start: make demo-start"
    echo "  - Demo stop: make demo-stop"
    echo "  - Demo status: make demo-status"
    echo ""
    echo "⚠️  Nota: Los nuevos endpoints pueden tardar 1-2 minutos en estar completamente disponibles"
}

# Función principal
main() {
    echo "🔄 REDEPLOY DE LA APLICACIÓN"
    echo "============================="
    echo ""
    echo "Este script va a:"
    echo "  1. 🐳 Construir nueva imagen Docker con el código actualizado"
    echo "  2. 📤 Subir la imagen a ECR"
    echo "  3. 🚀 Forzar nuevo deployment de ECS (detendrá las tareas actuales)"
    echo "  4. ✅ Verificar que todo funcione correctamente"
    echo ""
    print_warning "⚠️  ADVERTENCIA: Esto detendrá las tareas ECS actuales y las reemplazará con nuevas"
    echo ""
    read -p "¿Continuar con el redeploy? (y/N): " -n 1 -r
    echo ""
    
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        print_warning "Redeploy cancelado"
        exit 0
    fi
    
    echo ""
    print_status "🚀 Iniciando redeploy de la aplicación..."
    echo ""
    
    get_account_info
    build_image
    push_image
    redeploy_ecs
    verify_deployment
    show_final_info
}

# Ejecutar script
main "$@"

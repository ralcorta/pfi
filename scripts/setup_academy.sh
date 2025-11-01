#!/bin/bash

# ========================================
# Script principal para configurar AWS Academy
# ========================================
# Este script ofrece dos opciones:
# 1. Crear todos los recursos necesarios
# 2. Buscar recursos existentes y actualizar terraform.tfvars

set -e  # Exit on any error

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m' # No Color

# Función para mostrar banner
show_banner() {
    echo -e "${PURPLE}"
    echo "╔══════════════════════════════════════════════════════════════╗"
    echo "║                    AWS Academy Setup                        ║"
    echo "║              Configuración Terraform PFI-Sensor             ║"
    echo "╚══════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
}

# Función para logging
log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

success() {
    echo -e "${GREEN}✅ $1${NC}"
}

warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

error() {
    echo -e "${RED}❌ $1${NC}"
    exit 1
}

# Función para mostrar menú
show_menu() {
    echo ""
    echo -e "${BLUE}Selecciona una opción:${NC}"
    echo ""
    echo "1. 🚀 Crear todos los recursos necesarios (recomendado para primera vez)"
    echo "2. 🔍 Buscar recursos existentes y actualizar terraform.tfvars"
    echo "3. 📋 Mostrar información sobre los recursos necesarios"
    echo "4. ❌ Salir"
    echo ""
}

# Función para verificar AWS CLI
check_aws_cli() {
    log "Verificando configuración de AWS CLI..."
    
    if ! command -v aws &> /dev/null; then
        error "AWS CLI no está instalado. Instálalo desde: https://aws.amazon.com/cli/"
    fi
    
    if ! aws sts get-caller-identity &> /dev/null; then
        error "AWS CLI no está configurado o las credenciales no son válidas. Ejecuta: aws configure"
    fi
    
    local caller_identity=$(aws sts get-caller-identity --query 'Arn' --output text)
    success "AWS CLI configurado correctamente"
    log "Usuario actual: $caller_identity"
}

# Función para mostrar información sobre recursos necesarios
show_resources_info() {
    echo ""
    echo -e "${BLUE}📋 Recursos necesarios para AWS Academy:${NC}"
    echo ""
    echo -e "${YELLOW}VPCs y Redes:${NC}"
    echo "  • VPC Analizador (10.0.0.0/16)"
    echo "  • VPC Cliente (10.1.0.0/16)"
    echo "  • 4 Subnets (2 públicas, 2 privadas)"
    echo "  • 2 Internet Gateways"
    echo "  • 4 Route Tables"
    echo ""
    echo -e "${YELLOW}Servicios AWS:${NC}"
    echo "  • ECR Repository (mirror-sensor)"
    echo "  • ECS Cluster (pfi-sensor-cluster)"
    echo "  • CloudWatch Log Group (/ecs/pfi-sensor-sensor)"
    echo "  • Traffic Mirror Filter (pfi-sensor-cliente-filter)"
    echo ""
    echo -e "${YELLOW}Recursos que crea Terraform:${NC}"
    echo "  • Security Groups"
    echo "  • Network Load Balancer"
    echo "  • ECS Task Definition"
    echo "  • ECS Service"
    echo "  • Network Interface (ENI)"
    echo "  • Traffic Mirror Target"
    echo "  • Traffic Mirror Session"
    echo ""
    echo -e "${BLUE}💡 Nota:${NC} Los recursos de la primera lista deben crearse manualmente"
    echo "    debido a las restricciones de permisos de AWS Academy."
    echo ""
}

# Función para ejecutar script de creación
run_create_script() {
    log "Ejecutando script de creación de recursos..."
    
    if [ ! -f "scripts/setup_academy_resources.sh" ]; then
        error "No se encontró el script setup_academy_resources.sh"
    fi
    
    chmod +x scripts/setup_academy_resources.sh
    ./scripts/setup_academy_resources.sh
}

# Función para ejecutar script de búsqueda
run_find_script() {
    log "Ejecutando script de búsqueda de recursos existentes..."
    
    if [ ! -f "scripts/update_tfvars_from_existing.sh" ]; then
        error "No se encontró el script update_tfvars_from_existing.sh"
    fi
    
    chmod +x scripts/update_tfvars_from_existing.sh
    ./scripts/update_tfvars_from_existing.sh
}

# Función para verificar si terraform.tfvars existe
check_tfvars() {
    local tfvars_file="terraform/academy/terraform.tfvars"
    
    if [ -f "$tfvars_file" ]; then
        warning "El archivo terraform.tfvars ya existe"
        echo "¿Deseas continuar? Esto creará un backup del archivo actual. (y/N)"
        read -r response
        if [[ ! "$response" =~ ^[Yy]$ ]]; then
            log "Operación cancelada por el usuario"
            exit 0
        fi
    fi
}

# Función para mostrar próximos pasos
show_next_steps() {
    echo ""
    echo -e "${GREEN}🎉 ¡Configuración completada!${NC}"
    echo ""
    echo -e "${BLUE}Próximos pasos:${NC}"
    echo ""
    echo "1. 📁 Navegar al directorio de Terraform:"
    echo "   cd terraform/academy"
    echo ""
    echo "2. 🔧 Inicializar Terraform:"
    echo "   terraform init"
    echo ""
    echo "3. 📋 Revisar el plan:"
    echo "   terraform plan"
    echo ""
    echo "4. 🚀 Aplicar la configuración:"
    echo "   terraform apply"
    echo ""
    echo "5. 📊 Ver los outputs:"
    echo "   terraform output"
    echo ""
    echo -e "${YELLOW}💡 Consejos:${NC}"
    echo "  • Si encuentras errores, revisa que todos los recursos existan"
    echo "  • Los backups de terraform.tfvars se guardan automáticamente"
    echo "  • Puedes ejecutar este script nuevamente si necesitas actualizar algo"
    echo ""
}

# Función principal
main() {
    show_banner
    
    # Verificar que estamos en el directorio correcto
    if [ ! -d "scripts" ] || [ ! -d "terraform/academy" ]; then
        error "Ejecuta este script desde el directorio raíz del proyecto"
    fi
    
    # Verificar AWS CLI
    check_aws_cli
    
    # Verificar terraform.tfvars
    check_tfvars
    
    while true; do
        show_menu
        read -p "Ingresa tu opción (1-4): " choice
        
        case $choice in
            1)
                log "Opción seleccionada: Crear todos los recursos"
                run_create_script
                show_next_steps
                break
                ;;
            2)
                log "Opción seleccionada: Buscar recursos existentes"
                run_find_script
                show_next_steps
                break
                ;;
            3)
                show_resources_info
                ;;
            4)
                log "Saliendo..."
                exit 0
                ;;
            *)
                echo -e "${RED}Opción inválida. Por favor, selecciona 1, 2, 3 o 4.${NC}"
                ;;
        esac
    done
}

# Ejecutar función principal
main "$@"

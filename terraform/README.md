<<<<<<< HEAD
# Terraform - Configuración de VPCs

Este directorio contiene la configuración de Terraform para crear dos VPCs en AWS Academy.

## Estructura

- `main.tf` - Configuración principal de los recursos
- `variables.tf` - Definición de variables
- `outputs.tf` - Outputs de los recursos creados
- `terraform.tfvars.example` - Archivo de ejemplo para variables

## Recursos Creados

### VPC 1

- VPC con CIDR 10.0.0.0/16
- Subnet pública (10.0.1.0/24)
- Subnet privada (10.0.2.0/24)
- Internet Gateway
- Route Tables (pública y privada)

### VPC 2

- VPC con CIDR 10.1.0.0/16
- Subnet pública (10.1.1.0/24)
- Subnet privada (10.1.2.0/24)
- Internet Gateway
- Route Tables (pública y privada)

### Conectividad

- VPC Peering Connection entre las dos VPCs
- Rutas configuradas para comunicación entre VPCs

## Uso

1. **Configurar variables**:

   ```bash
   cp terraform.tfvars.example terraform.tfvars
   # Editar terraform.tfvars con tus valores
   ```

2. **Inicializar Terraform**:

   ```bash
   terraform init
   ```

3. **Planificar cambios**:

   ```bash
   terraform plan
   ```

4. **Aplicar configuración**:

   ```bash
   terraform apply
   ```

5. **Destruir recursos** (cuando termines):
   ```bash
   terraform destroy
   ```

## Notas para AWS Academy

- Este código está diseñado para funcionar con el rol `LabRole` de AWS Academy
- No requiere permisos adicionales más allá de los estándar de VPC
- Todos los recursos están etiquetados para facilitar la identificación
- Las VPCs están configuradas para ser completamente funcionales

## Variables Importantes

- `aws_region`: Región donde desplegar (por defecto: us-east-1)
- `project_name`: Nombre del proyecto para tagging
- `environment`: Ambiente (dev, staging, prod)
- CIDR blocks: Configurables para evitar conflictos

## Outputs

Después del despliegue, Terraform mostrará:

- IDs de las VPCs
- IDs de las subnets
- ID de la conexión de peering
- Resumen completo de recursos
=======
# Infraestructura Terraform - MVP Tesis

Esta configuración crea dos VPCs en AWS para el proyecto de tesis.

## Estructura

- **VPC Principal (10.0.0.0/16)**: Para servicios principales

  - 2 subnets públicas (10.0.1.0/24, 10.0.2.0/24)
  - 2 subnets privadas (10.0.10.0/24, 10.0.20.0/24)
  - Internet Gateway

- **VPC Secundaria (10.1.0.0/16)**: Para clientes o testing
  - 2 subnets públicas (10.1.1.0/24, 10.1.2.0/24)
  - 2 subnets privadas (10.1.10.0/24, 10.1.20.0/24)
  - Internet Gateway

## Uso

```bash
# Inicializar Terraform
terraform init

# Planificar cambios
terraform plan

# Aplicar cambios
terraform apply

# Destruir infraestructura
terraform destroy
```

## Requisitos

- AWS CLI configurado con el rol LabRole
- Terraform >= 1.0
- Acceso a la región us-east-1
>>>>>>> 9c77decf5f2f7c358ccba6c24c68b2a6f2ede750

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

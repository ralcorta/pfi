# Terraform Split - Módulos Analizador y Cliente

Esta carpeta contiene la infraestructura separada en dos módulos independientes:

- **`analizer/`**: Infraestructura del analizador (desplegar primero)
- **`client/`**: Infraestructura del cliente (desplegar después del analizador)

## Estructura

```
terraform/split/
├── analizer/              # Módulo del analizador (estado independiente)
│   ├── provider.tf
│   ├── variables.tf
│   ├── main.tf
│   └── terraform.tfvars
└── client/                # Módulo del cliente (estado independiente)
    ├── provider.tf
    ├── variables.tf
    ├── main.tf
    └── terraform.tfvars
```

## Despliegue

### 1. Desplegar Analizador

```bash
cd analizer
terraform init
terraform plan
terraform apply
```

Obtener el Traffic Mirror Target ID:

```bash
terraform output traffic_mirror_target_id
```

### 2. Desplegar Cliente

```bash
cd client
terraform init
terraform plan
terraform apply
```

El cliente obtiene automáticamente su configuración desde la API del analizador.

## Ventajas de esta Estructura

✅ **Estados separados**: Cada módulo tiene su propio estado de Terraform
✅ **Despliegues independientes**: Puedes desplegar solo el analizador sin afectar el cliente
✅ **Organización clara**: Cada módulo tiene sus propias variables y configuración
✅ **Sin dependencias de compilación**: No necesitas usar `-target` para filtrar recursos

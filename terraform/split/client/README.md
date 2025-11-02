# Módulo Cliente

Infraestructura del cliente que envía su tráfico al analizador mediante AWS Traffic Mirroring.

## Archivos

- `provider.tf`: Configuración del provider AWS + HTTP
- `variables.tf`: Variables del módulo
- `main.tf`: Recursos de infraestructura (VPC, EC2, Traffic Mirroring, etc.)
- `terraform.tfvars`: Valores de las variables

## Despliegue

### Prerrequisitos

El analizador debe estar desplegado primero y la API debe estar funcionando.

### Pasos

```bash
cd terraform/split/client

# Editar terraform.tfvars con tu email
# client_email = "tu-email@example.com"
# api_url = "http://app-nlb-dns/v1/clients/terraform-config"

# Inicializar
terraform init

# Ver plan
terraform plan

# Desplegar
terraform apply
```

## Configuración Automática vía API

El módulo consulta automáticamente la API del analizador para obtener:

- `traffic_mirror_target_id`: ID del target del analizador
- `vni_cliente`: VNI único asignado automáticamente (3001, 3002, etc.)

**Endpoint de la API**: `GET ${api_url}?email={client_email}`

**Respuesta esperada**:

```json
{
  "traffic_mirror_target_id": "tmt-0abc123",
  "vni_cliente": 3007
}
```

## Recursos Creados

- VPC del cliente (10.20.0.0/16)
- Subnets públicas/privadas
- EC2 Instance con ENI
- Traffic Mirror Filter y Rules
- Traffic Mirror Session (conecta con el analizador)
- Security Groups
- Elastic IP

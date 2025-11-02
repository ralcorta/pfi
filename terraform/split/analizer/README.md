# Módulo Analizador

Infraestructura del analizador que recibe y procesa tráfico duplicado de los clientes.

## Archivos

- `provider.tf`: Configuración del provider AWS
- `variables.tf`: Variables del módulo
- `main.tf`: Recursos de infraestructura (VPC, ECS, NLB, etc.)
- `terraform.tfvars`: Valores de las variables

## Despliegue

```bash
cd terraform/split/analizer

# Inicializar
terraform init

# Ver plan
terraform plan

# Desplegar
terraform apply
```

## Outputs Importantes

Después del despliegue, obtén el Traffic Mirror Target ID:

```bash
terraform output traffic_mirror_target_id
# Ejemplo: tmt-0a1b2c3d4e5f6g7h8
```

Este ID se usa automáticamente por la API cuando los clientes se registran.

## Recursos Creados

- VPC del analizador (10.10.0.0/16)
- Subnets públicas/privadas
- ECR repository para la imagen del sensor
- ECS Cluster + Task Definition + Service (Fargate)
- 2 Network Load Balancers (mirror_nlb y app_nlb)
- Traffic Mirror Target (para que los clientes apunten)
- Security Groups
- CloudWatch Logs

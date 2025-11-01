# 🎓 Configuración Terraform para AWS Academy

Esta configuración está diseñada específicamente para **AWS Academy/Voclabs** donde hay restricciones de permisos que impiden crear ciertos recursos programáticamente.

## 🚫 Recursos que NO se pueden crear con Terraform

Debido a las políticas restrictivas de Voclabs, estos recursos deben crearse **manualmente** en la consola AWS:

- ✅ **VPCs** (analizador y cliente)
- ✅ **Subnets** (públicas y privadas)
- ✅ **Internet Gateways**
- ✅ **ECR Repository**
- ✅ **ECS Cluster**
- ✅ **CloudWatch Log Group**
- ✅ **Traffic Mirror Filter**

## 📋 Pasos para usar esta configuración

### 1. Crear recursos manualmente en la consola AWS

#### VPCs y Subnets:

1. Crear VPC analizador (10.0.0.0/16)
2. Crear VPC cliente (10.1.0.0/16)
3. Crear subnets públicas y privadas en cada VPC
4. Crear Internet Gateways y asociarlos a las VPCs

#### ECR Repository:

```bash
aws ecr create-repository --repository-name mirror-sensor --region us-east-1
```

#### ECS Cluster:

```bash
aws ecs create-cluster --cluster-name pfi-sensor-cluster --region us-east-1
```

#### CloudWatch Log Group:

```bash
aws logs create-log-group --log-group-name /ecs/pfi-sensor-sensor --region us-east-1
```

#### Traffic Mirror Filter:

```bash
aws ec2 create-traffic-mirror-filter --description "Traffic filter for client - TCP+UDP ingress/egress" --tag-specifications 'ResourceType=traffic-mirror-filter,Tags=[{Key=Name,Value=pfi-sensor-cliente-filter}]'
```

### 2. Obtener IDs de recursos existentes

Ejecuta estos comandos para obtener los IDs:

```bash
# VPCs
aws ec2 describe-vpcs --filters "Name=tag:Name,Values=pfi-sensor-*" --query 'Vpcs[*].[VpcId,Tags[?Key==`Name`].Value|[0]]' --output table

# Subnets
aws ec2 describe-subnets --filters "Name=tag:Name,Values=pfi-sensor-*" --query 'Subnets[*].[SubnetId,Tags[?Key==`Name`].Value|[0]]' --output table

# ECR Repository
aws ecr describe-repositories --repository-names mirror-sensor --query 'repositories[0].repositoryUri' --output text

# ECS Cluster
aws ecs describe-clusters --clusters pfi-sensor-cluster --query 'clusters[0].clusterArn' --output text

# CloudWatch Log Group
aws logs describe-log-groups --log-group-name-prefix /ecs/pfi-sensor --query 'logGroups[0].logGroupName' --output text

# Traffic Mirror Filter
aws ec2 describe-traffic-mirror-filters --filters "Name=tag:Name,Values=pfi-sensor-cliente-filter" --query 'TrafficMirrorFilters[0].TrafficMirrorFilterId' --output text
```

### 3. Actualizar terraform.tfvars

Reemplaza los valores placeholder en `terraform.tfvars`:

```hcl
# Reemplazar con IDs reales
existing_vpc_analizador_id = "vpc-12345678"
existing_vpc_cliente_id    = "vpc-87654321"
# ... etc
```

### 4. Ejecutar Terraform

```bash
cd terraform/academy
terraform init
terraform plan
terraform apply
```

## 🔧 Recursos que SÍ crea Terraform

- Security Groups
- Network Load Balancer
- ECS Task Definition
- ECS Service
- Network Interface (ENI)
- Traffic Mirror Target
- Traffic Mirror Session

## 🎯 Ventajas de este enfoque

1. **Funciona con permisos restrictivos** de AWS Academy
2. **Reutiliza recursos existentes** creados manualmente
3. **Mantiene la funcionalidad completa** del sistema
4. **Fácil de mantener** y actualizar

## 🚨 Notas importantes

- Asegúrate de que los recursos existentes tengan los tags correctos
- Los CIDR blocks deben coincidir con los definidos en las variables
- El Traffic Mirror Filter debe crearse con las reglas apropiadas
- Verifica que el ECR repository tenga la imagen del sensor

## 🔍 Troubleshooting

Si encuentras errores:

1. **Verifica los IDs** en `terraform.tfvars`
2. **Confirma que los recursos existen** con los comandos AWS CLI
3. **Revisa los tags** de los recursos existentes
4. **Ejecuta `terraform plan`** antes de `apply` para verificar cambios

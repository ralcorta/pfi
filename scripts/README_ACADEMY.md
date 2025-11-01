# 🎓 Scripts para AWS Academy

Esta carpeta contiene scripts para configurar automáticamente los recursos necesarios para el proyecto PFI-Sensor en AWS Academy/Voclabs.

## 📁 Archivos incluidos

### Scripts principales

- **`setup_academy.sh`** - Script principal con menú interactivo
- **`setup_academy_resources.sh`** - Crea todos los recursos necesarios
- **`update_tfvars_from_existing.sh`** - Busca recursos existentes y actualiza terraform.tfvars

## 🚀 Uso rápido

### Opción 1: Script principal (recomendado)

```bash
cd scripts
./setup_academy.sh
```

### Opción 2: Crear recursos desde cero

```bash
cd scripts
./setup_academy_resources.sh
```

### Opción 3: Usar recursos existentes

```bash
cd scripts
./update_tfvars_from_existing.sh
```

## 📋 Recursos que crean los scripts

### Recursos de red

- ✅ **2 VPCs** (analizador y cliente)
- ✅ **4 Subnets** (2 públicas, 2 privadas)
- ✅ **2 Internet Gateways**
- ✅ **4 Route Tables** con rutas configuradas

### Servicios AWS

- ✅ **ECR Repository** (mirror-sensor)
- ✅ **ECS Cluster** (pfi-sensor-cluster)
- ✅ **CloudWatch Log Group** (/ecs/pfi-sensor-sensor)
- ✅ **Traffic Mirror Filter** con reglas TCP/UDP

## 🔧 Prerrequisitos

1. **AWS CLI configurado** con credenciales de AWS Academy
2. **Permisos necesarios** para crear recursos en AWS Academy
3. **Terraform instalado** (para el paso final)

### Verificar configuración AWS CLI

```bash
aws sts get-caller-identity
```

## 📝 Flujo de trabajo

### 1. Ejecutar script principal

```bash
cd scripts
./setup_academy.sh
```

### 2. Seleccionar opción

- **Opción 1**: Crear todos los recursos (primera vez)
- **Opción 2**: Buscar recursos existentes (si ya los creaste)
- **Opción 3**: Ver información sobre recursos necesarios

### 3. Ejecutar Terraform

```bash
cd ../terraform/academy
terraform init
terraform plan
terraform apply
```

## 🛠️ Configuración automática

Los scripts configuran automáticamente:

### CIDR Blocks

- **VPC Analizador**: 10.0.0.0/16
- **VPC Cliente**: 10.1.0.0/16
- **Subnets**: 10.0.1.0/24, 10.0.2.0/24, 10.1.1.0/24, 10.1.2.0/24

### Availability Zones

- **AZ1**: us-east-1a
- **AZ2**: us-east-1b

### Tags automáticos

Todos los recursos se crean con tags consistentes:

- `Project`: PFI-Sensor
- `Environment`: academy
- `Owner`: rodrigo
- `Purpose`: Ransomware Detection
- `Academy`: AWS Academy

## 🔍 Troubleshooting

### Error: "No se encontró VPC con nombre"

- Verifica que las VPCs existan con los nombres correctos
- Ejecuta: `aws ec2 describe-vpcs --filters "Name=tag:Name,Values=pfi-sensor-*"`

### Error: "AWS CLI no está configurado"

- Configura AWS CLI: `aws configure`
- Verifica credenciales: `aws sts get-caller-identity`

### Error: "No se encontró ECR repository"

- Crea el repository manualmente:

```bash
aws ecr create-repository --repository-name mirror-sensor --region us-east-1
```

### Error: "No se encontró ECS cluster"

- Crea el cluster manualmente:

```bash
aws ecs create-cluster --cluster-name pfi-sensor-cluster --region us-east-1
```

## 📊 Verificación de recursos

### Listar VPCs

```bash
aws ec2 describe-vpcs --filters "Name=tag:Project,Values=PFI-Sensor" --query 'Vpcs[*].[VpcId,Tags[?Key==`Name`].Value|[0]]' --output table
```

### Listar Subnets

```bash
aws ec2 describe-subnets --filters "Name=tag:Project,Values=PFI-Sensor" --query 'Subnets[*].[SubnetId,Tags[?Key==`Name`].Value|[0]]' --output table
```

### Listar ECR Repositories

```bash
aws ecr describe-repositories --query 'repositories[*].[repositoryName,repositoryUri]' --output table
```

### Listar ECS Clusters

```bash
aws ecs list-clusters --query 'clusterArns[*]' --output table
```

## 🔄 Backup y restauración

Los scripts crean automáticamente backups de `terraform.tfvars`:

- Formato: `terraform.tfvars.backup.YYYYMMDD_HHMMSS`
- Ubicación: `../terraform/academy/`

### Restaurar backup

```bash
cp ../terraform/academy/terraform.tfvars.backup.YYYYMMDD_HHMMSS ../terraform/academy/terraform.tfvars
```

## 🎯 Ventajas de estos scripts

1. **Automatización completa** - No necesitas crear recursos manualmente
2. **Configuración consistente** - Todos los recursos tienen la misma configuración
3. **Manejo de errores** - Verifican que los recursos existan antes de usarlos
4. **Backups automáticos** - Protegen tu configuración existente
5. **Interfaz amigable** - Menú interactivo fácil de usar

## 🚨 Notas importantes

- Los scripts asumen que tienes permisos para crear recursos en AWS Academy
- Si algunos recursos ya existen, los scripts los detectarán y los reutilizarán
- Siempre revisa el plan de Terraform antes de aplicar: `terraform plan`
- Los backups se crean automáticamente antes de cualquier modificación

## 📞 Soporte

Si encuentras problemas:

1. Verifica que AWS CLI esté configurado correctamente
2. Confirma que tienes los permisos necesarios en AWS Academy
3. Revisa los logs de los scripts para identificar el error específico
4. Consulta la documentación de AWS Academy para restricciones de permisos

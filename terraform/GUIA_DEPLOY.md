# 🚀 Guía de Despliegue - AWS Academy

Guía rápida para desplegar el analizador y cliente en AWS Academy.

## 📋 Prerrequisitos

- Acceso a AWS Academy con credenciales configuradas
- Terraform instalado (>= 1.0)
- Docker instalado
- AWS CLI configurado (`aws configure`)
- Clave SSH para EC2 (`vockey` en AWS Academy)

## 🔧 Configuración Inicial

### 1. Verificar credenciales AWS

```bash
aws sts get-caller-identity
```

Debería mostrar tu Account ID.

### 2. Configurar variables (opcional)

Los valores por defecto funcionan, pero puedes editarlos:

**Analizador** (`analizer/terraform.tfvars`):

- `account_id`: Tu Account ID de AWS Academy
- `jwt_secret_key`: Cambiar en producción

**Cliente** (`client/terraform.tfvars`):

- `client_email`: Tu email (se usa para obtener configuración automática)
- `key_name`: "vockey" (clave SSH de AWS Academy)

## 📦 Paso 1: Desplegar Analizador

```bash
cd terraform/analizer

# Inicializar Terraform
terraform init

# Ver plan
terraform plan -out=tfplan

# Desplegar infraestructura
terraform apply -auto-approve tfplan
```

⏱️ **Tiempo estimado**: ~5-7 minutos

### 1.2. Construir y subir imagen Docker

```bash
cd ../..  # Volver a raíz del proyecto
bash scripts/build-and-push.sh terraform/analizer true
```

⏱️ **Tiempo estimado**: ~3-5 minutos (depende de tu conexión)

## 📦 Paso 2: Desplegar Cliente

El cliente obtiene automáticamente los valores del analizador via remote state, **no necesitas editar nada**.

```bash
cd terraform/client

# Inicializar Terraform
terraform init

# Ver plan (mostrará valores obtenidos automáticamente)
terraform plan -out=tfplan

# Desplegar
terraform apply -auto-approve tfplan
```

⏱️ **Tiempo estimado**: ~3-5 minutos

## ✅ Verificación

### Verificar outputs importantes:

**Analizador:**

```bash
cd terraform/analizer
terraform output
```

**Cliente:**

```bash
cd terraform/client
terraform output
```

### Probar tráfico reflejado:

```bash
# Obtener IP pública del cliente
CLIENT_IP=$(cd terraform/client && terraform output -raw client_instance_public_ip 2>/dev/null || aws ec2 describe-instances --instance-ids $(aws ec2 describe-instances --filters "Name=tag:Name,Values=sensor-analyzer-cliente-instance" --query 'Reservations[0].Instances[0].InstanceId' --output text) --query 'Reservations[0].Instances[0].PublicIpAddress' --output text)

# Ejecutar script de tráfico
CLIENT_IP=$CLIENT_IP ./scripts/emulate_normal_traffic.sh
```

### Ver logs del sensor:

```bash
aws logs tail /ecs/sensor-analyzer-sensor --follow --format short --region us-east-1 | grep -E "(Tráfico UDP|📥|UDP recibido)"
```

## 🗑️ Limpieza (Destroy)

**⚠️ IMPORTANTE: Destruir en orden inverso**

### 1. Destruir Cliente

```bash
cd terraform/client
terraform destroy -auto-approve
```

### 2. Destruir Analizador

```bash
cd terraform/analizer
terraform destroy -auto-approve
```

## 📊 Recursos Creados

### Analizador:

- VPC (10.10.0.0/16) con subnets públicas/privadas
- Transit Gateway
- ECR Repository
- ECS Cluster + Service (Fargate)
- 2 Network Load Balancers (app y mirror)
- Traffic Mirror Target
- S3 Bucket para dashboard
- CloudWatch Logs

### Cliente:

- VPC (10.20.0.0/16) con subnets públicas/privadas
- EC2 Instance (t3.micro)
- Transit Gateway Attachment
- Traffic Mirror Filter + Rules
- Traffic Mirror Session
- Elastic IP

## 🔍 Troubleshooting

### Error: "ECR repository not found"

**Solución**: Asegúrate de desplegar primero el analizador completo.

### Error: "Traffic Mirror Session failed"

**Solución**: Verifica que el Transit Gateway esté completamente creado (puede tomar ~1 minuto).

### Error: "Cannot read remote state"

**Solución**: Verifica que el analizador esté desplegado y el archivo `analizer/terraform.tfstate` exista.

### El sensor no recibe tráfico

**Verificar**:

1. Transit Gateway attachments están en estado "available"
2. Traffic Mirror Session está activa
3. Security Groups permiten UDP/4789
4. NLB interno está en subnets correctas

## 📝 Notas

- **Remote State**: El cliente lee automáticamente valores del analizador (`transit_gateway_id`, `api_url`, `vpc_cidr`)
- **VNI Automático**: El sistema asigna VNIs automáticamente (3001, 3002, etc.) vía API
- **Orden de despliegue**: Siempre analizador primero, luego cliente
- **Propagación automática**: Transit Gateway propaga rutas automáticamente entre VPCs

## 🔗 URLs Importantes

Después del despliegue, guarda estas URLs:

- **API**: `http://sensor-analyzer-app-nlb-XXX.elb.us-east-1.amazonaws.com`
- **Dashboard**: `http://sensor-analyzer-dashboard-XXX.s3-website-us-east-1.amazonaws.com`
- **Health Check**: `http://sensor-analyzer-app-nlb-XXX.elb.us-east-1.amazonaws.com/health`

# 🚀 Guía Rápida de Deployment

## ⚡ Deployment Automático (Recomendado)

### Para Nueva Cuenta AWS:

```bash
# 1. Configurar AWS CLI
aws configure

# 2. Ejecutar script automático
make setup-new-account
```

### 🔄 RESET COMPLETO (Borrar todo y recrear):

```bash
# ⚠️ ADVERTENCIA: Esto borra TODO y lo vuelve a crear
make reset-complete
```

### Para Limpiar Todo:

```bash
make cleanup-account
```

## 🔧 Deployment Manual

### 1. Configuración Inicial

```bash
# Obtener información de la cuenta
make get-account-info

# Actualizar configuración ECR
make update-ecr-config
```

### 2. Build y Deploy

```bash
# Build y push de imagen
make build
make push-ecr

# Deploy de infraestructura
cd terraform/env
terraform init
terraform apply -auto-approve
cd ../..

# Inicializar aplicación
ENVIRONMENT=aws poetry run python scripts/setup_aws_records.py
```

### 3. Verificar Deployment

```bash
# Ver estado
make check-aws-status

# Obtener URL del ALB
terraform output alb_dns
```

## 🌐 Acceso a la Aplicación

Una vez desplegado, accede a:

- **Health Check**: `http://[ALB_DNS]/health`
- **Detecciones**: `http://[ALB_DNS]/detections`
- **Demo**: `http://[ALB_DNS]/demo`

## 📋 Checklist Rápido

- [ ] AWS CLI configurado
- [ ] `make setup-new-account` ejecutado
- [ ] URLs accesibles desde browser
- [ ] `make check-aws-status` muestra todo OK

## 🆘 Troubleshooting

### Error de VPC/Subnets:

```bash
make get-account-info
# Actualizar terraform/env/terraform.tfvars con los IDs correctos
```

### Error de ECR:

```bash
make update-ecr-config
```

### Error de ECS:

```bash
aws logs tail /aws/ecs/net-mirror-sensor --follow
```

---

**Para más detalles, ver [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md)**

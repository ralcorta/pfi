# 📧 Configuración de Resend.com para Envío de Emails

Guía simple para configurar el envío de emails con Resend.com.

## ⚡ Configuración Rápida

### 1. Obtener API Key de Resend

1. Ve a [resend.com](https://resend.com) y crea una cuenta
2. Ve a **API Keys** en el dashboard
3. Crea una nueva API Key
4. Copia la key (formato: `re_xxxxxxxxxxxxx`)

### 2. Verificar Dominio o Email

**Opción A: Usar dominio verificado (recomendado para producción)**

1. Ve a **Domains** en Resend
2. Agrega tu dominio
3. Configura los registros DNS según las instrucciones
4. Una vez verificado, puedes usar cualquier email @tudominio.com

**Opción B: Usar email de prueba (solo para desarrollo)**

- Resend proporciona `onboarding@resend.dev` que funciona sin verificación

### 3. Configurar Variables de Entorno

En tu despliegue (ECS, Docker, etc.):

```bash
EMAIL_ENABLED=true
EMAIL_FROM_ADDRESS=onboarding@resend.dev  # O tu email verificado
RESEND_API_KEY=re_xxxxxxxxxxxxx
```

### 4. Configurar en Terraform

Edita `terraform/analizer/terraform.tfvars`:

```hcl
enable_email_service = true
email_from_address   = "onboarding@resend.dev"
resend_api_key       = "re_xxxxxxxxxxxxx"
```

Luego aplica:

```bash
terraform apply
```

## ✅ Verificar que Funciona

1. Registra un nuevo usuario (que no exista en la base de datos)
2. Revisa los logs: deberías ver `✅ Email de bienvenida enviado a usuario@example.com`
3. El usuario recibirá el email con sus credenciales de VNI

## 🔐 Seguridad

- **Nunca** comitees la `RESEND_API_KEY` al repositorio
- Usa secretos de AWS Secrets Manager o variables de entorno en ECS
- Para Terraform, considera usar:
  - AWS Secrets Manager
  - Variables de entorno del sistema
  - `terraform.tfvars` (que debe estar en .gitignore)

## 📚 Recursos

- [Documentación de Resend](https://resend.com/docs)
- [API Reference](https://resend.com/docs/api-reference/emails/send-email)

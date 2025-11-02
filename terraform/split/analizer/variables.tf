############################################
# VARIABLES - ANALIZADOR
############################################

variable "aws_region" { default = "us-east-1" }
variable "account_id" { default = "339712899854" }
variable "project_name" { default = "sensor-analyzer" }
variable "environment" { default = "production" }
variable "tags" {
  description = "Tagging por defecto"
  type        = map(string)
  default     = {}
}

############################################
# AVAILABILITY ZONES
############################################
variable "availability_zone_1" {
  description = "Primera zona de disponibilidad"
}
variable "availability_zone_2" {
  description = "Segunda zona de disponibilidad"
}

############################################
# VPC ANALIZADOR
############################################
variable "vpc_1_cidr" { default = "10.10.0.0/16" }
variable "vpc_1_public_subnet_cidr" { default = "10.10.1.0/24" }
variable "vpc_1_private_subnet_cidr" { default = "10.10.2.0/24" }

############################################
# EMAIL SERVICE (Resend.com)
############################################
variable "enable_email_service" {
  description = "Habilitar servicio de email con Resend.com"
  type        = bool
  default     = false
}

variable "email_from_address" {
  description = "Dirección de email desde la cual se enviarán los emails (debe estar verificada en Resend)"
  type        = string
  default     = ""
}

variable "resend_api_key" {
  description = "API Key de Resend.com para envío de emails"
  type        = string
  default     = ""
  sensitive   = true
}

############################################
# JWT AUTHENTICATION
############################################
variable "jwt_secret_key" {
  description = "Clave secreta para firmar tokens JWT (debe ser segura y única en producción)"
  type        = string
  sensitive   = true
  default     = "SECRET"
}

variable "jwt_expire_minutes" {
  description = "Tiempo de expiración de tokens JWT en minutos"
  type        = number
  default     = 1440
}

############################################
# URLs (Auto-configuradas si están vacías)
############################################
variable "base_url" {
  description = "URL base de la API (ej: https://api.example.com). Si está vacío (default), se usará automáticamente la URL del NLB (http://app-nlb-dns-name). Esta URL se usa para generar los enlaces en los emails de bienvenida."
  type        = string
  default     = ""
}

variable "dashboard_url" {
  description = "URL del dashboard frontend (ej: https://dashboard.example.com). Si está vacío (default), se usará automáticamente la URL del bucket S3 website endpoint. Esta URL se usa para generar los enlaces en los emails de bienvenida y se genera automáticamente después de crear el bucket S3."
  type        = string
  default     = ""
}



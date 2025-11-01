# =========================
# Configuración general
# =========================
variable "tags" {
  description = "Tagging por defecto"
  type        = map(string)
  default     = {}
}

variable "aws_region" {
  description = "Región AWS"
  type        = string
  default     = "us-east-1"
}

variable "account_id" {
  description = "AWS Account ID (para LabRole)"
  type        = string
}

variable "project_name" {
  description = "Nombre del proyecto para tags y nombres"
  type        = string
  default     = "pfi-project"
}

variable "environment" {
  description = "Ambiente (dev, staging, prod)"
  type        = string
  default     = "dev"
}

# Clave SSH para la instancia cliente (EC2)
variable "key_name" {
  description = "Nombre de la key pair para SSH en la EC2 cliente"
  type        = string
  default     = "vockey"
}

# =========================
# VPC Analizador (VPC 1)
# =========================
variable "vpc_1_cidr" {
  description = "CIDR de la VPC Analizador"
  type        = string
  default     = "10.0.0.0/16"
}

variable "vpc_1_public_subnet_cidr" {
  description = "CIDR de la subnet pública de la VPC Analizador"
  type        = string
  default     = "10.0.1.0/24"
}

variable "vpc_1_private_subnet_cidr" {
  description = "CIDR de la subnet privada de la VPC Analizador"
  type        = string
  default     = "10.0.2.0/24"
}

# =========================
# VPC Cliente (VPC 2)
# =========================
variable "vpc_2_cidr" {
  description = "CIDR de la VPC Cliente"
  type        = string
  default     = "10.1.0.0/16"
}

variable "vpc_2_public_subnet_cidr" {
  description = "CIDR de la subnet pública de la VPC Cliente"
  type        = string
  default     = "10.1.1.0/24"
}

variable "vpc_2_private_subnet_cidr" {
  description = "CIDR de la subnet privada de la VPC Cliente"
  type        = string
  default     = "10.1.2.0/24"
}

# =========================
# Availability Zones
# =========================
variable "availability_zone_1" {
  description = "Primera AZ"
  type        = string
  default     = "us-east-1a"
}

variable "availability_zone_2" {
  description = "Segunda AZ"
  type        = string
  default     = "us-east-1b"
}

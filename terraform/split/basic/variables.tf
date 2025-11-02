############################################
# VARIABLES
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
# AVAILABILITY ZONES (compartidas)
############################################
variable "availability_zone_1" {
  description = "Primera zona de disponibilidad"
}
variable "availability_zone_2" {
  description = "Segunda zona de disponibilidad"
}

############################################
# ANALIZADOR
############################################
variable "vpc_1_cidr" { default = "10.10.0.0/16" }
variable "vpc_1_public_subnet_cidr" { default = "10.10.1.0/24" }
variable "vpc_1_private_subnet_cidr" { default = "10.10.2.0/24" }

############################################
# CLIENTE
############################################
variable "vpc_2_cidr" { default = "10.20.0.0/16" }
variable "vpc_2_public_subnet_cidr" { default = "10.20.1.0/24" }
variable "vpc_2_private_subnet_cidr" { default = "10.20.2.0/24" }
variable "key_name" {
  description = "Nombre de la clave SSH para instancias EC2"
}
variable "client_ami_id" {
  default     = "ami-0c02fb55956c7d316" # AL2 us-east-1
  description = "AMI ID para la instancia cliente"
}

############################################
# TRAFFIC MIRRORING (Configuración automática vía API)
############################################
variable "client_email" {
  description = "Email del cliente registrado en el dashboard para obtener config automática"
  type        = string
}

variable "api_url" {
  description = "URL base de la API para obtener la configuracion del cliente para Terraform"
  type        = string
}

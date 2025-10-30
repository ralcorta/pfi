# Variables de configuración general
variable "tags" {
  type    = map(string)
  default = {}
}

variable "aws_region" {
  description = "AWS region where resources will be deployed"
  type        = string
  default     = "us-east-1"
}

variable "account_id" {
  description = "AWS Account ID"
  type        = string
}

variable "project_name" {
  description = "Nombre del proyecto para el tagging de recursos"
  type        = string
  default     = "pfi-project"
}

variable "environment" {
  description = "Ambiente de despliegue (dev, staging, prod)"
  type        = string
  default     = "dev"
}

# Variables para VPC 1
variable "vpc_1_cidr" {
  description = "CIDR block para VPC 1"
  type        = string
  default     = "10.0.0.0/16"
}

variable "vpc_1_public_subnet_cidr" {
  description = "CIDR block for VPC 1 public subnet"
  type        = string
  default     = "10.0.1.0/24"
}

variable "vpc_1_private_subnet_cidr" {
  description = "CIDR block para la subnet privada de VPC 1"
  type        = string
  default     = "10.0.2.0/24"
}

# Variables para VPC 2 (Cliente)
variable "vpc_2_cidr" {
  description = "CIDR block para VPC 2 (Cliente)"
  type        = string
  default     = "10.1.0.0/16"
}

variable "vpc_2_public_subnet_cidr" {
  description = "CIDR block for VPC 2 (Client) public subnet"
  type        = string
  default     = "10.1.1.0/24"
}

variable "vpc_2_private_subnet_cidr" {
  description = "CIDR block para la subnet privada de VPC 2 (Cliente)"
  type        = string
  default     = "10.1.2.0/24"
}

# Variables para VPC Mirroring
variable "mirror_target_ip" {
  description = "IP privada para el ENI Mirror Target"
  type        = string
  default     = "10.0.2.100"
}

variable "cliente_eni_ip" {
  description = "IP privada para el ENI del Cliente"
  type        = string
  default     = "10.1.2.10"
}

variable "sensor_instance_type" {
  description = "Tipo de instancia para el sensor de IA"
  type        = string
  default     = "t3.medium"
}

variable "enable_public_access" {
  description = "Enable public access to sensor (for demos)"
  type        = bool
  default     = false
}

# Variables para Availability Zones
variable "availability_zone_1" {
  description = "Primera Availability Zone"
  type        = string
  default     = "us-east-1a"
}

variable "availability_zone_2" {
  description = "Segunda Availability Zone"
  type        = string
  default     = "us-east-1b"
}

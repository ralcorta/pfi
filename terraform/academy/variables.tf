# Variables de configuración para AWS Academy
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
  default     = "pfi-sensor"
}

variable "environment" {
  description = "Ambiente de despliegue (dev, staging, prod)"
  type        = string
  default     = "dev"
}

# Variables para VPCs existentes (IDs que debes obtener de la consola)
variable "existing_vpc_analizador_id" {
  description = "ID de la VPC analizador existente (creada manualmente)"
  type        = string
}

variable "existing_vpc_cliente_id" {
  description = "ID de la VPC cliente existente (creada manualmente)"
  type        = string
}

# Variables para subnets existentes
variable "existing_subnet_analizador_public_id" {
  description = "ID de la subnet pública del analizador"
  type        = string
}

variable "existing_subnet_analizador_private_id" {
  description = "ID de la subnet privada del analizador"
  type        = string
}

variable "existing_subnet_cliente_public_id" {
  description = "ID de la subnet pública del cliente"
  type        = string
}

variable "existing_subnet_cliente_private_id" {
  description = "ID de la subnet privada del cliente"
  type        = string
}

# Variables para recursos existentes que no se pueden crear
variable "existing_ecr_repository_name" {
  description = "Nombre del repositorio ECR existente"
  type        = string
  default     = "mirror-sensor"
}

variable "existing_ecs_cluster_name" {
  description = "Nombre del cluster ECS existente"
  type        = string
  default     = "pfi-sensor-cluster"
}

variable "existing_cloudwatch_log_group_name" {
  description = "Nombre del grupo de logs CloudWatch existente"
  type        = string
  default     = "/ecs/pfi-sensor-sensor"
}

# Variables para configuración del sensor
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

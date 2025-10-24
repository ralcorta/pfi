# Variables para el módulo VPC Secundaria

variable "project_name" {
  description = "Nombre del proyecto"
  type        = string
}

variable "vpc_cidr" {
  description = "CIDR block para VPC secundaria"
  type        = string
}

variable "availability_zones" {
  description = "Zonas de disponibilidad"
  type        = list(string)
}

variable "public_subnet_cidrs" {
  description = "CIDR blocks para subnets públicas de VPC secundaria"
  type        = list(string)
}

variable "private_subnet_cidrs" {
  description = "CIDR blocks para subnets privadas de VPC secundaria"
  type        = list(string)
}

# Variables generales
variable "aws_region" {
  description = "Región de AWS"
  type        = string
  default     = "us-east-1"
}

variable "project_name" {
  description = "Nombre del proyecto"
  type        = string
  default     = "pfi-thesis"
}

variable "availability_zones" {
  description = "Zonas de disponibilidad"
  type        = list(string)
  default     = ["us-east-1a", "us-east-1b"]
}

# Variables para VPC Principal
variable "main_vpc_cidr" {
  description = "CIDR block para VPC principal"
  type        = string
  default     = "10.0.0.0/16"
}

variable "main_public_subnet_cidrs" {
  description = "CIDR blocks para subnets públicas de VPC principal"
  type        = list(string)
  default     = ["10.0.1.0/24", "10.0.2.0/24"]
}

variable "main_private_subnet_cidrs" {
  description = "CIDR blocks para subnets privadas de VPC principal"
  type        = list(string)
  default     = ["10.0.10.0/24", "10.0.20.0/24"]
}

# Variables para VPC Secundaria
variable "secondary_vpc_cidr" {
  description = "CIDR block para VPC secundaria"
  type        = string
  default     = "10.1.0.0/16"
}

variable "secondary_public_subnet_cidrs" {
  description = "CIDR blocks para subnets públicas de VPC secundaria"
  type        = list(string)
  default     = ["10.1.1.0/24", "10.1.2.0/24"]
}

variable "secondary_private_subnet_cidrs" {
  description = "CIDR blocks para subnets privadas de VPC secundaria"
  type        = list(string)
  default     = ["10.1.10.0/24", "10.1.20.0/24"]
}

# Variables para ECS y ECR
variable "app_port" {
  description = "Puerto de la aplicación"
  type        = number
  default     = 3000
}

variable "app_count" {
  description = "Número de instancias de la aplicación"
  type        = number
  default     = 2
}

variable "fargate_cpu" {
  description = "CPU para Fargate"
  type        = number
  default     = 256
}

variable "fargate_memory" {
  description = "Memoria para Fargate"
  type        = number
  default     = 512
}

variable "health_check_path" {
  description = "Path para health check"
  type        = string
  default     = "/healthz"
}

variable "app_environment" {
  description = "Variables de entorno para la aplicación"
  type        = list(map(string))
  default     = []
}

# Variables para Autoscaling
variable "min_capacity" {
  description = "Capacidad mínima para autoscaling"
  type        = number
  default     = 1
}

variable "max_capacity" {
  description = "Capacidad máxima para autoscaling"
  type        = number
  default     = 10
}

variable "cpu_target_value" {
  description = "Valor objetivo de CPU para autoscaling"
  type        = number
  default     = 70.0
}

# Variables para Lambda
variable "lambda_zip_path" {
  description = "Ruta al archivo ZIP de la Lambda function (vacío para usar código existente)"
  type        = string
  default     = ""
}

variable "lambda_handler" {
  description = "Handler de la Lambda function (para FastAPI usar: main.handler)"
  type        = string
  default     = "main.handler"
}

variable "lambda_runtime" {
  description = "Runtime de la Lambda function"
  type        = string
  default     = "python3.9"
}

variable "lambda_timeout" {
  description = "Timeout para Lambda function en segundos"
  type        = number
  default     = 30
}

variable "lambda_memory_size" {
  description = "Memoria para Lambda function en MB"
  type        = number
  default     = 128
}

variable "dynamodb_table_name" {
  description = "Nombre de la tabla DynamoDB"
  type        = string
  default     = "pfi-thesis-table"
}

# Variables para API Gateway (FastAPI)
variable "api_stage" {
  description = "Stage para la API Gateway"
  type        = string
  default     = "prod"
}

variable "api_gateway_name" {
  description = "Nombre de la API Gateway"
  type        = string
  default     = "fastapi-lambda"
}

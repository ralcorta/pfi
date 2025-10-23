# Configuración del provider AWS
terraform {
  required_version = ">= 1.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

# Módulo VPC Primaria
module "vpc_primary" {
  source = "./modules/vpc-primary"

  project_name         = var.project_name
  vpc_cidr             = var.main_vpc_cidr
  availability_zones   = var.availability_zones
  public_subnet_cidrs  = var.main_public_subnet_cidrs
  private_subnet_cidrs = var.main_private_subnet_cidrs

  # Variables para ECS y ECR
  aws_region        = var.aws_region
  app_port          = var.app_port
  app_count         = var.app_count
  fargate_cpu       = var.fargate_cpu
  fargate_memory    = var.fargate_memory
  health_check_path = var.health_check_path
  app_environment   = var.app_environment

  # Variables para Autoscaling
  min_capacity     = var.min_capacity
  max_capacity     = var.max_capacity
  cpu_target_value = var.cpu_target_value

  # Variables para Lambda
  lambda_zip_path     = var.lambda_zip_path
  lambda_handler      = var.lambda_handler
  lambda_runtime      = var.lambda_runtime
  lambda_timeout      = var.lambda_timeout
  lambda_memory_size  = var.lambda_memory_size
  dynamodb_table_name = var.dynamodb_table_name

  # Variables para API Gateway (FastAPI)
  api_stage        = var.api_stage
  api_gateway_name = var.api_gateway_name
}

# Módulo VPC Secundaria
module "vpc_secondary" {
  source = "./modules/vpc-secondary"

  project_name         = var.project_name
  vpc_cidr             = var.secondary_vpc_cidr
  availability_zones   = var.availability_zones
  public_subnet_cidrs  = var.secondary_public_subnet_cidrs
  private_subnet_cidrs = var.secondary_private_subnet_cidrs
}

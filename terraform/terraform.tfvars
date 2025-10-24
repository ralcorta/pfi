# Configuración para el MVP de tesis
aws_region   = "us-east-1"
project_name = "pfi-thesis"

# VPC Principal (para servicios principales)
main_vpc_cidr             = "10.0.0.0/16"
main_public_subnet_cidrs  = ["10.0.1.0/24", "10.0.2.0/24"]
main_private_subnet_cidrs = ["10.0.10.0/24", "10.0.20.0/24"]

# VPC Secundaria (para clientes o testing)
secondary_vpc_cidr             = "10.1.0.0/16"
secondary_public_subnet_cidrs  = ["10.1.1.0/24", "10.1.2.0/24"]
secondary_private_subnet_cidrs = ["10.1.10.0/24", "10.1.20.0/24"]

# Configuración para cuenta AWS 339712899854
# Solo variables definidas en variables.tf

# Configuración general
aws_region   = "us-east-1"
project_name = "pfi-sensor"
environment  = "production"

# VPC 1 (Analizador)
vpc_1_cidr                = "10.0.0.0/16"
vpc_1_public_subnet_cidr  = "10.0.1.0/24"
vpc_1_private_subnet_cidr = "10.0.2.0/24"

# VPC 2 (Cliente)
vpc_2_cidr                = "10.1.0.0/16"
vpc_2_public_subnet_cidr  = "10.1.1.0/24"
vpc_2_private_subnet_cidr = "10.1.2.0/24"

# Configuración de Mirroring
mirror_target_ip = "10.0.2.100"
cliente_eni_ip   = "10.1.2.10"

# Availability Zones
availability_zone_1 = "us-east-1a"
availability_zone_2 = "us-east-1b"

# Configuración del sensor
sensor_instance_type = "t3.medium"
enable_public_access = false

# Tags
tags = {
  Project     = "PFI-Sensor"
  Environment = "production"
  Owner       = "rodrigo"
  Account     = "339712899854"
  Purpose     = "Ransomware Detection"
}

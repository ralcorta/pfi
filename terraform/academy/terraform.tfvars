# Configuración para AWS Academy (Voclabs)
# Usa recursos existentes creados manualmente en la consola

# Configuración general
aws_region   = "us-east-1"
project_name = "pfi-sensor"
environment  = "academy"
account_id   = "339712899854"

# IDs de VPCs existentes (obtener de la consola AWS)
# IMPORTANTE: Reemplaza estos valores con los IDs reales de tus VPCs
existing_vpc_analizador_id = "vpc-XXXXXXXXX" # Reemplazar con ID real
existing_vpc_cliente_id    = "vpc-YYYYYYYYY" # Reemplazar con ID real

# IDs de subnets existentes (obtener de la consola AWS)
# IMPORTANTE: Reemplaza estos valores con los IDs reales de tus subnets
existing_subnet_analizador_public_id  = "subnet-XXXXXXXXX" # Reemplazar con ID real
existing_subnet_analizador_private_id = "subnet-YYYYYYYYY" # Reemplazar con ID real
existing_subnet_cliente_public_id     = "subnet-ZZZZZZZZZ" # Reemplazar con ID real
existing_subnet_cliente_private_id    = "subnet-AAAAAAAAA" # Reemplazar con ID real

# Recursos existentes (creados manualmente)
existing_ecr_repository_name       = "mirror-sensor"
existing_ecs_cluster_name          = "pfi-sensor-cluster"
existing_cloudwatch_log_group_name = "/ecs/pfi-sensor-sensor"

# Availability Zones
availability_zone_1 = "us-east-1a"
availability_zone_2 = "us-east-1b"

# Configuración del sensor
sensor_instance_type = "t3.medium"
enable_public_access = false

# Tags
tags = {
  Project     = "PFI-Sensor"
  Environment = "academy"
  Owner       = "rodrigo"
  Account     = "339712899854"
  Purpose     = "Ransomware Detection"
  Academy     = "AWS Academy"
}

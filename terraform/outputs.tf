<<<<<<< HEAD
# Outputs para VPC Analizador
output "vpc_analizador_id" {
  description = "ID de VPC Analizador"
  value       = aws_vpc.vpc_analizador.id
}

output "vpc_analizador_cidr_block" {
  description = "CIDR block de VPC Analizador"
  value       = aws_vpc.vpc_analizador.cidr_block
}

output "vpc_analizador_public_subnet_id" {
  description = "ID de la subnet pública de VPC Analizador"
  value       = aws_subnet.analizador_public_subnet.id
}

output "vpc_analizador_private_subnet_id" {
  description = "ID de la subnet privada de VPC Analizador"
  value       = aws_subnet.analizador_private_subnet.id
}

output "vpc_analizador_internet_gateway_id" {
  description = "ID del Internet Gateway de VPC Analizador"
  value       = aws_internet_gateway.igw_analizador.id
}

# Outputs para VPC Cliente
output "vpc_cliente_id" {
  description = "ID de VPC Cliente"
  value       = aws_vpc.vpc_cliente.id
}

output "vpc_cliente_cidr_block" {
  description = "CIDR block de VPC Cliente"
  value       = aws_vpc.vpc_cliente.cidr_block
}

output "vpc_cliente_public_subnet_id" {
  description = "ID de la subnet pública de VPC Cliente"
  value       = aws_subnet.cliente_public_subnet.id
}

output "vpc_cliente_private_subnet_id" {
  description = "ID de la subnet privada de VPC Cliente"
  value       = aws_subnet.cliente_private_subnet.id
}

output "cliente_eni_id" {
  description = "ID del ENI del Cliente"
  value       = aws_network_interface.cliente_eni.id
}

output "cliente_mirror_session_id" {
  description = "ID de la VPC Mirror Session del Cliente"
  value       = aws_ec2_traffic_mirror_session.cliente_mirror.id
}

# Outputs para VPC Mirroring
output "mirror_target_eni_id" {
  description = "ID del ENI Mirror Target"
  value       = aws_network_interface.mirror_target.id
}

output "mirror_target_private_ip" {
  description = "IP privada del ENI Mirror Target"
  value       = aws_network_interface.mirror_target.private_ip
}

output "mirror_target_security_group_id" {
  description = "ID del Security Group del Mirror Target"
  value       = aws_security_group.mirror_target.id
}

output "sensor_security_group_id" {
  description = "ID del Security Group del Sensor"
  value       = aws_security_group.sensor.id
}

# Outputs de resumen
output "vpc_mirroring_summary" {
  description = "Resumen de la arquitectura VPC Mirroring"
  value = {
    vpc_analyzer = {
      id                = aws_vpc.vpc_analizador.id
      cidr_block        = aws_vpc.vpc_analizador.cidr_block
      public_subnet_id  = aws_subnet.analizador_public_subnet.id
      private_subnet_id = aws_subnet.analizador_private_subnet.id
    }
    vpc_cliente = {
      id                = aws_vpc.vpc_cliente.id
      cidr_block        = aws_vpc.vpc_cliente.cidr_block
      public_subnet_id  = aws_subnet.cliente_public_subnet.id
      private_subnet_id = aws_subnet.cliente_private_subnet.id
    }
    mirror_target = {
      eni_id            = aws_network_interface.mirror_target.id
      private_ip        = aws_network_interface.mirror_target.private_ip
      security_group_id = aws_security_group.mirror_target.id
    }
    cliente_mirror = {
      eni_id     = aws_network_interface.cliente_eni.id
      session_id = aws_ec2_traffic_mirror_session.cliente_mirror.id
      filter_id  = aws_ec2_traffic_mirror_filter.cliente_filter.id
    }
    sensor = {
      security_group_id = aws_security_group.sensor.id
    }
  }
}

# Outputs para configuración de clientes
output "client_mirror_config" {
  description = "Configuración que los clientes necesitan para VPC Mirroring"
  value = {
    target_eni_id = aws_network_interface.mirror_target.id
    target_ip     = aws_network_interface.mirror_target.private_ip
    instructions  = "Los clientes deben configurar VPC Mirror Session apuntando a este ENI"
  }
}

# Outputs para demo del cliente
output "cliente_demo_config" {
  description = "Configuración para demo del cliente"
  value = {
    vpc_id            = aws_vpc.vpc_cliente.id
    public_subnet_id  = aws_subnet.cliente_public_subnet.id
    private_subnet_id = aws_subnet.cliente_private_subnet.id
    security_group_id = aws_security_group.cliente_instances.id
    mirror_session_id = aws_ec2_traffic_mirror_session.cliente_mirror.id
    instructions      = "Esta VPC simula un cliente que envía tráfico al analizador"
  }
}

# ========================================
# OUTPUTS PARA ECR Y ECS
# ========================================

# ECR Repository
output "ecr_repository_url" {
  description = "URL del ECR repository"
  value       = aws_ecr_repository.sensor_repo.repository_url
}

output "ecr_repository_name" {
  description = "Nombre del ECR repository"
  value       = aws_ecr_repository.sensor_repo.name
}

# ECS Cluster
output "ecs_cluster_id" {
  description = "ID del ECS Cluster"
  value       = aws_ecs_cluster.sensor_cluster.id
}

output "ecs_cluster_name" {
  description = "Nombre del ECS Cluster"
  value       = aws_ecs_cluster.sensor_cluster.name
}

# ECS Service
output "ecs_service_name" {
  description = "Nombre del ECS Service"
  value       = aws_ecs_service.sensor_service.name
}

output "ecs_task_definition_arn" {
  description = "ARN de la ECS Task Definition"
  value       = aws_ecs_task_definition.sensor_task.arn
}

# CloudWatch Logs
output "cloudwatch_log_group" {
  description = "CloudWatch Log Group para el sensor"
  value       = aws_cloudwatch_log_group.sensor_logs.name
}

# ========================================
# INSTRUCCIONES DE DESPLIEGUE
# ========================================

output "deployment_instructions" {
  description = "Instrucciones para desplegar el sensor"
  value = {
    step_1           = "Desplegar infraestructura: terraform apply"
    step_2           = "Build y push imagen: ./scripts/build-and-push.sh"
    step_3           = "Verificar ECS service: aws ecs describe-services --cluster pfi-sensor-cluster"
    step_4           = "Ver logs: aws logs tail /ecs/pfi-sensor --follow"
    step_5           = "Verificar LabRole: aws sts get-caller-identity"
    ecr_repo         = aws_ecr_repository.sensor_repo.repository_url
    ecs_cluster      = aws_ecs_cluster.sensor_cluster.name
    aws_academy_note = "Usando solo LabRole - no se crean permisos adicionales"
  }
}

# ========================================
# OUTPUTS ESPECÍFICOS PARA AWS ACADEMY
# ========================================

output "aws_academy_info" {
  description = "Información específica para AWS Academy"
  value = {
    lab_role     = "LabRole (sin permisos adicionales)"
    region       = var.aws_region
    project_name = var.project_name
    environment  = var.environment
    note         = "Todos los recursos usan LabRole por defecto"
  }
=======
# Outputs para VPC Primaria (desde módulo)
output "main_vpc_id" {
  description = "ID de la VPC principal"
  value       = module.vpc_primary.vpc_id
}

output "main_vpc_cidr" {
  description = "CIDR block de la VPC principal"
  value       = module.vpc_primary.vpc_cidr
}

output "main_public_subnet_ids" {
  description = "IDs de las subnets públicas de la VPC principal"
  value       = module.vpc_primary.public_subnet_ids
}

output "main_private_subnet_ids" {
  description = "IDs de las subnets privadas de la VPC principal"
  value       = module.vpc_primary.private_subnet_ids
}

output "main_internet_gateway_id" {
  description = "ID del Internet Gateway de la VPC principal"
  value       = module.vpc_primary.internet_gateway_id
}

output "main_public_route_table_id" {
  description = "ID de la route table pública de la VPC principal"
  value       = module.vpc_primary.public_route_table_id
}

# Outputs para VPC Secundaria (desde módulo)
output "secondary_vpc_id" {
  description = "ID de la VPC secundaria"
  value       = module.vpc_secondary.vpc_id
}

output "secondary_vpc_cidr" {
  description = "CIDR block de la VPC secundaria"
  value       = module.vpc_secondary.vpc_cidr
}

output "secondary_public_subnet_ids" {
  description = "IDs de las subnets públicas de la VPC secundaria"
  value       = module.vpc_secondary.public_subnet_ids
}

output "secondary_private_subnet_ids" {
  description = "IDs de las subnets privadas de la VPC secundaria"
  value       = module.vpc_secondary.private_subnet_ids
}

output "secondary_internet_gateway_id" {
  description = "ID del Internet Gateway de la VPC secundaria"
  value       = module.vpc_secondary.internet_gateway_id
}

output "secondary_public_route_table_id" {
  description = "ID de la route table pública de la VPC secundaria"
  value       = module.vpc_secondary.public_route_table_id
}

# Outputs para ECS y ECR (VPC Primaria)
output "ecr_repository_url" {
  description = "URL del repositorio ECR"
  value       = module.vpc_primary.ecr_repository_url
}

output "ecr_repository_name" {
  description = "Nombre del repositorio ECR"
  value       = module.vpc_primary.ecr_repository_name
}

output "ecs_cluster_id" {
  description = "ID del cluster ECS"
  value       = module.vpc_primary.ecs_cluster_id
}

output "ecs_cluster_name" {
  description = "Nombre del cluster ECS"
  value       = module.vpc_primary.ecs_cluster_name
}

output "ecs_service_name" {
  description = "Nombre del servicio ECS"
  value       = module.vpc_primary.ecs_service_name
}

output "alb_dns_name" {
  description = "DNS name del ALB"
  value       = module.vpc_primary.alb_dns_name
}

output "alb_zone_id" {
  description = "Zone ID del ALB"
  value       = module.vpc_primary.alb_zone_id
}

output "alb_arn" {
  description = "ARN del ALB"
  value       = module.vpc_primary.alb_arn
}

output "target_group_arn" {
  description = "ARN del target group"
  value       = module.vpc_primary.target_group_arn
}


# Outputs para DynamoDB
output "dynamodb_table_name" {
  description = "Nombre de la tabla DynamoDB"
  value       = module.vpc_primary.dynamodb_table_name
}

output "dynamodb_table_arn" {
  description = "ARN de la tabla DynamoDB"
  value       = module.vpc_primary.dynamodb_table_arn
}

output "dynamodb_table_id" {
  description = "ID de la tabla DynamoDB"
  value       = module.vpc_primary.dynamodb_table_id
>>>>>>> 9c77decf5f2f7c358ccba6c24c68b2a6f2ede750
}

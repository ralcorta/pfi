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
  description = "ID of VPC Analyzer public subnet"
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
  description = "ID of VPC Client public subnet"
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

# output "cliente_mirror_session_id" {
#   description = "ID de la VPC Mirror Session del Cliente"
#   value       = aws_ec2_traffic_mirror_session.cliente_mirror.id
# }

# Outputs para VPC Mirroring
output "mirror_target_security_group_id" {
  description = "ID del Security Group del Mirror Target (ECS)"
  value       = aws_security_group.ecs_mirror.id
}

output "sensor_security_group_id" {
  description = "ID del Security Group del Sensor"
  value       = aws_security_group.ecs_mirror.id
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
      target_id         = aws_ec2_traffic_mirror_target.analizador_target.id
      nlb_dns_name      = aws_lb.mirror_nlb.dns_name
      security_group_id = aws_security_group.ecs_mirror.id
    }
    cliente_mirror = {
      eni_id     = aws_network_interface.cliente_eni.id
      session_id = aws_ec2_traffic_mirror_session.cliente_mirror.id
      filter_id  = aws_ec2_traffic_mirror_filter.cliente_filter.id
    }
    sensor = {
      security_group_id = aws_security_group.ecs_mirror.id
      cluster_name      = aws_ecs_cluster.sensor_cluster.name
      service_name      = aws_ecs_service.sensor_service.name
    }
  }
}

# Outputs para configuración de clientes
output "client_mirror_config" {
  description = "Configuration that clients need for VPC Mirroring"
  value = {
    target_id    = aws_ec2_traffic_mirror_target.analizador_target.id
    nlb_dns_name = aws_lb.mirror_nlb.dns_name
    instructions = "Los clientes deben configurar VPC Mirror Session apuntando a este NLB Target"
  }
}

# Outputs para demo del cliente
output "cliente_demo_config" {
  description = "Configuration for client demo"
  value = {
    vpc_id            = aws_vpc.vpc_cliente.id
    public_subnet_id  = aws_subnet.cliente_public_subnet.id
    private_subnet_id = aws_subnet.cliente_private_subnet.id
    security_group_id = aws_security_group.cliente_instances.id
    mirror_session_id = "N/A (Traffic Mirror Session disabled)"
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
# OUTPUTS PARA TRAFFIC MIRRORING CON NLB
# ========================================

output "mirror_nlb_dns" {
  description = "DNS name del NLB para Traffic Mirroring"
  value       = aws_lb.mirror_nlb.dns_name
}

output "mirror_target_id" {
  description = "ID del Traffic Mirror Target"
  value       = aws_ec2_traffic_mirror_target.analizador_target.id
}

output "vxlan_target_group_arn" {
  description = "ARN del Target Group VXLAN UDP 4789"
  value       = aws_lb_target_group.vxlan_tg.arn
}

# ========================================
# OUTPUTS ESPECÍFICOS PARA AWS ACADEMY
# ========================================

output "aws_academy_info" {
  description = "Specific information for AWS Academy"
  value = {
    lab_role     = "LabRole (sin permisos adicionales)"
    region       = var.aws_region
    project_name = var.project_name
    environment  = var.environment
    note         = "Todos los recursos usan LabRole por defecto"
  }
}

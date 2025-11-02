# =========================
# VPC Analizador
# =========================
output "vpc_analizador_id" {
  description = "ID de la VPC Analizador"
  value       = aws_vpc.vpc_analizador.id
}

output "vpc_analizador_cidr_block" {
  description = "CIDR de la VPC Analizador"
  value       = aws_vpc.vpc_analizador.cidr_block
}

output "vpc_analizador_public_subnet_id" {
  description = "Subnet pública de la VPC Analizador"
  value       = aws_subnet.analizador_public_subnet.id
}

output "vpc_analizador_private_subnet_id" {
  description = "Subnet privada de la VPC Analizador"
  value       = aws_subnet.analizador_private_subnet.id
}

output "vpc_analizador_internet_gateway_id" {
  description = "IGW de la VPC Analizador"
  value       = aws_internet_gateway.igw_analizador.id
}

# =========================
# VPC Cliente
# =========================
output "vpc_cliente_id" {
  description = "ID de la VPC Cliente"
  value       = aws_vpc.vpc_cliente.id
}

output "vpc_cliente_cidr_block" {
  description = "CIDR de la VPC Cliente"
  value       = aws_vpc.vpc_cliente.cidr_block
}

output "vpc_cliente_public_subnet_id" {
  description = "Subnet pública de la VPC Cliente"
  value       = aws_subnet.cliente_public_subnet.id
}

output "vpc_cliente_private_subnet_id" {
  description = "Subnet privada de la VPC Cliente"
  value       = aws_subnet.cliente_private_subnet.id
}

output "cliente_eni_id" {
  description = "ENI fuente de mirroring (Cliente)"
  value       = aws_network_interface.cliente_eni.id
}

output "cliente_instance_info" {
  description = "EC2 cliente (para tcpreplay y pruebas)"
  value = {
    instance_id = aws_instance.cliente_instance.id
    public_ip   = aws_eip.cliente_instance_eip.public_ip
    public_dns  = aws_eip.cliente_instance_eip.public_dns
    ssh_command = "ssh ec2-user@${aws_eip.cliente_instance_eip.public_ip}"
  }
}

# =========================
# Mirroring / NLB VXLAN
# =========================
output "mirror_target_security_group_id" {
  description = "SG del ECS (recibe VXLAN UDP/4789)"
  value       = aws_security_group.ecs_mirror.id
}

output "mirror_nlb_dns" {
  description = "DNS del NLB (UDP/4789) para Traffic Mirroring"
  value       = aws_lb.mirror_nlb.dns_name
}

output "mirror_target_id" {
  description = "ID del Traffic Mirror Target (NLB)"
  value       = aws_ec2_traffic_mirror_target.analizador_target.id
}

output "vxlan_target_group_arn" {
  description = "ARN del Target Group UDP/4789"
  value       = aws_lb_target_group.vxlan_tg.arn
}

output "cliente_mirror_session_id" {
  description = "ID de la Traffic Mirror Session del Cliente"
  value       = aws_ec2_traffic_mirror_session.cliente_mirror.id
}

# =========================
# App FastAPI (salud/diag)
# =========================
output "app_nlb_dns" {
  description = "DNS público para FastAPI (TCP/80 -> 8080)"
  value       = aws_lb.app_nlb.dns_name
}

# =========================
# ECR / ECS
# =========================
output "ecr_repository_url" {
  description = "URL del repo ECR"
  value       = aws_ecr_repository.sensor_repo.repository_url
}

output "ecr_repository_name" {
  description = "Nombre del repo ECR"
  value       = aws_ecr_repository.sensor_repo.name
}

output "ecs_cluster_id" {
  description = "ID del ECS Cluster"
  value       = aws_ecs_cluster.sensor_cluster.id
}

output "ecs_cluster_name" {
  description = "Nombre del ECS Cluster"
  value       = aws_ecs_cluster.sensor_cluster.name
}

output "ecs_service_name" {
  description = "Nombre del ECS Service"
  value       = aws_ecs_service.sensor_service.name
}

output "ecs_task_definition_arn" {
  description = "ARN de la Task Definition"
  value       = aws_ecs_task_definition.sensor_task.arn
}

# =========================
# CloudWatch Logs
# =========================
output "cloudwatch_log_group" {
  description = "Log Group del sensor"
  value       = aws_cloudwatch_log_group.sensor_logs.name
}

# =========================
# Resumen
# =========================
output "vpc_mirroring_summary" {
  description = "Resumen de mirroring y servicios"
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
    mirror = {
      target_id    = aws_ec2_traffic_mirror_target.analizador_target.id
      nlb_dns_name = aws_lb.mirror_nlb.dns_name
      tg_arn       = aws_lb_target_group.vxlan_tg.arn
      session_id   = aws_ec2_traffic_mirror_session.cliente_mirror.id
    }
    ecs = {
      cluster_name = aws_ecs_cluster.sensor_cluster.name
      service_name = aws_ecs_service.sensor_service.name
    }
  }
}

# =========================
# Info AWS Academy
# =========================
output "aws_academy_info" {
  description = "Info para despliegue con LabRole"
  value = {
    lab_role     = "LabRole (sin permisos adicionales)"
    region       = var.aws_region
    project_name = var.project_name
    environment  = var.environment
  }
}




output "nlb_vxlan_dns" {
  value = aws_lb.mirror_nlb.dns_name
}

output "cliente_public_ip" {
  value = aws_eip.cliente_instance_eip.public_ip
}

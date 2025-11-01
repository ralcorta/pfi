# Outputs para AWS Academy

output "vpc_analizador_id" {
  description = "ID de la VPC analizador"
  value       = data.aws_vpc.vpc_analizador.id
}

output "vpc_cliente_id" {
  description = "ID de la VPC cliente"
  value       = data.aws_vpc.vpc_cliente.id
}

output "ecs_cluster_name" {
  description = "Nombre del cluster ECS"
  value       = data.aws_ecs_cluster.sensor_cluster.cluster_name
}

output "ecr_repository_url" {
  description = "URL del repositorio ECR"
  value       = data.aws_ecr_repository.sensor_repo.repository_url
}

output "nlb_dns_name" {
  description = "DNS name del Network Load Balancer"
  value       = aws_lb.mirror_nlb.dns_name
}

output "nlb_arn" {
  description = "ARN del Network Load Balancer"
  value       = aws_lb.mirror_nlb.arn
}

output "traffic_mirror_target_id" {
  description = "ID del Traffic Mirror Target"
  value       = aws_ec2_traffic_mirror_target.analizador_target.id
}

output "traffic_mirror_session_id" {
  description = "ID de la Traffic Mirror Session"
  value       = aws_ec2_traffic_mirror_session.cliente_mirror.id
}

output "cliente_eni_id" {
  description = "ID del ENI del cliente"
  value       = aws_network_interface.cliente_eni.id
}

output "cliente_eni_private_ip" {
  description = "IP privada del ENI del cliente"
  value       = aws_network_interface.cliente_eni.private_ip
}

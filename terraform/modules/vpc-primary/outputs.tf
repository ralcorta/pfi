# Outputs para el módulo VPC Primaria

output "vpc_id" {
  description = "ID de la VPC principal"
  value       = aws_vpc.main_vpc.id
}

output "vpc_cidr" {
  description = "CIDR block de la VPC principal"
  value       = aws_vpc.main_vpc.cidr_block
}

output "public_subnet_ids" {
  description = "IDs de las subnets públicas de la VPC principal"
  value       = aws_subnet.public_subnets[*].id
}

output "private_subnet_ids" {
  description = "IDs de las subnets privadas de la VPC principal"
  value       = aws_subnet.private_subnets[*].id
}

output "internet_gateway_id" {
  description = "ID del Internet Gateway de la VPC principal"
  value       = aws_internet_gateway.main_igw.id
}

output "public_route_table_id" {
  description = "ID de la route table pública"
  value       = aws_route_table.public_rt.id
}

# Outputs para ECS y ECR
output "ecr_repository_url" {
  description = "URL del repositorio ECR"
  value       = aws_ecr_repository.app_repository.repository_url
}

output "ecr_repository_name" {
  description = "Nombre del repositorio ECR"
  value       = aws_ecr_repository.app_repository.name
}

output "ecs_cluster_id" {
  description = "ID del cluster ECS"
  value       = aws_ecs_cluster.main.id
}

output "ecs_cluster_name" {
  description = "Nombre del cluster ECS"
  value       = aws_ecs_cluster.main.name
}

output "ecs_service_name" {
  description = "Nombre del servicio ECS"
  value       = aws_ecs_service.main.name
}

output "alb_dns_name" {
  description = "DNS name del ALB"
  value       = aws_lb.main.dns_name
}

output "alb_zone_id" {
  description = "Zone ID del ALB"
  value       = aws_lb.main.zone_id
}

output "alb_arn" {
  description = "ARN del ALB"
  value       = aws_lb.main.arn
}

output "target_group_arn" {
  description = "ARN del target group"
  value       = aws_lb_target_group.app.arn
}


# Outputs para DynamoDB
output "dynamodb_table_name" {
  description = "Nombre de la tabla DynamoDB"
  value       = aws_dynamodb_table.main_table.name
}

output "dynamodb_table_arn" {
  description = "ARN de la tabla DynamoDB"
  value       = aws_dynamodb_table.main_table.arn
}

output "dynamodb_table_id" {
  description = "ID de la tabla DynamoDB"
  value       = aws_dynamodb_table.main_table.id
}


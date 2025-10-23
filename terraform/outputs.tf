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
}

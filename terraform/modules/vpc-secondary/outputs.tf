# Outputs para el módulo VPC Secundaria

output "vpc_id" {
  description = "ID de la VPC secundaria"
  value       = aws_vpc.secondary_vpc.id
}

output "vpc_cidr" {
  description = "CIDR block de la VPC secundaria"
  value       = aws_vpc.secondary_vpc.cidr_block
}

output "public_subnet_ids" {
  description = "IDs de las subnets públicas de la VPC secundaria"
  value       = aws_subnet.public_subnets[*].id
}

output "private_subnet_ids" {
  description = "IDs de las subnets privadas de la VPC secundaria"
  value       = aws_subnet.private_subnets[*].id
}

output "internet_gateway_id" {
  description = "ID del Internet Gateway de la VPC secundaria"
  value       = aws_internet_gateway.secondary_igw.id
}

output "public_route_table_id" {
  description = "ID de la route table pública"
  value       = aws_route_table.public_rt.id
}

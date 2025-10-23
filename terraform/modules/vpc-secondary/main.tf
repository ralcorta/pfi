# Módulo VPC Secundaria
# Este módulo contiene todos los recursos para la VPC secundaria

# VPC Secundaria
resource "aws_vpc" "secondary_vpc" {
  cidr_block           = var.vpc_cidr
  enable_dns_hostnames = true
  enable_dns_support   = true

  tags = {
    Name = "${var.project_name}-secondary-vpc"
    Type = "Secondary"
  }
}

# Internet Gateway para VPC Secundaria
resource "aws_internet_gateway" "secondary_igw" {
  vpc_id = aws_vpc.secondary_vpc.id

  tags = {
    Name = "${var.project_name}-secondary-igw"
  }
}

# Subnets públicas para VPC Secundaria
resource "aws_subnet" "public_subnets" {
  count = length(var.availability_zones)

  vpc_id                  = aws_vpc.secondary_vpc.id
  cidr_block              = var.public_subnet_cidrs[count.index]
  availability_zone       = var.availability_zones[count.index]
  map_public_ip_on_launch = true

  tags = {
    Name = "${var.project_name}-secondary-public-${count.index + 1}"
    Type = "Public"
  }
}

# Subnets privadas para VPC Secundaria
resource "aws_subnet" "private_subnets" {
  count = length(var.availability_zones)

  vpc_id            = aws_vpc.secondary_vpc.id
  cidr_block        = var.private_subnet_cidrs[count.index]
  availability_zone = var.availability_zones[count.index]

  tags = {
    Name = "${var.project_name}-secondary-private-${count.index + 1}"
    Type = "Private"
  }
}

# Route Table para subnets públicas de VPC Secundaria
resource "aws_route_table" "public_rt" {
  vpc_id = aws_vpc.secondary_vpc.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.secondary_igw.id
  }

  tags = {
    Name = "${var.project_name}-secondary-public-rt"
  }
}

# Asociación de subnets públicas con route table
resource "aws_route_table_association" "public_rta" {
  count = length(aws_subnet.public_subnets)

  subnet_id      = aws_subnet.public_subnets[count.index].id
  route_table_id = aws_route_table.public_rt.id
}

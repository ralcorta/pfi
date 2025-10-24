# ========================================
# VPC CLIENTE - SIMULACIÓN DE CLIENTE REAL
# ========================================
# Esta VPC simula un cliente que envía su tráfico al analizador
# via VPC Mirroring para detección de ransomware

# VPC del Cliente (Ejemplo)
resource "aws_vpc" "vpc_cliente" {
  cidr_block           = var.vpc_2_cidr
  enable_dns_hostnames = true
  enable_dns_support   = true

  tags = {
    Name        = "${var.project_name}-cliente-vpc"
    Environment = var.environment
    Project     = var.project_name
    Type        = "Cliente-Ejemplo"
    Purpose     = "Demo-Cliente"
  }
}

# Internet Gateway para VPC Cliente
resource "aws_internet_gateway" "igw_cliente" {
  vpc_id = aws_vpc.vpc_cliente.id

  tags = {
    Name        = "${var.project_name}-cliente-igw"
    Environment = var.environment
    Project     = var.project_name
    Type        = "Cliente-Ejemplo"
  }
}

# Subnet pública para VPC Cliente
resource "aws_subnet" "cliente_public_subnet" {
  vpc_id                  = aws_vpc.vpc_cliente.id
  cidr_block              = var.vpc_2_public_subnet_cidr
  availability_zone       = var.availability_zone_1
  map_public_ip_on_launch = true

  tags = {
    Name        = "${var.project_name}-cliente-public"
    Environment = var.environment
    Project     = var.project_name
    Type        = "Cliente-Public"
  }
}

# Subnet privada para VPC Cliente
resource "aws_subnet" "cliente_private_subnet" {
  vpc_id            = aws_vpc.vpc_cliente.id
  cidr_block        = var.vpc_2_private_subnet_cidr
  availability_zone = var.availability_zone_2

  tags = {
    Name        = "${var.project_name}-cliente-private"
    Environment = var.environment
    Project     = var.project_name
    Type        = "Cliente-Private"
  }
}

# Route table para VPC Cliente (pública)
resource "aws_route_table" "cliente_public_rt" {
  vpc_id = aws_vpc.vpc_cliente.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.igw_cliente.id
  }

  tags = {
    Name        = "${var.project_name}-cliente-public-rt"
    Environment = var.environment
    Project     = var.project_name
    Type        = "Cliente-Public"
  }
}

# Route table para VPC Cliente (privada)
resource "aws_route_table" "cliente_private_rt" {
  vpc_id = aws_vpc.vpc_cliente.id

  tags = {
    Name        = "${var.project_name}-cliente-private-rt"
    Environment = var.environment
    Project     = var.project_name
    Type        = "Cliente-Private"
  }
}

# Asociación de subnet pública con route table pública
resource "aws_route_table_association" "cliente_public_rta" {
  subnet_id      = aws_subnet.cliente_public_subnet.id
  route_table_id = aws_route_table.cliente_public_rt.id
}

# Asociación de subnet privada con route table privada
resource "aws_route_table_association" "cliente_private_rta" {
  subnet_id      = aws_subnet.cliente_private_subnet.id
  route_table_id = aws_route_table.cliente_private_rt.id
}

# ========================================
# SECURITY GROUPS - VPC CLIENTE
# ========================================

# Security Group para instancias del cliente
resource "aws_security_group" "cliente_instances" {
  name_prefix = "${var.project_name}-cliente"
  vpc_id      = aws_vpc.vpc_cliente.id
  description = "Security group para instancias del cliente"

  # Permitir SSH
  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "SSH"
  }

  # Permitir HTTP/HTTPS
  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "HTTP"
  }

  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "HTTPS"
  }

  # Salida para internet
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
    description = "Salida a internet"
  }

  tags = {
    Name        = "${var.project_name}-cliente-sg"
    Environment = var.environment
    Project     = var.project_name
    Type        = "Cliente-Instances"
  }
}

# ========================================
# VPC MIRRORING - ENVÍO DE TRÁFICO
# ========================================

# ENI en VPC Cliente para capturar tráfico
resource "aws_network_interface" "cliente_eni" {
  subnet_id         = aws_subnet.cliente_private_subnet.id
  private_ips       = ["10.1.2.10"]
  security_groups   = [aws_security_group.cliente_instances.id]
  source_dest_check = false

  tags = {
    Name        = "${var.project_name}-cliente-eni"
    Environment = var.environment
    Project     = var.project_name
    Type        = "Cliente-ENI"
    Purpose     = "Traffic-Capture"
  }
}

# Traffic Mirror Filter para el cliente
resource "aws_ec2_traffic_mirror_filter" "cliente_filter" {
  description = "Filtro de tráfico para cliente - Solo TCP"

  tags = {
    Name        = "${var.project_name}-cliente-filter"
    Environment = var.environment
    Project     = var.project_name
    Type        = "Cliente-Filter"
  }
}

# Regla de filtro para capturar solo TCP
resource "aws_ec2_traffic_mirror_filter_rule" "cliente_tcp_rule" {
  traffic_mirror_filter_id = aws_ec2_traffic_mirror_filter.cliente_filter.id
  destination_cidr_block   = "0.0.0.0/0"
  source_cidr_block        = "0.0.0.0/0"
  rule_number              = 1
  rule_action              = "accept"
  traffic_direction        = "ingress"
  protocol                 = 6 # TCP
}

# ========================================
# VPC MIRROR SESSION - CONEXIÓN AL ANALIZADOR
# ========================================

# VPC Mirror Session en VPC Cliente - Envía tráfico al analizador
resource "aws_ec2_traffic_mirror_session" "cliente_mirror" {
  traffic_mirror_target_id = aws_network_interface.mirror_target.id
  traffic_mirror_filter_id = aws_ec2_traffic_mirror_filter.cliente_filter.id
  network_interface_id     = aws_network_interface.cliente_eni.id
  session_number           = 1
  description              = "VPC Mirror Session del cliente hacia el analizador"

  tags = {
    Name        = "${var.project_name}-cliente-mirror-session"
    Environment = var.environment
    Project     = var.project_name
    Type        = "Cliente-Mirror"
    Purpose     = "Send-Traffic-to-Analyzer"
  }
}

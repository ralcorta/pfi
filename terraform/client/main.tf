############################################
# VPC CLIENTE
############################################
resource "aws_vpc" "vpc_cliente" {
  cidr_block           = var.vpc_2_cidr
  enable_dns_hostnames = true
  enable_dns_support   = true
  tags = {
    Name        = "${var.project_name}-cliente-vpc"
    Environment = var.environment
    Project     = var.project_name
  }
}

resource "aws_internet_gateway" "igw_cliente" {
  vpc_id = aws_vpc.vpc_cliente.id
  tags = {
    Name        = "${var.project_name}-cliente-igw"
    Environment = var.environment
    Project     = var.project_name
  }
}

resource "aws_subnet" "cliente_public_subnet" {
  vpc_id                  = aws_vpc.vpc_cliente.id
  cidr_block              = var.vpc_2_public_subnet_cidr
  availability_zone       = var.availability_zone_1
  map_public_ip_on_launch = true
  tags = {
    Name        = "${var.project_name}-cliente-public"
    Environment = var.environment
    Project     = var.project_name
  }
}

resource "aws_subnet" "cliente_private_subnet" {
  vpc_id            = aws_vpc.vpc_cliente.id
  cidr_block        = var.vpc_2_private_subnet_cidr
  availability_zone = var.availability_zone_2
  tags = {
    Name        = "${var.project_name}-cliente-private"
    Environment = var.environment
    Project     = var.project_name
  }
}

resource "aws_route_table" "cliente_public_rt" {
  vpc_id = aws_vpc.vpc_cliente.id
  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.igw_cliente.id
  }
  # Ruta hacia VPC Analizador via Transit Gateway (si está configurado)
  dynamic "route" {
    for_each = local.transit_gateway_id_to_use != "" ? [1] : []
    content {
      cidr_block         = local.vpc_1_cidr_to_use
      transit_gateway_id = local.transit_gateway_id_to_use
    }
  }
  tags = {
    Name        = "${var.project_name}-cliente-public-rt"
    Environment = var.environment
    Project     = var.project_name
  }
}

resource "aws_route_table" "cliente_private_rt" {
  vpc_id = aws_vpc.vpc_cliente.id
  tags = {
    Name        = "${var.project_name}-cliente-private-rt"
    Environment = var.environment
    Project     = var.project_name
  }
}

resource "aws_route_table_association" "cliente_public_rta" {
  subnet_id      = aws_subnet.cliente_public_subnet.id
  route_table_id = aws_route_table.cliente_public_rt.id
}

resource "aws_route_table_association" "cliente_private_rta" {
  subnet_id      = aws_subnet.cliente_private_subnet.id
  route_table_id = aws_route_table.cliente_private_rt.id
}

############################################
# SG + ENI + EC2 de ejemplo
############################################
resource "aws_security_group" "cliente_instances" {
  name_prefix = "${var.project_name}-cliente"
  vpc_id      = aws_vpc.vpc_cliente.id
  description = "SG para instancias del cliente"

  lifecycle { create_before_destroy = true }

  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "SSH"
  }

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

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name        = "${var.project_name}-cliente-sg"
    Environment = var.environment
    Project     = var.project_name
  }
}

resource "aws_network_interface" "cliente_eni" {
  subnet_id         = aws_subnet.cliente_public_subnet.id
  security_groups   = [aws_security_group.cliente_instances.id]
  source_dest_check = false
  tags = {
    Name        = "${var.project_name}-cliente-eni"
    Environment = var.environment
    Project     = var.project_name
  }
}

resource "aws_eip" "cliente_instance_eip" {
  domain = "vpc"
  tags = {
    Name        = "${var.project_name}-cliente-eip"
    Environment = var.environment
    Project     = var.project_name
  }
}

resource "aws_eip_association" "cliente_eip_assoc" {
  allocation_id        = aws_eip.cliente_instance_eip.id
  network_interface_id = aws_network_interface.cliente_eni.id
}

resource "aws_instance" "cliente_instance" {
  ami           = var.client_ami_id # ej AL2 us-east-1
  instance_type = "t3.micro"
  key_name      = var.key_name
  network_interface {
    network_interface_id = aws_network_interface.cliente_eni.id
    device_index         = 0
  }
  user_data_replace_on_change = true
  user_data                   = <<-EOF
              #!/bin/bash
              set -xe
              yum update -y || true
              yum install -y python3 python3-pip nc bind-utils || true
              EOF
  tags = {
    Name        = "${var.project_name}-cliente-instance"
    Environment = var.environment
    Project     = var.project_name
  }
}

############################################
# TRANSIT GATEWAY ATTACHMENT (conecta VPC Cliente al TGW)
############################################
resource "aws_ec2_transit_gateway_vpc_attachment" "cliente" {
  count = local.transit_gateway_id_to_use != "" ? 1 : 0

  subnet_ids         = [aws_subnet.cliente_public_subnet.id]
  transit_gateway_id = local.transit_gateway_id_to_use
  vpc_id             = aws_vpc.vpc_cliente.id
  tags = {
    Name        = "${var.project_name}-tgw-attach-cliente"
    Environment = var.environment
    Project     = var.project_name
  }
}

############################################
# TRAFFIC MIRRORING (Filter + Session -> Target del analizador)
############################################

############################################
# LOCALS - Valores obtenidos del analizador o variables
############################################
locals {
  # Obtener valores del remote state del analizador (con fallback a variables)
  # try() permite que falle gracefully si el remote state no existe
  analizer_api_base_url = try(
    "${data.terraform_remote_state.analizer.outputs.api_base_url}/v1/clients/terraform-config",
    ""
  )

  api_url_to_use = var.api_url != "" ? var.api_url : (
    local.analizer_api_base_url != "" ? local.analizer_api_base_url : ""
  )

  transit_gateway_id_to_use = var.transit_gateway_id != "" ? var.transit_gateway_id : (
    try(data.terraform_remote_state.analizer.outputs.transit_gateway_id, "")
  )

  vpc_1_cidr_to_use = var.vpc_1_cidr != "" ? var.vpc_1_cidr : (
    try(data.terraform_remote_state.analizer.outputs.vpc_analizador_cidr, "10.10.0.0/16")
  )
}

# Obtener configuración automática desde la API
data "http" "client_config" {
  url = "${local.api_url_to_use}?email=${urlencode(var.client_email)}"

  request_headers = {
    Accept = "application/json"
  }
}

# Parsear la respuesta JSON
locals {
  client_config = jsondecode(data.http.client_config.response_body)

  # Validar que la respuesta contiene los campos requeridos
  traffic_mirror_target_id = try(local.client_config.traffic_mirror_target_id, null)
  vni_cliente              = try(local.client_config.vni_cliente, null)
}

# Validación: verificar que la API retorno los datos necesarios
resource "null_resource" "validate_config" {
  lifecycle {
    # Validar que los campos requeridos están presentes
    precondition {
      condition     = local.traffic_mirror_target_id != null && local.vni_cliente != null
      error_message = "La API no retorno traffic_mirror_target_id y vni_cliente. Respuesta: ${data.http.client_config.response_body}"
    }

    postcondition {
      condition     = startswith(local.traffic_mirror_target_id, "tmt-")
      error_message = "El traffic_mirror_target_id debe comenzar con 'tmt-'"
    }

    postcondition {
      condition     = local.vni_cliente >= 1 && local.vni_cliente <= 16777215
      error_message = "El vni_cliente debe ser un numero entre 1 y 16777215"
    }
  }
}

resource "aws_ec2_traffic_mirror_filter" "cliente_filter" {
  description = "Filter TCP+UDP ingress/egress"
  tags = {
    Name        = "${var.project_name}-cliente-filter"
    Environment = var.environment
    Project     = var.project_name
  }
}

resource "aws_ec2_traffic_mirror_filter_rule" "cliente_tcp_ingress" {
  traffic_mirror_filter_id = aws_ec2_traffic_mirror_filter.cliente_filter.id
  destination_cidr_block   = "0.0.0.0/0"
  source_cidr_block        = "0.0.0.0/0"
  rule_number              = 1
  rule_action              = "accept"
  traffic_direction        = "ingress"
  protocol                 = 6
}

resource "aws_ec2_traffic_mirror_filter_rule" "cliente_tcp_egress" {
  traffic_mirror_filter_id = aws_ec2_traffic_mirror_filter.cliente_filter.id
  destination_cidr_block   = "0.0.0.0/0"
  source_cidr_block        = "0.0.0.0/0"
  rule_number              = 2
  rule_action              = "accept"
  traffic_direction        = "egress"
  protocol                 = 6
}

resource "aws_ec2_traffic_mirror_filter_rule" "cliente_udp_ingress" {
  traffic_mirror_filter_id = aws_ec2_traffic_mirror_filter.cliente_filter.id
  destination_cidr_block   = "0.0.0.0/0"
  source_cidr_block        = "0.0.0.0/0"
  rule_number              = 3
  rule_action              = "accept"
  traffic_direction        = "ingress"
  protocol                 = 17
}

resource "aws_ec2_traffic_mirror_filter_rule" "cliente_udp_egress" {
  traffic_mirror_filter_id = aws_ec2_traffic_mirror_filter.cliente_filter.id
  destination_cidr_block   = "0.0.0.0/0"
  source_cidr_block        = "0.0.0.0/0"
  rule_number              = 4
  rule_action              = "accept"
  traffic_direction        = "egress"
  protocol                 = 17
}

resource "aws_ec2_traffic_mirror_session" "cliente_mirror" {
  depends_on = [
    aws_instance.cliente_instance,
    null_resource.validate_config
  ]

  traffic_mirror_target_id = local.traffic_mirror_target_id
  traffic_mirror_filter_id = aws_ec2_traffic_mirror_filter.cliente_filter.id
  network_interface_id     = aws_instance.cliente_instance.primary_network_interface_id
  session_number           = 1
  virtual_network_id       = local.vni_cliente
  description              = "Cliente -> Analizador via NLB UDP/4789 (Email: ${var.client_email})"
  tags = {
    Name        = "${var.project_name}-cliente-mirror-session"
    Environment = var.environment
    Project     = var.project_name
    ClientEmail = var.client_email
  }
}

############################################
# Outputs útiles
############################################
output "mirror_session_id" {
  description = "ID de la sesión de Traffic Mirroring"
  value       = aws_ec2_traffic_mirror_session.cliente_mirror.id
}

output "vni_usado" {
  description = "VNI asignado automáticamente desde la API"
  value       = local.vni_cliente
}

output "client_email" {
  description = "Email del cliente usado para obtener la configuración"
  value       = var.client_email
}

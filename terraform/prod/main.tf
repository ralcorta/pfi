############################################
# PROVIDER & BASE
############################################
terraform {
  required_version = ">= 1.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
  default_tags { tags = var.tags }
}

############################################
# VPC ANALIZADOR
############################################
resource "aws_vpc" "vpc_analizador" {
  cidr_block           = var.vpc_1_cidr
  enable_dns_hostnames = true
  enable_dns_support   = true
  tags = {
    Name        = "${var.project_name}-analizador-vpc"
    Environment = var.environment
    Project     = var.project_name
    Type        = "Analizador"
    Purpose     = "Ransomware-Detection"
  }
}

resource "aws_internet_gateway" "igw_analizador" {
  vpc_id = aws_vpc.vpc_analizador.id
  tags   = { Name = "${var.project_name}-analizador-igw" }
}

resource "aws_subnet" "analizador_public_subnet" {
  vpc_id                  = aws_vpc.vpc_analizador.id
  cidr_block              = var.vpc_1_public_subnet_cidr
  availability_zone       = var.availability_zone_1
  map_public_ip_on_launch = true
  tags                    = { Name = "${var.project_name}-analizador-public" }
}

resource "aws_subnet" "analizador_private_subnet" {
  vpc_id            = aws_vpc.vpc_analizador.id
  cidr_block        = var.vpc_1_private_subnet_cidr
  availability_zone = var.availability_zone_2
  tags              = { Name = "${var.project_name}-analizador-private" }
}

resource "aws_route_table" "analizador_public_rt" {
  vpc_id = aws_vpc.vpc_analizador.id
  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.igw_analizador.id
  }
  tags = { Name = "${var.project_name}-analizador-public-rt" }
}

resource "aws_route_table" "analizador_private_rt" {
  vpc_id = aws_vpc.vpc_analizador.id
  tags   = { Name = "${var.project_name}-analizador-private-rt" }
}

resource "aws_route_table_association" "analizador_public_rta" {
  subnet_id      = aws_subnet.analizador_public_subnet.id
  route_table_id = aws_route_table.analizador_public_rt.id
}

resource "aws_route_table_association" "analizador_private_rta" {
  subnet_id      = aws_subnet.analizador_private_subnet.id
  route_table_id = aws_route_table.analizador_private_rt.id
}

############################################
# SECURITY GROUP (ECS Sensor)
############################################
resource "aws_security_group" "ecs_mirror" {
  name_prefix = "${var.project_name}-ecs-mirror"
  vpc_id      = aws_vpc.vpc_analizador.id
  description = "SG para ECS sensor (mirroring via NLB)"

  lifecycle {
    create_before_destroy = true
  }

  # Health (debug)
  ingress {
    from_port   = 8080
    to_port     = 8080
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "Health 8080"
  }

  # VXLAN/UDP 4789
  ingress {
    from_port   = 4789
    to_port     = 4789
    protocol    = "udp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "VXLAN UDP/4789"
  }

  # Egress general
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = { Name = "${var.project_name}-ecs-mirror-sg" }
}

############################################
# ECR (repo imagen sensor)
############################################
resource "aws_ecr_repository" "sensor_repo" {
  name                 = "mirror-sensor"
  image_tag_mutability = "MUTABLE"
  image_scanning_configuration {
    scan_on_push = true
  }
  tags = { Name = "${var.project_name}-sensor-repo" }
}

resource "aws_ecr_lifecycle_policy" "sensor_repo_policy" {
  repository = aws_ecr_repository.sensor_repo.name
  policy = jsonencode({
    rules = [{
      rulePriority = 1
      description  = "Keep last 10 images"
      selection    = { tagStatus = "tagged", tagPrefixList = ["v"], countType = "imageCountMoreThan", countNumber = 10 }
      action       = { type = "expire" }
    }]
  })
}

############################################
# ECS Cluster
############################################
resource "aws_ecs_cluster" "sensor_cluster" {
  name = "${var.project_name}-sensor-cluster"
  setting {
    name  = "containerInsights"
    value = "enabled"
  }
  tags = { Name = "${var.project_name}-sensor-cluster" }
}

############################################
# NLB (UDP/4789) + TG (ip) + Listener
# IMPORTANT: Misma(s) subnets que usará el ECS Service
############################################
resource "aws_lb" "mirror_nlb" {
  name               = "${var.project_name}-mirror-nlb"
  internal           = true
  load_balancer_type = "network"
  subnets = [
    aws_subnet.analizador_public_subnet.id,
    aws_subnet.analizador_private_subnet.id
  ]
  tags = { Name = "${var.project_name}-mirror-nlb" }
}

resource "aws_lb_target_group" "vxlan_tg" {
  name        = "${var.project_name}-vxlan-tg"
  port        = 4789
  protocol    = "UDP"
  target_type = "ip"
  vpc_id      = aws_vpc.vpc_analizador.id

  # Health via TCP:8080 (UDP no soporta HC nativo)
  health_check {
    enabled             = true
    protocol            = "TCP"
    port                = "8080"
    interval            = 30
    timeout             = 5
    healthy_threshold   = 2
    unhealthy_threshold = 2
  }
  tags = { Name = "${var.project_name}-vxlan-tg" }
}

resource "aws_lb_listener" "vxlan_listener" {
  load_balancer_arn = aws_lb.mirror_nlb.arn
  port              = 4789
  protocol          = "UDP"
  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.vxlan_tg.arn
  }
}

############################################
# Task Definition (LabRole) + Container puertos 8080/TCP, 4789/UDP
############################################
resource "aws_ecs_task_definition" "sensor_task" {
  family                   = "${var.project_name}-sensor"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = "256"
  memory                   = "512"
  execution_role_arn       = "arn:aws:iam::${var.account_id}:role/LabRole"
  task_role_arn            = "arn:aws:iam::${var.account_id}:role/LabRole"

  container_definitions = jsonencode([
    {
      name      = "sensor",
      image     = "${aws_ecr_repository.sensor_repo.repository_url}:latest",
      cpu       = 256,
      memory    = 512,
      essential = true,
      environment = [
        { name = "AWS_REGION", value = var.aws_region },
        { name = "AWS_DYNAMO_DB_TABLE_NAME", value = "detections" },
        { name = "VXLAN_PORT", value = "4789" },
        { name = "HTTP_PORT", value = "8080" },
        { name = "WORKERS", value = "4" },
        { name = "QUEUE_MAX", value = "20000" },
        { name = "WINDOW_SECONDS", value = "3.0" },
        { name = "MAX_PKTS_PER_WINDOW", value = "256" },
        { name = "LOG_LEVEL", value = "info" }
      ],
      logConfiguration = {
        logDriver = "awslogs",
        options = {
          "awslogs-group"         = aws_cloudwatch_log_group.sensor_logs.name,
          "awslogs-region"        = var.aws_region,
          "awslogs-stream-prefix" = "ecs",
          "awslogs-create-group"  = "true"
        }
      },
      portMappings = [
        { containerPort = 8080, protocol = "tcp" },
        { containerPort = 4789, protocol = "udp" }
      ]
    }
  ])

  tags = { Name = "${var.project_name}-sensor-task" }
}

############################################
# NLB para FastAPI (TCP/80 -> 8080)
############################################
resource "aws_lb" "app_nlb" {
  name               = "${var.project_name}-app-nlb"
  load_balancer_type = "network"
  subnets            = [aws_subnet.analizador_public_subnet.id]
  tags               = { Name = "${var.project_name}-app-nlb" }
}

resource "aws_lb_target_group" "http_tg2" {
  name        = "${var.project_name}-http-tg2"
  port        = 8080
  protocol    = "TCP"
  target_type = "ip"
  vpc_id      = aws_vpc.vpc_analizador.id
  health_check {
    enabled             = true
    protocol            = "TCP"
    interval            = 30
    timeout             = 10
    healthy_threshold   = 2
    unhealthy_threshold = 3
  }
  tags = { Name = "${var.project_name}-http-tg" }
}

resource "aws_lb_listener" "http_listener" {
  load_balancer_arn = aws_lb.app_nlb.arn
  port              = 80
  protocol          = "TCP"
  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.http_tg2.arn
  }
}

############################################
# ECS Service (UDP OK con platform_version 1.4.0)
# Subnets del Service = mismas del NLB UDP
############################################
resource "aws_ecs_service" "sensor_service" {
  name             = "${var.project_name}-sensor-service"
  cluster          = aws_ecs_cluster.sensor_cluster.id
  task_definition  = aws_ecs_task_definition.sensor_task.arn
  desired_count    = 1
  launch_type      = "FARGATE"
  platform_version = "1.4.0"

  network_configuration {
    subnets = [
      aws_subnet.analizador_public_subnet.id,
      aws_subnet.analizador_private_subnet.id
    ]
    security_groups  = [aws_security_group.ecs_mirror.id]
    assign_public_ip = true
  }

  # NLB UDP/4789 -> container:4789
  load_balancer {
    target_group_arn = aws_lb_target_group.vxlan_tg.arn
    container_name   = "sensor"
    container_port   = 4789
  }

  # NLB TCP/80 -> container:8080
  load_balancer {
    target_group_arn = aws_lb_target_group.http_tg2.arn
    container_name   = "sensor"
    container_port   = 8080
  }

  health_check_grace_period_seconds = 180
  depends_on = [
    aws_ecs_task_definition.sensor_task,
    aws_lb_listener.vxlan_listener,
    aws_lb_listener.http_listener
  ]
  tags = { Name = "${var.project_name}-sensor-service" }
}

############################################
# CloudWatch Logs
############################################
resource "aws_cloudwatch_log_group" "sensor_logs" {
  name              = "/ecs/${var.project_name}-sensor"
  retention_in_days = 7
  tags              = { Name = "${var.project_name}-sensor-logs" }
}

############################################
# VPC CLIENTE
############################################
resource "aws_vpc" "vpc_cliente" {
  cidr_block           = var.vpc_2_cidr
  enable_dns_hostnames = true
  enable_dns_support   = true
  tags                 = { Name = "${var.project_name}-cliente-vpc" }
}

resource "aws_internet_gateway" "igw_cliente" {
  vpc_id = aws_vpc.vpc_cliente.id
  tags   = { Name = "${var.project_name}-cliente-igw" }
}

resource "aws_subnet" "cliente_public_subnet" {
  vpc_id                  = aws_vpc.vpc_cliente.id
  cidr_block              = var.vpc_2_public_subnet_cidr
  availability_zone       = var.availability_zone_1
  map_public_ip_on_launch = true
  tags                    = { Name = "${var.project_name}-cliente-public" }
}

resource "aws_subnet" "cliente_private_subnet" {
  vpc_id            = aws_vpc.vpc_cliente.id
  cidr_block        = var.vpc_2_private_subnet_cidr
  availability_zone = var.availability_zone_2
  tags              = { Name = "${var.project_name}-cliente-private" }
}

resource "aws_route_table" "cliente_public_rt" {
  vpc_id = aws_vpc.vpc_cliente.id
  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.igw_cliente.id
  }
  tags = { Name = "${var.project_name}-cliente-public-rt" }
}

resource "aws_route_table" "cliente_private_rt" {
  vpc_id = aws_vpc.vpc_cliente.id
  tags   = { Name = "${var.project_name}-cliente-private-rt" }
}

resource "aws_route_table_association" "cliente_public_rta" {
  subnet_id      = aws_subnet.cliente_public_subnet.id
  route_table_id = aws_route_table.cliente_public_rt.id
}

resource "aws_route_table_association" "cliente_private_rta" {
  subnet_id      = aws_subnet.cliente_private_subnet.id
  route_table_id = aws_route_table.cliente_private_rt.id
}

# SG cliente
resource "aws_security_group" "cliente_instances" {
  name_prefix = "${var.project_name}-cliente"
  vpc_id      = aws_vpc.vpc_cliente.id
  description = "SG para instancias del cliente"

  lifecycle {
    create_before_destroy = true
  }
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
  tags = { Name = "${var.project_name}-cliente-sg" }
}

# ENI cliente (mirror source)
resource "aws_network_interface" "cliente_eni" {
  subnet_id         = aws_subnet.cliente_public_subnet.id
  security_groups   = [aws_security_group.cliente_instances.id]
  source_dest_check = false
  tags              = { Name = "${var.project_name}-cliente-eni" }
}

resource "aws_eip" "cliente_instance_eip" {
  domain = "vpc"
  tags   = { Name = "${var.project_name}-cliente-eip" }
}

resource "aws_eip_association" "cliente_eip_assoc" {
  allocation_id        = aws_eip.cliente_instance_eip.id
  network_interface_id = aws_network_interface.cliente_eni.id
}

resource "aws_instance" "cliente_instance" {
  ami           = "ami-0c02fb55956c7d316" # AL2 us-east-1
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
  tags                        = { Name = "${var.project_name}-cliente-instance" }
}

############################################
# TRANSIT GATEWAY (conecta VPCs)
############################################
resource "aws_ec2_transit_gateway" "main" {
  description                     = "TGW VPC Cliente <-> VPC Analizador"
  default_route_table_association = "enable"
  default_route_table_propagation = "enable"
  dns_support                     = "enable"
  vpn_ecmp_support                = "enable"
  tags                            = { Name = "${var.project_name}-tgw" }
}

resource "aws_ec2_transit_gateway_vpc_attachment" "cliente" {
  subnet_ids         = [aws_subnet.cliente_public_subnet.id]
  transit_gateway_id = aws_ec2_transit_gateway.main.id
  vpc_id             = aws_vpc.vpc_cliente.id
  tags               = { Name = "${var.project_name}-tgw-attach-cliente" }
}

resource "aws_ec2_transit_gateway_vpc_attachment" "analizador" {
  subnet_ids         = [aws_subnet.analizador_public_subnet.id, aws_subnet.analizador_private_subnet.id]
  transit_gateway_id = aws_ec2_transit_gateway.main.id
  vpc_id             = aws_vpc.vpc_analizador.id
  tags               = { Name = "${var.project_name}-tgw-attach-analizador" }
}

resource "aws_ec2_transit_gateway_route_table" "main" {
  transit_gateway_id = aws_ec2_transit_gateway.main.id
  tags               = { Name = "${var.project_name}-tgw-rt" }
}

# *** FIX: Associations explícitas a la TGW RT ***
resource "aws_ec2_transit_gateway_route_table_association" "assoc_cliente" {
  transit_gateway_attachment_id  = aws_ec2_transit_gateway_vpc_attachment.cliente.id
  transit_gateway_route_table_id = aws_ec2_transit_gateway_route_table.main.id
  replace_existing_association   = true
}

resource "aws_ec2_transit_gateway_route_table_association" "assoc_analizador" {
  transit_gateway_attachment_id  = aws_ec2_transit_gateway_vpc_attachment.analizador.id
  transit_gateway_route_table_id = aws_ec2_transit_gateway_route_table.main.id
  replace_existing_association   = true
}

# Propagation
resource "aws_ec2_transit_gateway_route_table_propagation" "prop_cliente" {
  transit_gateway_attachment_id  = aws_ec2_transit_gateway_vpc_attachment.cliente.id
  transit_gateway_route_table_id = aws_ec2_transit_gateway_route_table.main.id
}

resource "aws_ec2_transit_gateway_route_table_propagation" "prop_analizador" {
  transit_gateway_attachment_id  = aws_ec2_transit_gateway_vpc_attachment.analizador.id
  transit_gateway_route_table_id = aws_ec2_transit_gateway_route_table.main.id
}

# Rutas VPC <-> VPC via TGW (CIDR completo)
resource "aws_route" "cliente_to_analizador_tgw" {
  route_table_id         = aws_route_table.cliente_public_rt.id
  destination_cidr_block = aws_vpc.vpc_analizador.cidr_block
  transit_gateway_id     = aws_ec2_transit_gateway.main.id
}

resource "aws_route" "analizador_to_cliente_tgw_public" {
  route_table_id         = aws_route_table.analizador_public_rt.id
  destination_cidr_block = aws_vpc.vpc_cliente.cidr_block
  transit_gateway_id     = aws_ec2_transit_gateway.main.id
}

resource "aws_route" "analizador_to_cliente_tgw_private" {
  route_table_id         = aws_route_table.analizador_private_rt.id
  destination_cidr_block = aws_vpc.vpc_cliente.cidr_block
  transit_gateway_id     = aws_ec2_transit_gateway.main.id
}

############################################
# TRAFFIC MIRRORING (Target = NLB del analizador)
############################################
resource "aws_ec2_traffic_mirror_target" "analizador_target" {
  network_load_balancer_arn = aws_lb.mirror_nlb.arn
  tags                      = { Name = "${var.project_name}-analizador-target-nlb" }
}

resource "aws_ec2_traffic_mirror_filter" "cliente_filter" {
  description = "Filter TCP+UDP ingress/egress"
  tags        = { Name = "${var.project_name}-cliente-filter" }
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
  depends_on               = [aws_instance.cliente_instance]
  traffic_mirror_target_id = aws_ec2_traffic_mirror_target.analizador_target.id
  traffic_mirror_filter_id = aws_ec2_traffic_mirror_filter.cliente_filter.id
  network_interface_id     = aws_instance.cliente_instance.primary_network_interface_id
  session_number           = 1
  description              = "Cliente -> Analizador via NLB UDP/4789"
  tags                     = { Name = "${var.project_name}-cliente-mirror-session" }
}

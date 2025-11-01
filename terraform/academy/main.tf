# ========================================
# CONFIGURACIÓN TERRAFORM PARA AWS ACADEMY
# ========================================
# Esta configuración usa data sources para referenciar recursos existentes
# en lugar de crearlos, debido a las restricciones de permisos de Voclabs

# Configuración del provider AWS
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
  default_tags {
    tags = var.tags
  }
}

############################################
# DATA SOURCES - Recursos existentes
############################################

# VPCs existentes
data "aws_vpc" "vpc_analizador" {
  id = var.existing_vpc_analizador_id
}

data "aws_vpc" "vpc_cliente" {
  id = var.existing_vpc_cliente_id
}

# Subnets existentes
data "aws_subnet" "analizador_public_subnet" {
  id = var.existing_subnet_analizador_public_id
}

data "aws_subnet" "analizador_private_subnet" {
  id = var.existing_subnet_analizador_private_id
}

data "aws_subnet" "cliente_public_subnet" {
  id = var.existing_subnet_cliente_public_id
}

data "aws_subnet" "cliente_private_subnet" {
  id = var.existing_subnet_cliente_private_id
}

# ECR Repository existente
data "aws_ecr_repository" "sensor_repo" {
  name = var.existing_ecr_repository_name
}

# ECS Cluster existente
data "aws_ecs_cluster" "sensor_cluster" {
  cluster_name = var.existing_ecs_cluster_name
}

# CloudWatch Log Group existente
data "aws_cloudwatch_log_group" "sensor_logs" {
  name = var.existing_cloudwatch_log_group_name
}

# Internet Gateways existentes (se asume que ya existen)
data "aws_internet_gateway" "igw_analizador" {
  filter {
    name   = "attachment.vpc-id"
    values = [data.aws_vpc.vpc_analizador.id]
  }
}

data "aws_internet_gateway" "igw_cliente" {
  filter {
    name   = "attachment.vpc-id"
    values = [data.aws_vpc.vpc_cliente.id]
  }
}

############################################
# SECURITY GROUPS
############################################

# SG del ECS (sensor)
resource "aws_security_group" "ecs_mirror" {
  name_prefix = "${var.project_name}-ecs-mirror"
  vpc_id      = data.aws_vpc.vpc_analizador.id
  description = "SG para ECS sensor (mirroring via NLB)"

  # Health checks desde la VPC analizador
  ingress {
    from_port   = 8080
    to_port     = 8080
    protocol    = "tcp"
    cidr_blocks = [data.aws_vpc.vpc_analizador.cidr_block]
    description = "Health check endpoint"
  }

  # VXLAN/UDP 4789 (desde NLB)
  ingress {
    from_port = 4789
    to_port   = 4789
    protocol  = "udp"
    cidr_blocks = [
      data.aws_vpc.vpc_analizador.cidr_block,
      data.aws_vpc.vpc_cliente.cidr_block
    ]
    description = "VXLAN/UDP 4789 hacia el task via NLB"
  }

  # Salida
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
    description = "Salida para logs/monitoreo"
  }

  tags = {
    Name        = "${var.project_name}-ecs-mirror-sg"
    Environment = var.environment
    Project     = var.project_name
    Purpose     = "ECS-Mirroring"
  }
}

# SG para instancias del cliente
resource "aws_security_group" "cliente_instances" {
  name_prefix = "${var.project_name}-cliente"
  vpc_id      = data.aws_vpc.vpc_cliente.id
  description = "SG para instancias del cliente"

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
    description = "Salida a internet"
  }

  tags = {
    Name        = "${var.project_name}-cliente-sg"
    Environment = var.environment
    Project     = var.project_name
    Type        = "Cliente-Instances"
  }
}

############################################
# NLB interno (UDP/4789) + TG + Listener
############################################
resource "aws_lb" "mirror_nlb" {
  name               = "${var.project_name}-mirror-nlb"
  internal           = true
  load_balancer_type = "network"
  subnets            = [data.aws_subnet.analizador_private_subnet.id]

  tags = {
    Name        = "${var.project_name}-mirror-nlb"
    Environment = var.environment
    Project     = var.project_name
    Purpose     = "Traffic-Mirroring-UDP4789"
  }
}

resource "aws_lb_target_group" "vxlan_tg" {
  name        = "${var.project_name}-vxlan-tg"
  port        = 4789
  protocol    = "UDP"
  target_type = "ip"
  vpc_id      = data.aws_vpc.vpc_analizador.id

  # Para UDP con target_type=ip, AWS requiere health_check habilitado
  health_check {
    enabled             = true
    healthy_threshold   = 2
    unhealthy_threshold = 2
    timeout             = 5
    interval            = 30
    protocol            = "TCP"
    port                = "8080"
    path                = "/health"
    matcher             = "200"
  }

  tags = {
    Name        = "${var.project_name}-vxlan-tg"
    Environment = var.environment
    Project     = var.project_name
    Purpose     = "VXLAN-TargetGroup"
  }
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
# Task Definition
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
      name      = "sensor"
      image     = "${data.aws_ecr_repository.sensor_repo.repository_url}:latest"
      cpu       = 256
      memory    = 512
      essential = true
      environment = [
        { name = "INTERFACE", value = "eth0" },
        { name = "FILTER", value = "tcp or udp" },
        { name = "MODEL_PATH", value = "/app/models/convlstm_model.keras" },
        { name = "VXLAN_PORT", value = "4789" }
      ]
      healthCheck = {
        command     = ["CMD-SHELL", "curl -sf http://localhost:8080/health || exit 1"]
        interval    = 30
        timeout     = 5
        retries     = 3
        startPeriod = 60
      }
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = data.aws_cloudwatch_log_group.sensor_logs.name
          "awslogs-region"        = var.aws_region
          "awslogs-stream-prefix" = "ecs"
          "awslogs-create-group"  = "false"
        }
      }
      portMappings = [
        { containerPort = 8080, protocol = "tcp" },
        { containerPort = 4789, protocol = "udp" }
      ]
    }
  ])

  tags = {
    Name        = "${var.project_name}-sensor-task"
    Environment = var.environment
    Project     = var.project_name
    Type        = "ECS-Task"
  }
}

############################################
# ECS Service
############################################
resource "aws_ecs_service" "sensor_service" {
  name            = "${var.project_name}-sensor-service"
  cluster         = data.aws_ecs_cluster.sensor_cluster.id
  task_definition = aws_ecs_task_definition.sensor_task.arn
  desired_count   = 1
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = [data.aws_subnet.analizador_private_subnet.id]
    security_groups  = [aws_security_group.ecs_mirror.id]
    assign_public_ip = false
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.vxlan_tg.arn
    container_name   = "sensor"
    container_port   = 4789
  }

  health_check_grace_period_seconds = 60

  depends_on = [
    aws_ecs_task_definition.sensor_task,
    aws_lb_listener.vxlan_listener
  ]

  tags = {
    Name        = "${var.project_name}-sensor-service"
    Environment = var.environment
    Project     = var.project_name
    Type        = "ECS-Service"
  }
}

############################################
# EC2 Instance para captura de tráfico
############################################
# Data source para AMI
data "aws_ami" "amazon_linux" {
  most_recent = true
  owners      = ["amazon"]

  filter {
    name   = "name"
    values = ["amzn2-ami-hvm-*-x86_64-gp2"]
  }
}

# EC2 Instance para captura de tráfico
resource "aws_instance" "cliente_instance" {
  ami                    = data.aws_ami.amazon_linux.id
  instance_type          = "t3.micro"
  subnet_id              = data.aws_subnet.cliente_private_subnet.id
  vpc_security_group_ids = [aws_security_group.cliente_instances.id]

  # Configuración de red para traffic mirroring
  source_dest_check = false

  user_data = base64encode(<<-EOF
    #!/bin/bash
    yum update -y
    yum install -y tcpdump
    # Configurar para permitir traffic mirroring
    echo 'net.ipv4.conf.all.accept_redirects = 0' >> /etc/sysctl.conf
    echo 'net.ipv4.conf.all.send_redirects = 0' >> /etc/sysctl.conf
    sysctl -p
  EOF
  )

  tags = {
    Name        = "${var.project_name}-cliente-instance"
    Environment = var.environment
    Project     = var.project_name
    Type        = "Cliente-Instance"
    Purpose     = "Traffic-Capture"
  }
}

############################################
# Traffic Mirroring (Target = NLB)
############################################
resource "aws_ec2_traffic_mirror_target" "analizador_target" {
  network_load_balancer_arn = aws_lb.mirror_nlb.arn
  tags = {
    Name        = "${var.project_name}-analizador-target"
    Environment = var.environment
    Project     = var.project_name
    Purpose     = "Traffic-Mirror-Target"
    Type        = "Analizador-Target-NLB"
  }
}

# NOTA: Traffic Mirror Filter debe crearse manualmente debido a restricciones
# Usar data source para referenciar el filtro existente
data "aws_ec2_traffic_mirror_filter" "cliente_filter" {
  filter {
    name   = "tag:Name"
    values = ["${var.project_name}-cliente-filter"]
  }
}

resource "aws_ec2_traffic_mirror_session" "cliente_mirror" {
  traffic_mirror_target_id = aws_ec2_traffic_mirror_target.analizador_target.id
  traffic_mirror_filter_id = data.aws_ec2_traffic_mirror_filter.cliente_filter.id
  network_interface_id     = aws_instance.cliente_instance.primary_network_interface_id
  session_number           = 1
  description              = "Cliente -> Analizador via NLB UDP/4789"

  tags = {
    Name        = "${var.project_name}-cliente-mirror-session"
    Environment = var.environment
    Project     = var.project_name
    Purpose     = "Send-Traffic-to-Analyzer"
  }
}

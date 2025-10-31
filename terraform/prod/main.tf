# ========================================
# CONFIGURACIÓN TERRAFORM
# ========================================

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

  tags = {
    Name        = "${var.project_name}-analizador-igw"
    Environment = var.environment
    Project     = var.project_name
    Type        = "Analizador"
  }
}

resource "aws_subnet" "analizador_public_subnet" {
  vpc_id                  = aws_vpc.vpc_analizador.id
  cidr_block              = var.vpc_1_public_subnet_cidr
  availability_zone       = var.availability_zone_1
  map_public_ip_on_launch = true

  tags = {
    Name        = "${var.project_name}-analizador-public"
    Environment = var.environment
    Project     = var.project_name
    Type        = "Analizador-Public"
  }
}

resource "aws_subnet" "analizador_private_subnet" {
  vpc_id            = aws_vpc.vpc_analizador.id
  cidr_block        = var.vpc_1_private_subnet_cidr
  availability_zone = var.availability_zone_2

  tags = {
    Name        = "${var.project_name}-analizador-private"
    Environment = var.environment
    Project     = var.project_name
    Type        = "Analizador-Private"
  }
}

resource "aws_route_table" "analizador_public_rt" {
  vpc_id = aws_vpc.vpc_analizador.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.igw_analizador.id
  }

  tags = {
    Name        = "${var.project_name}-analizador-public-rt"
    Environment = var.environment
    Project     = var.project_name
    Type        = "Analizador-Public"
  }
}

resource "aws_route_table" "analizador_private_rt" {
  vpc_id = aws_vpc.vpc_analizador.id

  tags = {
    Name        = "${var.project_name}-analizador-private-rt"
    Environment = var.environment
    Project     = var.project_name
    Type        = "Analizador-Private"
  }
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
# SECURITY GROUPS (Analizador)
############################################
# SG del ECS (sensor). Abrimos 8080/tcp (health) y 4789/udp (VXLAN).
resource "aws_security_group" "ecs_mirror" {
  name_prefix = "${var.project_name}-ecs-mirror"
  vpc_id      = aws_vpc.vpc_analizador.id
  description = "SG para ECS sensor (mirroring via NLB)"

  # Health check - MUY PERMISIVO para debugging
  ingress {
    from_port   = 8080
    to_port     = 8080
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "Health check endpoint (DEBUGGING - muy permisivo)"
  }

  # VXLAN/UDP 4789 - MUY PERMISIVO para debugging
  ingress {
    from_port   = 4789
    to_port     = 4789
    protocol    = "udp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "VXLAN/UDP 4789 desde cualquier origen (DEBUGGING - muy permisivo)"
  }

  # Permitir todo UDP para debugging (por si AWS usa otro puerto)
  ingress {
    from_port   = 0
    to_port     = 65535
    protocol    = "udp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "Todo UDP desde cualquier origen (DEBUGGING - muy permisivo)"
  }

  # Permitir trafico desde VPC Cliente (para peering y Traffic Mirroring)
  ingress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = [aws_vpc.vpc_cliente.cidr_block]
    description = "Todo trafico desde VPC Cliente (para Traffic Mirroring via peering)"
  }

  # HTTPS interno para llegar a los Interface Endpoints (ECR/Logs)
  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    self        = true
    description = "HTTPS hacia VPCE desde tasks (self SG)"
  }

  # HTTPS para ECR y CloudWatch
  egress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "HTTPS para ECR y CloudWatch"
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

############################################
# ECR
############################################
resource "aws_ecr_repository" "sensor_repo" {
  name                 = "mirror-sensor"
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration { scan_on_push = true }

  tags = {
    Name        = "${var.project_name}-sensor-repo"
    Environment = var.environment
    Project     = var.project_name
    Type        = "Docker-Repository"
  }
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

  tags = {
    Name        = "${var.project_name}-sensor-cluster"
    Environment = var.environment
    Project     = var.project_name
    Type        = "ECS-Cluster"
  }
}

############################################
# NLB interno (UDP/4789) + TG (target_type=ip) + Listener
############################################
resource "aws_lb" "mirror_nlb" {
  name               = "${var.project_name}-mirror-nlb"
  internal           = true
  load_balancer_type = "network"
  # Incluir subnets en las AZ donde corren los tasks; evita "AZ not enabled" en TG
  subnets = [
    aws_subnet.analizador_public_subnet.id, # AZ1
    aws_subnet.analizador_private_subnet.id # AZ2
  ]

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
  vpc_id      = aws_vpc.vpc_analizador.id

  # Para UDP con target type 'ip', AWS requiere health check habilitado
  # Usamos TCP para health check ya que UDP no está soportado
  health_check {
    enabled             = true
    healthy_threshold   = 2
    unhealthy_threshold = 2
    timeout             = 5
    interval            = 30
    port                = "8080"
    protocol            = "TCP"
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
# Task Definition (usa solo LabRole)
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
      image     = "${aws_ecr_repository.sensor_repo.repository_url}:latest"
      cpu       = 256
      memory    = 512
      essential = true
      environment = [
        { name = "INTERFACE", value = "eth0" },
        { name = "FILTER", value = "tcp or udp" },
        { name = "MODEL_PATH", value = "/app/models/convlstm_model.keras" },
        { name = "VXLAN_PORT", value = "4789" },
        { name = "DISABLE_DOTENV", value = "1" },
        # Forzar AWS en prod: sin endpoint local
        { name = "AWS_DYNAMO_DB_ENDPOINT", value = "" },
        { name = "AWS_REGION", value = var.aws_region },
        { name = "AWS_DYNAMO_DB_TABLE_NAME", value = "detections" }
      ]
      # healthCheck deshabilitado temporalmente a pedido
      # healthCheck = {
      #   command     = ["CMD-SHELL", "curl -sf http://localhost:8080/health || exit 1"]
      #   interval    = 30
      #   timeout     = 5
      #   retries     = 3
      #   startPeriod = 60
      # }
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = aws_cloudwatch_log_group.sensor_logs.name
          "awslogs-region"        = var.aws_region
          "awslogs-stream-prefix" = "ecs"
          "awslogs-create-group"  = "true"
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
# VPC Endpoints para ECR (acceso desde subnet privada)
############################################
resource "aws_vpc_endpoint" "ecr_dkr" {
  vpc_id              = aws_vpc.vpc_analizador.id
  service_name        = "com.amazonaws.${var.aws_region}.ecr.dkr"
  vpc_endpoint_type   = "Interface"
  subnet_ids          = [aws_subnet.analizador_private_subnet.id]
  security_group_ids  = [aws_security_group.ecs_mirror.id]
  private_dns_enabled = false

  tags = {
    Name        = "${var.project_name}-ecr-dkr-endpoint"
    Environment = var.environment
    Project     = var.project_name
    Purpose     = "ECR-Docker-API"
  }
}

############################################
# NLB para exponer FastAPI (TCP/80 -> 8080)
############################################
resource "aws_lb" "app_nlb" {
  name               = "${var.project_name}-app-nlb"
  load_balancer_type = "network"
  subnets            = [aws_subnet.analizador_public_subnet.id]

  tags = {
    Name        = "${var.project_name}-app-nlb"
    Environment = var.environment
    Project     = var.project_name
    Purpose     = "Expose-FastAPI"
  }
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

  tags = {
    Name        = "${var.project_name}-http-tg"
    Environment = var.environment
    Project     = var.project_name
    Purpose     = "FastAPI-TargetGroup"
  }
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

resource "aws_vpc_endpoint" "ecr_api" {
  vpc_id              = aws_vpc.vpc_analizador.id
  service_name        = "com.amazonaws.${var.aws_region}.ecr.api"
  vpc_endpoint_type   = "Interface"
  subnet_ids          = [aws_subnet.analizador_private_subnet.id]
  security_group_ids  = [aws_security_group.ecs_mirror.id]
  private_dns_enabled = false

  tags = {
    Name        = "${var.project_name}-ecr-api-endpoint"
    Environment = var.environment
    Project     = var.project_name
    Purpose     = "ECR-API"
  }
}

resource "aws_vpc_endpoint" "s3" {
  vpc_id            = aws_vpc.vpc_analizador.id
  service_name      = "com.amazonaws.${var.aws_region}.s3"
  vpc_endpoint_type = "Gateway"
  route_table_ids   = [aws_route_table.analizador_private_rt.id]

  tags = {
    Name        = "${var.project_name}-s3-endpoint"
    Environment = var.environment
    Project     = var.project_name
    Purpose     = "S3-Gateway"
  }
}

resource "aws_vpc_endpoint" "cloudwatch_logs" {
  vpc_id              = aws_vpc.vpc_analizador.id
  service_name        = "com.amazonaws.${var.aws_region}.logs"
  vpc_endpoint_type   = "Interface"
  subnet_ids          = [aws_subnet.analizador_private_subnet.id]
  security_group_ids  = [aws_security_group.ecs_mirror.id]
  private_dns_enabled = true

  tags = {
    Name        = "${var.project_name}-cloudwatch-logs-endpoint"
    Environment = var.environment
    Project     = var.project_name
    Purpose     = "CloudWatch-Logs"
  }
}

############################################
# ECS Service (registra IP del task en TG UDP/4789)
############################################
resource "aws_ecs_service" "sensor_service" {
  name            = "${var.project_name}-sensor-service"
  cluster         = aws_ecs_cluster.sensor_cluster.id
  task_definition = aws_ecs_task_definition.sensor_task.arn
  desired_count   = 1
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = [aws_subnet.analizador_public_subnet.id]
    security_groups  = [aws_security_group.ecs_mirror.id]
    assign_public_ip = true
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.vxlan_tg.arn
    container_name   = "sensor"
    container_port   = 4789
  }

  # Publicar FastAPI en ALB HTTP/80 -> 8080 container
  load_balancer {
    target_group_arn = aws_lb_target_group.http_tg2.arn
    container_name   = "sensor"
    container_port   = 8080
  }

  health_check_grace_period_seconds = 180

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
# CloudWatch Logs
############################################
resource "aws_cloudwatch_log_group" "sensor_logs" {
  name              = "/ecs/${var.project_name}-sensor"
  retention_in_days = 7
  tags = {
    Name        = "${var.project_name}-sensor-logs"
    Environment = var.environment
    Project     = var.project_name
  }
}

############################################
# VPC CLIENTE (fuente del mirror)
############################################
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

resource "aws_internet_gateway" "igw_cliente" {
  vpc_id = aws_vpc.vpc_cliente.id
  tags = {
    Name        = "${var.project_name}-cliente-igw"
    Environment = var.environment
    Project     = var.project_name
    Type        = "Cliente-Ejemplo"
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
    Type        = "Cliente-Public"
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
    Type        = "Cliente-Private"
  }
}

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

resource "aws_route_table" "cliente_private_rt" {
  vpc_id = aws_vpc.vpc_cliente.id
  tags = {
    Name        = "${var.project_name}-cliente-private-rt"
    Environment = var.environment
    Project     = var.project_name
    Type        = "Cliente-Private"
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

# SG para instancias del cliente
resource "aws_security_group" "cliente_instances" {
  name_prefix = "${var.project_name}-cliente"
  vpc_id      = aws_vpc.vpc_cliente.id
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

  # Permitir trafico desde VPC Analizador (para peering)
  ingress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = [aws_vpc.vpc_analizador.cidr_block]
    description = "Todo trafico desde VPC Analizador (para Traffic Mirroring)"
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

# ENI fuente (donde tcpreplay-ás)
resource "aws_network_interface" "cliente_eni" {
  subnet_id         = aws_subnet.cliente_public_subnet.id
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

# IP pública para la instancia cliente (necesaria cuando se usa ENI existente)
resource "aws_eip" "cliente_instance_eip" {
  domain = "vpc"

  tags = {
    Name        = "${var.project_name}-cliente-eip"
    Environment = var.environment
    Project     = var.project_name
    Purpose     = "Cliente-Public-IP"
  }
}

resource "aws_eip_association" "cliente_eip_assoc" {
  allocation_id        = aws_eip.cliente_instance_eip.id
  network_interface_id = aws_network_interface.cliente_eni.id
}

# EC2 instance para el cliente (requerido para traffic mirroring)
resource "aws_instance" "cliente_instance" {
  ami           = "ami-0c02fb55956c7d316" # Amazon Linux 2 AMI (us-east-1)
  instance_type = "t3.micro"
  key_name      = "vockey" # Clave SSH de AWS Academy

  network_interface {
    network_interface_id = aws_network_interface.cliente_eni.id
    device_index         = 0
  }

  # Forzar recreación cuando cambie user_data
  user_data_replace_on_change = true

  user_data = <<-EOF
              #!/bin/bash
              # Instalar solo Python y requests para scripts manuales
              set -xe
              yum update -y || true
              yum install -y python3 python3-pip nc bind-utils || true
              pip3 install --upgrade pip requests || true
              
              # Crear directorio para scripts
              mkdir -p /home/ec2-user/scripts
              chown ec2-user:ec2-user /home/ec2-user/scripts
              
              # Log de inicio
              echo "$(date): Python y requests instalados. Listo para ejecutar scripts." >> /var/log/user_data.log
              EOF

  tags = {
    Name        = "${var.project_name}-cliente-instance"
    Environment = var.environment
    Project     = var.project_name
    Type        = "Cliente-Instance"
    Purpose     = "Traffic-Mirror-Source"
  }
}

############################################
# Transit Gateway (conecta VPCs para Traffic Mirroring)
############################################
resource "aws_ec2_transit_gateway" "main" {
  description = "Transit Gateway para conectar VPC Cliente y Analizador"

  default_route_table_association = "enable"
  default_route_table_propagation = "enable"

  dns_support      = "enable"
  vpn_ecmp_support = "enable"

  tags = {
    Name        = "${var.project_name}-transit-gateway"
    Environment = var.environment
    Project     = var.project_name
    Purpose     = "Traffic-Mirroring-Connectivity"
  }
}

# Attachment VPC Cliente al Transit Gateway
resource "aws_ec2_transit_gateway_vpc_attachment" "cliente" {
  subnet_ids         = [aws_subnet.cliente_public_subnet.id]
  transit_gateway_id = aws_ec2_transit_gateway.main.id
  vpc_id             = aws_vpc.vpc_cliente.id

  tags = {
    Name        = "${var.project_name}-tgw-attachment-cliente"
    Environment = var.environment
    Project     = var.project_name
  }
}

# Attachment VPC Analizador al Transit Gateway
resource "aws_ec2_transit_gateway_vpc_attachment" "analizador" {
  subnet_ids = [
    aws_subnet.analizador_public_subnet.id,
    aws_subnet.analizador_private_subnet.id
  ]
  transit_gateway_id = aws_ec2_transit_gateway.main.id
  vpc_id             = aws_vpc.vpc_analizador.id

  tags = {
    Name        = "${var.project_name}-tgw-attachment-analizador"
    Environment = var.environment
    Project     = var.project_name
  }
}

# Route Table del Transit Gateway
resource "aws_ec2_transit_gateway_route_table" "main" {
  transit_gateway_id = aws_ec2_transit_gateway.main.id

  tags = {
    Name        = "${var.project_name}-tgw-route-table"
    Environment = var.environment
    Project     = var.project_name
  }
}

# Routes en Transit Gateway para permitir comunicación entre VPCs
resource "aws_ec2_transit_gateway_route" "cliente_to_analizador" {
  destination_cidr_block         = aws_vpc.vpc_analizador.cidr_block
  transit_gateway_attachment_id  = aws_ec2_transit_gateway_vpc_attachment.analizador.id
  transit_gateway_route_table_id = aws_ec2_transit_gateway_route_table.main.id
}

resource "aws_ec2_transit_gateway_route" "analizador_to_cliente" {
  destination_cidr_block         = aws_vpc.vpc_cliente.cidr_block
  transit_gateway_attachment_id  = aws_ec2_transit_gateway_vpc_attachment.cliente.id
  transit_gateway_route_table_id = aws_ec2_transit_gateway_route_table.main.id
}

# Propagaciones en la route table (las asociaciones son automáticas con default_route_table_association)
resource "aws_ec2_transit_gateway_route_table_propagation" "cliente" {
  transit_gateway_attachment_id  = aws_ec2_transit_gateway_vpc_attachment.cliente.id
  transit_gateway_route_table_id = aws_ec2_transit_gateway_route_table.main.id
}

resource "aws_ec2_transit_gateway_route_table_propagation" "analizador" {
  transit_gateway_attachment_id  = aws_ec2_transit_gateway_vpc_attachment.analizador.id
  transit_gateway_route_table_id = aws_ec2_transit_gateway_route_table.main.id
}

# Routes en VPC Cliente hacia VPC Analizador via Transit Gateway
resource "aws_route" "cliente_to_analizador_tgw" {
  route_table_id         = aws_route_table.cliente_public_rt.id
  destination_cidr_block = aws_vpc.vpc_analizador.cidr_block
  transit_gateway_id     = aws_ec2_transit_gateway.main.id
}

# Routes en VPC Analizador hacia VPC Cliente via Transit Gateway
resource "aws_route" "analizador_to_cliente_tgw" {
  route_table_id         = aws_route_table.analizador_public_rt.id
  destination_cidr_block = aws_vpc.vpc_cliente.cidr_block
  transit_gateway_id     = aws_ec2_transit_gateway.main.id
}

# También en la subnet privada del analizador
resource "aws_route" "analizador_private_to_cliente_tgw" {
  route_table_id         = aws_route_table.analizador_private_rt.id
  destination_cidr_block = aws_vpc.vpc_cliente.cidr_block
  transit_gateway_id     = aws_ec2_transit_gateway.main.id
}

############################################
# Traffic Mirroring (Target = Transit Gateway Attachment -> NLB)
############################################
# Usar Transit Gateway Attachment como target
# Flujo: Traffic Mirror Session -> Transit Gateway (via attachment) -> Routes -> NLB -> Sensor
# Esto permite que el tráfico mirrored cruce VPCs correctamente
# Traffic Mirror Target usando NLB
# Nota: Transit Gateway NO puede ser usado directamente como target en Terraform
# El Transit Gateway ya está configurado para routing entre VPCs
# El tráfico mirrored irá: Session -> NLB -> Sensor
# Transit Gateway permite conectividad entre VPCs para routing general
resource "aws_ec2_traffic_mirror_target" "analizador_target" {
  network_load_balancer_arn = aws_lb.mirror_nlb.arn
  tags = {
    Name        = "${var.project_name}-analizador-target"
    Environment = var.environment
    Project     = var.project_name
    Purpose     = "Traffic-Mirror-Target-NLB"
    Type        = "Analizador-Target-NLB"
    Note        = "Transit Gateway configured for VPC connectivity"
  }
}

resource "aws_ec2_traffic_mirror_filter" "cliente_filter" {
  description = "Traffic filter for client - TCP+UDP ingress/egress"
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
  depends_on = [aws_instance.cliente_instance]

  traffic_mirror_target_id = aws_ec2_traffic_mirror_target.analizador_target.id
  traffic_mirror_filter_id = aws_ec2_traffic_mirror_filter.cliente_filter.id
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

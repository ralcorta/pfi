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
  }
}

resource "aws_route_table" "analizador_public_rt" {
  vpc_id = aws_vpc.vpc_analizador.id
  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.igw_analizador.id
  }
  # Nota: No agregamos rutas específicas hacia clientes aquí.
  # El Transit Gateway con default_route_table_propagation = "enable"
  # automáticamente propagará las rutas de todos los VPCs conectados.
  tags = {
    Name        = "${var.project_name}-analizador-public-rt"
    Environment = var.environment
    Project     = var.project_name
  }
}

resource "aws_route_table" "analizador_private_rt" {
  vpc_id = aws_vpc.vpc_analizador.id

  # Nota: No agregamos rutas específicas hacia clientes aquí.
  # El Transit Gateway con default_route_table_propagation = "enable"
  # automáticamente propagará las rutas de todos los VPCs conectados.

  tags = {
    Name        = "${var.project_name}-analizador-private-rt"
    Environment = var.environment
    Project     = var.project_name
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
# SECURITY GROUP (ECS Sensor)
############################################
resource "aws_security_group" "ecs_mirror" {
  name_prefix = "${var.project_name}-ecs-mirror"
  vpc_id      = aws_vpc.vpc_analizador.id
  description = "SG para ECS sensor (mirroring via NLB)"

  lifecycle { create_before_destroy = true }

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

  tags = {
    Name        = "${var.project_name}-ecs-mirror-sg"
    Environment = var.environment
    Project     = var.project_name
  }
}

############################################
# ECR (repo imagen sensor)
############################################
resource "aws_ecr_repository" "sensor_repo" {
  name                 = "mirror-sensor"
  image_tag_mutability = "MUTABLE"
  image_scanning_configuration { scan_on_push = true }
  tags = {
    Name        = "${var.project_name}-sensor-repo"
    Environment = var.environment
    Project     = var.project_name
  }
}

resource "aws_ecr_lifecycle_policy" "sensor_repo_policy" {
  repository = aws_ecr_repository.sensor_repo.name
  policy = jsonencode({
    rules = [{
      rulePriority = 1
      description  = "Keep last 10 images"
      selection = {
        tagStatus     = "tagged"
        tagPrefixList = ["v"]
        countType     = "imageCountMoreThan"
        countNumber   = 10
      }
      action = { type = "expire" }
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
  }
}

############################################
# NLB (UDP/4789) + TG (ip) + Listener
############################################
resource "aws_lb" "mirror_nlb" {
  name               = "${var.project_name}-mirror-int"
  internal           = true # INTERNAL es requerido para Traffic Mirroring
  load_balancer_type = "network"
  subnets = [
    aws_subnet.analizador_public_subnet.id,
    aws_subnet.analizador_private_subnet.id
  ]
  tags = {
    Name        = "${var.project_name}-mirror-nlb"
    Environment = var.environment
    Project     = var.project_name
  }
}

resource "aws_lb_target_group" "vxlan_tg" {
  name        = "${var.project_name}-vxlan-tg"
  port        = 4789
  protocol    = "UDP"
  target_type = "ip"
  vpc_id      = aws_vpc.vpc_analizador.id

  # Health via TCP:8080
  health_check {
    enabled             = true
    protocol            = "TCP"
    port                = "8080"
    interval            = 30
    timeout             = 5
    healthy_threshold   = 2
    unhealthy_threshold = 2
  }
  tags = {
    Name        = "${var.project_name}-vxlan-tg"
    Environment = var.environment
    Project     = var.project_name
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
# Task Definition + Service (puertos 8080/TCP, 4789/UDP)
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

resource "aws_ecs_task_definition" "sensor_task" {
  family                   = "${var.project_name}-sensor"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = "1024"
  memory                   = "2048"
  execution_role_arn       = "arn:aws:iam::${var.account_id}:role/LabRole"
  task_role_arn            = "arn:aws:iam::${var.account_id}:role/LabRole"

  container_definitions = jsonencode([
    {
      name      = "sensor",
      image     = "${aws_ecr_repository.sensor_repo.repository_url}:latest",
      cpu       = 1024,
      memory    = 2048,
      essential = true,
      environment = [
        { name = "AWS_REGION", value = var.aws_region },
        { name = "AWS_DYNAMO_DB_TABLE_NAME", value = "detections" },
        { name = "AWS_USERS_TABLE_NAME", value = "users" },
        { name = "TRAFFIC_MIRROR_TARGET_ID", value = aws_ec2_traffic_mirror_target.analizador_target.id },
        { name = "VXLAN_PORT", value = "4789" },
        { name = "HTTP_PORT", value = "8080" },
        { name = "WORKERS", value = "4" },
        { name = "QUEUE_MAX", value = "20000" },
        { name = "WINDOW_SECONDS", value = "3.0" },
        { name = "MAX_PKTS_PER_WINDOW", value = "256" },
        { name = "LOG_LEVEL", value = "info" },
        { name = "EMAIL_ENABLED", value = var.enable_email_service ? "true" : "false" },
        { name = "EMAIL_FROM_ADDRESS", value = var.email_from_address },
        { name = "RESEND_API_KEY", value = var.resend_api_key },
        { name = "JWT_SECRET_KEY", value = var.jwt_secret_key },
        { name = "JWT_EXPIRE_MINUTES", value = tostring(var.jwt_expire_minutes) },
        { name = "BASE_URL", value = var.base_url != "" ? var.base_url : "http://${aws_lb.app_nlb.dns_name}" },
        { name = "DASHBOARD_URL", value = var.dashboard_url != "" ? var.dashboard_url : "http://${aws_s3_bucket_website_configuration.dashboard_website.website_endpoint}" }
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

  tags = {
    Name        = "${var.project_name}-sensor-task"
    Environment = var.environment
    Project     = var.project_name
  }
}

resource "aws_lb" "app_nlb" {
  name               = "${var.project_name}-app-nlb"
  load_balancer_type = "network"
  subnets            = [aws_subnet.analizador_public_subnet.id]
  tags = {
    Name        = "${var.project_name}-app-nlb"
    Environment = var.environment
    Project     = var.project_name
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
  tags = { Name = "${var.project_name}-http-tg"
    Environment = var.environment
    Project     = var.project_name
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

resource "aws_ecs_service" "sensor_service" {
  name             = "${var.project_name}-sensor-service"
  cluster          = aws_ecs_cluster.sensor_cluster.id
  task_definition  = aws_ecs_task_definition.sensor_task.arn
  desired_count    = 1
  launch_type      = "FARGATE"
  platform_version = "1.4.0"

  network_configuration {
    subnets          = [aws_subnet.analizador_public_subnet.id, aws_subnet.analizador_private_subnet.id]
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
  tags = { Name = "${var.project_name}-sensor-service"
    Environment = var.environment
    Project     = var.project_name
  }
}

############################################
# TRAFFIC MIRROR TARGET (para que los clientes apunten)
############################################
resource "aws_ec2_traffic_mirror_target" "analizador_target" {
  network_load_balancer_arn = aws_lb.mirror_nlb.arn
  tags = { Name = "${var.project_name}-analizador-target-nlb"
    Environment = var.environment
    Project     = var.project_name
  }

  lifecycle {
    create_before_destroy = true
  }
}

############################################
# TRANSIT GATEWAY (conecta VPC Analizador <-> VPC Cliente)
############################################
resource "aws_ec2_transit_gateway" "main" {
  description                     = "TGW VPC Cliente <-> VPC Analizador"
  default_route_table_association = "enable"
  default_route_table_propagation = "enable"
  dns_support                     = "enable"
  vpn_ecmp_support                = "enable"
  tags = {
    Name        = "${var.project_name}-tgw"
    Environment = var.environment
    Project     = var.project_name
  }
}

resource "aws_ec2_transit_gateway_vpc_attachment" "analizador" {
  subnet_ids         = [aws_subnet.analizador_public_subnet.id, aws_subnet.analizador_private_subnet.id]
  transit_gateway_id = aws_ec2_transit_gateway.main.id
  vpc_id             = aws_vpc.vpc_analizador.id
  tags = {
    Name        = "${var.project_name}-tgw-attach-analizador"
    Environment = var.environment
    Project     = var.project_name
  }
}

############################################
# S3 BUCKET PARA DASHBOARD (Static Website Hosting)
############################################
resource "aws_s3_bucket" "dashboard_bucket" {
  bucket = "${var.project_name}-dashboard-${var.account_id}"

  tags = {
    Name        = "${var.project_name}-dashboard-bucket"
    Environment = var.environment
    Project     = var.project_name
    Purpose     = "Frontend-Dashboard"
  }
}

resource "aws_s3_bucket_versioning" "dashboard_versioning" {
  bucket = aws_s3_bucket.dashboard_bucket.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_website_configuration" "dashboard_website" {
  bucket = aws_s3_bucket.dashboard_bucket.id

  index_document {
    suffix = "index.html"
  }

  error_document {
    key = "index.html"
  }
}

resource "aws_s3_bucket_public_access_block" "dashboard_public_access" {
  bucket = aws_s3_bucket.dashboard_bucket.id

  block_public_acls       = false
  block_public_policy     = false
  ignore_public_acls      = false
  restrict_public_buckets = false
}

resource "aws_s3_bucket_policy" "dashboard_bucket_policy" {
  bucket = aws_s3_bucket.dashboard_bucket.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid       = "PublicReadGetObject"
        Effect    = "Allow"
        Principal = "*"
        Action    = "s3:GetObject"
        Resource  = "${aws_s3_bucket.dashboard_bucket.arn}/*"
      }
    ]
  })

  depends_on = [aws_s3_bucket_public_access_block.dashboard_public_access]
}

resource "aws_s3_bucket_cors_configuration" "dashboard_cors" {
  bucket = aws_s3_bucket.dashboard_bucket.id

  cors_rule {
    allowed_headers = ["*"]
    allowed_methods = ["GET", "HEAD"]
    allowed_origins = ["*"]
    expose_headers  = []
    max_age_seconds = 3000
  }
}

############################################
# Outputs útiles para los clientes
############################################
output "traffic_mirror_target_id" {
  description = "ID del Traffic Mirror Target para que los clientes apunten su tráfico"
  value       = aws_ec2_traffic_mirror_target.analizador_target.id
}

output "mirror_nlb_dns" {
  description = "DNS del NLB interno para mirroring UDP/4789"
  value       = aws_lb.mirror_nlb.dns_name
}

output "app_nlb_dns" {
  description = "DNS del NLB público para la API HTTP (puerto 80 -> 8080)"
  value       = aws_lb.app_nlb.dns_name
}

output "api_base_url" {
  description = "URL base de la API configurada en el contenedor"
  value       = var.base_url != "" ? var.base_url : "http://${aws_lb.app_nlb.dns_name}"
}

output "dashboard_bucket_name" {
  description = "Nombre del bucket S3 para el dashboard"
  value       = aws_s3_bucket.dashboard_bucket.id
}

output "dashboard_website_url" {
  description = "URL completa del website endpoint del dashboard S3"
  value       = "http://${aws_s3_bucket_website_configuration.dashboard_website.website_endpoint}"
}

output "dashboard_url" {
  description = "URL del dashboard configurada en el contenedor (puede ser la del S3 o una personalizada)"
  value       = var.dashboard_url != "" ? var.dashboard_url : "http://${aws_s3_bucket_website_configuration.dashboard_website.website_endpoint}"
}

output "dashboard_website_domain" {
  description = "Dominio regional del bucket S3 (para CloudFront u otros servicios)"
  value       = aws_s3_bucket.dashboard_bucket.bucket_regional_domain_name
}

output "transit_gateway_id" {
  description = "ID del Transit Gateway para conectar VPCs"
  value       = aws_ec2_transit_gateway.main.id
}

output "vpc_analizador_cidr" {
  description = "CIDR de la VPC del analizador"
  value       = aws_vpc.vpc_analizador.cidr_block
}

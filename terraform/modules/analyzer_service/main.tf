# Data sources para obtener información del contexto actual de AWS
data "aws_caller_identity" "current" {} # Obtiene el ID de la cuenta AWS actual
data "aws_region" "current" {}          # Obtiene la región AWS actual

# ECR Repository para almacenar las imágenes Docker del sensor
resource "aws_ecr_repository" "mirror_sensor" {
  name                 = "mirror-sensor"
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }

  tags = var.tags
}

resource "aws_cloudwatch_log_group" "sensor" {
  name              = "/aws/ecs/net-mirror-sensor"
  retention_in_days = 7
  tags              = var.tags
}
resource "aws_security_group" "sensor" {
  name        = "sensor-security-group"
  description = "Permite HTTP 8080 para API; egress all"
  vpc_id      = var.vpc_id

  ingress {
    from_port       = 8080
    to_port         = 8080
    protocol        = "tcp"
    security_groups = [aws_security_group.api.id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = var.tags
}

resource "aws_ecs_cluster" "cluster" {
  name = "mirror-cluster"
  tags = var.tags
}

resource "aws_ecs_task_definition" "task" {
  family                   = "mirror-sensor"
  requires_compatibilities = ["FARGATE"]
  cpu                      = "256"
  memory                   = "512"
  network_mode             = "awsvpc"

  execution_role_arn = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:role/LabRole"
  task_role_arn      = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:role/LabRole"

  runtime_platform {
    cpu_architecture        = "X86_64" # "ARM64"
    operating_system_family = "LINUX"
  }

  container_definitions = jsonencode([
    {
      name      = "sensor",
      image     = var.container_image,
      essential = true,
      portMappings = [
        { containerPort = 8080, protocol = "tcp" }
      ],
      environment = [
        { name = "SM_ENDPOINT_NAME", value = var.sagemaker_endpoint_name },
        { name = "AWS_DEFAULT_REGION", value = var.region },
        { name = "AWS_REGION", value = var.region },
        { name = "ENVIRONMENT", value = "aws" }
      ],
      logConfiguration = {
        logDriver = "awslogs",
        options = {
          awslogs-group         = aws_cloudwatch_log_group.sensor.name,
          awslogs-region        = var.region,
          awslogs-stream-prefix = "sensor"
        }
      }
    }
  ])

  tags = var.tags
}
resource "aws_security_group" "api" {
  name        = "sensor-api-security-group"
  description = "Permite HTTP/HTTPS para API REST"
  vpc_id      = var.vpc_id

  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = var.tags
}
# Network Load Balancer removido - solo usamos Application Load Balancer para HTTP
# resource "aws_lb" "nlb" {
#   name               = "mirror-nlb"
#   internal           = true
#   load_balancer_type = "network"
#   subnets            = var.private_subnet_ids
#   tags               = var.tags
# }
resource "aws_lb" "alb" {
  name               = "sensor-api-alb"
  internal           = false
  load_balancer_type = "application"
  subnets            = var.public_subnet_ids
  security_groups    = [aws_security_group.api.id]
  tags               = var.tags
}

resource "aws_lb_target_group" "http_tg" {
  name        = "sensor-http-tg"
  vpc_id      = var.vpc_id
  port        = 8080
  protocol    = "HTTP"
  target_type = "ip"

  # Health check habilitado (requerido para target type 'ip')
  health_check {
    enabled             = true
    healthy_threshold   = 2
    unhealthy_threshold = 2
    timeout             = 5
    interval            = 30
    path                = "/health"
    matcher             = "200"
    port                = "traffic-port"
    protocol            = "HTTP"
  }

  tags = var.tags
}
resource "aws_lb_listener" "http" {
  load_balancer_arn = aws_lb.alb.arn
  port              = "80"
  protocol          = "HTTP"

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.http_tg.arn
  }
}

resource "aws_ecs_service" "service" {
  name            = "mirror-sensor"
  cluster         = aws_ecs_cluster.cluster.id
  task_definition = aws_ecs_task_definition.task.arn
  desired_count   = 1
  launch_type     = "FARGATE"

  # Health check grace period para HTTP
  health_check_grace_period_seconds = 360

  network_configuration {
    subnets          = var.private_subnet_ids
    security_groups  = [aws_security_group.sensor.id]
    assign_public_ip = true
  }

  # Configuración del load balancer para HTTP
  load_balancer {
    target_group_arn = aws_lb_target_group.http_tg.arn
    container_name   = "sensor"
    container_port   = 8080
  }

  lifecycle { ignore_changes = [desired_count] }
  depends_on = [aws_lb_listener.http]
  tags       = var.tags
}
resource "aws_dynamodb_table" "demo_control" {
  name         = "demo-pcap-control"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "id"

  attribute {
    name = "id"
    type = "S"
  }

  tags = var.tags
}

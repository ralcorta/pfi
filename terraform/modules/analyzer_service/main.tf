# Data sources para obtener información del contexto actual de AWS
data "aws_caller_identity" "current" {}  # Obtiene el ID de la cuenta AWS actual
data "aws_region" "current" {}           # Obtiene la región AWS actual

# Grupo de logs de CloudWatch para almacenar los logs del sensor de tráfico
# Sirve para monitorear y debuggear el comportamiento del sensor de detección de ransomware
# Está relacionado con: ECS task definition (container logs), troubleshooting del sistema
resource "aws_cloudwatch_log_group" "sensor" {
  name              = "/aws/ecs/net-mirror-sensor"
  retention_in_days = 7
  tags              = var.tags
}

# Security Group para controlar el acceso de red al sensor de tráfico
# Permite recibir tráfico UDP en puerto 4789 (VPC Traffic Mirroring) desde VPCs cliente
# Permite salida a internet para conectar con SageMaker y otros servicios AWS
# Está relacionado con: ECS service, VPC endpoint, Load Balancer
resource "aws_security_group" "sensor" {
  name        = "sensor-security-group"
  description = "Permite UDP 4789 desde VPC cliente; egress all"
  vpc_id      = var.vpc_id

  dynamic "ingress" {
    for_each = var.allowed_cidrs
    content {
      from_port   = 4789
      to_port     = 4789
      protocol    = "udp"
      cidr_blocks = [ingress.value]
    }
  }

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

# VPC Endpoint para SageMaker Runtime
# Permite al sensor acceder al modelo de IA de SageMaker sin salir a internet
# Mejora la seguridad y reduce latencia para las inferencias del modelo de detección de ransomware
# Está relacionado con: ECS task (inferencias), Security Group, subnets privadas
resource "aws_vpc_endpoint" "sagemaker_runtime" {
  vpc_id              = var.vpc_id
  service_name        = "com.amazonaws.${var.region}.sagemaker.runtime"
  vpc_endpoint_type   = "Interface"
  private_dns_enabled = true
  subnet_ids          = var.private_subnet_ids
  security_group_ids  = [aws_security_group.sensor.id]
  tags                = var.tags
}

# Cluster ECS Fargate para ejecutar los contenedores del sensor
# Proporciona la infraestructura serverless para ejecutar el sensor de detección de ransomware
# Está relacionado con: ECS service, ECS task definition, auto scaling
resource "aws_ecs_cluster" "cluster" {
  name = "mirror-cluster"
  tags = var.tags
}

# Task Definition de ECS que define cómo ejecutar el contenedor del sensor
# Especifica la imagen Docker, recursos (CPU/memoria), variables de entorno y configuración de logs
# El contenedor ejecuta el sensor de detección de ransomware con acceso al modelo SageMaker
# Está relacionado con: ECS service, CloudWatch logs, SageMaker endpoint, Load Balancer
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
      name         = "sensor",
      image        = var.container_image,
      essential    = true,
      portMappings = [
        { containerPort = 4789, protocol = "udp" },
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

# Security Group para la API HTTP
# Permite acceso HTTP/HTTPS a la API REST
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

# Network Load Balancer para distribuir el tráfico UDP del VPC Mirroring
# Recibe el tráfico duplicado de las VPCs cliente y lo distribuye a las instancias del sensor
# Es interno para mantener la seguridad y no exponer el sensor a internet
# Está relacionado con: Target Group, Listener, ECS service, subnets privadas
resource "aws_lb" "nlb" {
  name               = "mirror-nlb"
  internal           = true
  load_balancer_type = "network"
  subnets            = var.private_subnet_ids
  tags               = var.tags
}

# Application Load Balancer para la API HTTP
# Expone la API REST para health check y consultas de detecciones
# Es interno para mantener la seguridad
resource "aws_lb" "alb" {
  name               = "sensor-api-alb"
  internal           = false
  load_balancer_type = "application"
  subnets            = var.public_subnet_ids
  security_groups    = [aws_security_group.api.id]
  tags               = var.tags
}

# Target Group que define a qué contenedores ECS enviar el tráfico UDP
# Agrupa las instancias del sensor que están ejecutándose en ECS Fargate
# Incluye health checks para verificar que los contenedores estén funcionando correctamente
# Está relacionado con: Load Balancer, ECS service, Listener
resource "aws_lb_target_group" "tg" {
  name        = "tg-udp-4789"
  vpc_id      = var.vpc_id
  port        = 4789
  protocol    = "UDP"
  target_type = "ip"

  health_check {
    protocol            = "TCP"
    port                = "traffic-port"
    healthy_threshold   = 2
    unhealthy_threshold = 2
  }

  tags = var.tags
}

# Target Group para HTTP API
# Define a qué contenedores ECS enviar el tráfico HTTP
resource "aws_lb_target_group" "http_tg" {
  name        = "sensor-http-tg"
  vpc_id      = var.vpc_id
  port        = 8080
  protocol    = "HTTP"
  target_type = "ip"

  health_check {
    enabled             = true
    healthy_threshold   = 2
    interval            = 30
    matcher             = "200"
    path                = "/health"
    port                = "traffic-port"
    protocol            = "HTTP"
    timeout             = 5
    unhealthy_threshold = 2
  }

  tags = var.tags
}

# Listener del Load Balancer que escucha en puerto 4789 para tráfico UDP
# Recibe el tráfico duplicado del VPC Mirroring y lo reenvía al Target Group
# Puerto 4789 es el estándar para VPC Traffic Mirroring en AWS
# Está relacionado con: Load Balancer, Target Group, ECS service
resource "aws_lb_listener" "udp" {
  load_balancer_arn = aws_lb.nlb.arn
  port              = 4789
  protocol          = "UDP"

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.tg.arn
  }
}

# Listener HTTP para la API REST
# Escucha en puerto 80 y redirige al Target Group HTTP
resource "aws_lb_listener" "http" {
  load_balancer_arn = aws_lb.alb.arn
  port              = "80"
  protocol          = "HTTP"

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.http_tg.arn
  }
}

# ECS Service que ejecuta y mantiene las instancias del sensor de detección de ransomware
# Gestiona el número de contenedores en ejecución y los conecta al Load Balancer
# Ejecuta en subnets privadas para seguridad y se conecta al Target Group para recibir tráfico
# Está relacionado con: ECS cluster, Task definition, Load Balancer, Security Group, Auto Scaling
resource "aws_ecs_service" "service" {
  name            = "mirror-sensor"
  cluster         = aws_ecs_cluster.cluster.id
  task_definition = aws_ecs_task_definition.task.arn
  desired_count   = var.min_capacity
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = var.private_subnet_ids
    security_groups  = [aws_security_group.sensor.id]
    assign_public_ip = true
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.tg.arn
    container_name   = "sensor"
    container_port   = 4789
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.http_tg.arn
    container_name   = "sensor"
    container_port   = 8080
  }

  lifecycle { ignore_changes = [desired_count] }
  depends_on = [aws_lb_listener.udp]
  tags       = var.tags
}

# Target de Auto Scaling que define los límites de escalado para el servicio ECS
# Establece el número mínimo y máximo de contenedores del sensor que pueden ejecutarse
# Permite escalar automáticamente según la carga de tráfico de red
# Está relacionado con: ECS service, Auto Scaling policy
resource "aws_appautoscaling_target" "ecs" {
  max_capacity       = var.max_capacity
  min_capacity       = var.min_capacity
  resource_id        = "service/${aws_ecs_cluster.cluster.name}/${aws_ecs_service.service.name}"
  scalable_dimension = "ecs:service:DesiredCount"
  service_namespace  = "ecs"
}

# Política de Auto Scaling basada en utilización de CPU
# Escala automáticamente el número de contenedores del sensor según la carga de CPU
# Mantiene la utilización de CPU cerca del target especificado para optimizar costos y rendimiento
# Está relacionado con: Auto Scaling target, ECS service, CloudWatch metrics
resource "aws_appautoscaling_policy" "cpu_target" {
  name               = "scale-on-cpu"
  policy_type        = "TargetTrackingScaling"
  resource_id        = aws_appautoscaling_target.ecs.resource_id
  scalable_dimension = aws_appautoscaling_target.ecs.scalable_dimension
  service_namespace  = aws_appautoscaling_target.ecs.service_namespace

  target_tracking_scaling_policy_configuration {
    predefined_metric_specification { predefined_metric_type = "ECSServiceAverageCPUUtilization" }
    target_value       = var.cpu_target_percent
    scale_in_cooldown  = 60
    scale_out_cooldown = 60
  }
}

# Tabla DynamoDB para controlar si ejecutar demo .pcap o no
# Almacena un solo registro con un campo string que indica si el sensor debe usar archivos .pcap de demo
# Permite cambiar el comportamiento del sensor sin redeployar la aplicación
# Está relacionado con: ECS task (lectura de configuración), aplicación sensor
resource "aws_dynamodb_table" "demo_control" {
  name           = "demo-pcap-control"
  billing_mode   = "PAY_PER_REQUEST"
  hash_key       = "id"

  attribute {
    name = "id"
    type = "S"
  }

  tags = var.tags
}
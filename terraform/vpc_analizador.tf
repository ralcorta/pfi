# ========================================
# VPC ANALIZADOR - TU SERVICIO DE DETECCIÓN
# ========================================
# Esta VPC recibe tráfico de múltiples clientes via VPC Mirroring
# y lo procesa con el sensor de IA para detectar ransomware

# VPC Principal - Analizador
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

# Internet Gateway para VPC Analizador
resource "aws_internet_gateway" "igw_analizador" {
  vpc_id = aws_vpc.vpc_analizador.id

  tags = {
    Name        = "${var.project_name}-analizador-igw"
    Environment = var.environment
    Project     = var.project_name
    Type        = "Analizador"
  }
}

# Subnet pública para VPC Analizador
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

# Subnet privada para VPC Analizador
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

# Route table para VPC Analizador (pública)
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

# Route table para VPC Analizador (privada)
resource "aws_route_table" "analizador_private_rt" {
  vpc_id = aws_vpc.vpc_analizador.id

  tags = {
    Name        = "${var.project_name}-analizador-private-rt"
    Environment = var.environment
    Project     = var.project_name
    Type        = "Analizador-Private"
  }
}

# Asociación de subnet pública con route table pública
resource "aws_route_table_association" "analizador_public_rta" {
  subnet_id      = aws_subnet.analizador_public_subnet.id
  route_table_id = aws_route_table.analizador_public_rt.id
}

# Asociación de subnet privada con route table privada
resource "aws_route_table_association" "analizador_private_rta" {
  subnet_id      = aws_subnet.analizador_private_subnet.id
  route_table_id = aws_route_table.analizador_private_rt.id
}

# ========================================
# SECURITY GROUPS - VPC ANALIZADOR
# ========================================

# Security Group para el Mirror Target
resource "aws_security_group" "mirror_target" {
  name_prefix = "${var.project_name}-mirror-target"
  vpc_id      = aws_vpc.vpc_analizador.id
  description = "Security group para VPC Mirror Target"

  # Permitir tráfico mirroring de cualquier cliente
  ingress {
    from_port   = 0
    to_port     = 65535
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "Traffic mirroring TCP"
  }

  ingress {
    from_port   = 0
    to_port     = 65535
    protocol    = "udp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "Traffic mirroring UDP"
  }

  # Permitir salida para logs y monitoreo
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
    description = "Salida para logs y monitoreo"
  }

  tags = {
    Name        = "${var.project_name}-mirror-target-sg"
    Environment = var.environment
    Project     = var.project_name
    Purpose     = "VPC-Mirroring"
  }
}

# Security Group para el sensor de IA
resource "aws_security_group" "sensor" {
  name_prefix = "${var.project_name}-sensor"
  vpc_id      = aws_vpc.vpc_analizador.id
  description = "Security group para el sensor de ransomware"

  # Permitir tráfico desde el mirror target
  ingress {
    from_port       = 0
    to_port         = 65535
    protocol        = "tcp"
    security_groups = [aws_security_group.mirror_target.id]
    description     = "Traffic from mirror target"
  }

  # Permitir SSH para administración
  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "SSH for administration"
  }

  # Permitir HTTP para health checks
  ingress {
    from_port   = 8080
    to_port     = 8080
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "Health check endpoint"
  }

  # Salida para logs y monitoreo
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
    description = "Salida para logs y monitoreo"
  }

  tags = {
    Name        = "${var.project_name}-sensor-sg"
    Environment = var.environment
    Project     = var.project_name
    Purpose     = "Ransomware-Detection"
  }
}

# ========================================
# VPC MIRRORING - RECEPTOR DE TRÁFICO
# ========================================

# ENI Mirror Target - Recibe tráfico de múltiples clientes
# Este ENI será usado por el container ECS para recibir tráfico mirroring
resource "aws_network_interface" "mirror_target" {
  subnet_id         = aws_subnet.analizador_private_subnet.id
  private_ips       = ["10.0.2.100"]
  security_groups   = [aws_security_group.mirror_target.id]
  source_dest_check = false # Importante para mirroring

  tags = {
    Name        = "${var.project_name}-mirror-target"
    Environment = var.environment
    Project     = var.project_name
    Purpose     = "VPC-Mirroring"
    Type        = "Mirror-Target"
    ECS         = "true"
  }
}

# ========================================
# ECS NETWORK CONFIGURATION
# ========================================

# Security Group específico para ECS con tráfico mirroring
resource "aws_security_group" "ecs_mirror" {
  name_prefix = "${var.project_name}-ecs-mirror"
  vpc_id      = aws_vpc.vpc_analizador.id
  description = "Security group para ECS container con mirroring"

  # Permitir tráfico mirroring desde el ENI
  ingress {
    from_port       = 0
    to_port         = 65535
    protocol        = "tcp"
    security_groups = [aws_security_group.mirror_target.id]
    description     = "Traffic mirroring from ENI"
  }

  # Permitir HTTP para health checks
  ingress {
    from_port   = 8080
    to_port     = 8080
    protocol    = "tcp"
    cidr_blocks = ["10.0.0.0/16"]
    description = "Health check desde VPC"
  }

  # Salida para logs y monitoreo
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
    description = "Salida para logs y monitoreo"
  }

  tags = {
    Name        = "${var.project_name}-ecs-mirror-sg"
    Environment = var.environment
    Project     = var.project_name
    Purpose     = "ECS-Mirroring"
  }
}

# ========================================
# ECR REPOSITORY - IMAGEN DOCKER DEL SENSOR
# ========================================

# ECR Repository para la imagen del sensor
resource "aws_ecr_repository" "sensor_repo" {
  name                 = "mirror-sensor"
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }

  tags = {
    Name        = "${var.project_name}-sensor-repo"
    Environment = var.environment
    Project     = var.project_name
    Type        = "Docker-Repository"
  }
}

# ECR Lifecycle Policy
resource "aws_ecr_lifecycle_policy" "sensor_repo_policy" {
  repository = aws_ecr_repository.sensor_repo.name

  policy = jsonencode({
    rules = [
      {
        rulePriority = 1
        description  = "Keep last 10 images"
        selection = {
          tagStatus     = "tagged"
          tagPrefixList = ["v"]
          countType     = "imageCountMoreThan"
          countNumber   = 10
        }
        action = {
          type = "expire"
        }
      }
    ]
  })
}

# ========================================
# ECS CLUSTER - CONFIGURACIÓN MÍNIMA
# ========================================

# ECS Cluster para el sensor
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

# ========================================
# ECS TASK DEFINITION - CONFIGURACIÓN MÍNIMA
# ========================================

# ECS Task Definition para el sensor
resource "aws_ecs_task_definition" "sensor_task" {
  family                   = "${var.project_name}-sensor"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = "256" # 0.25 vCPU
  memory                   = "512" # 512 MB
  execution_role_arn       = "arn:aws:iam::339712899854:role/LabRole"
  task_role_arn            = "arn:aws:iam::339712899854:role/LabRole"

  container_definitions = jsonencode([
    {
      name  = "sensor"
      image = "${aws_ecr_repository.sensor_repo.repository_url}:latest"

      # Configuración mínima
      cpu       = 256
      memory    = 512
      essential = true

      # Variables de entorno
      environment = [
        {
          name  = "INTERFACE"
          value = "eth0"
        },
        {
          name  = "FILTER"
          value = "tcp"
        },
        {
          name  = "MODEL_PATH"
          value = "/app/models/convlstm_model.keras"
        }
      ]

      # Health check
      healthCheck = {
        command     = ["CMD-SHELL", "curl -f http://localhost:8080/health || exit 1"]
        interval    = 30
        timeout     = 5
        retries     = 3
        startPeriod = 60
      }

      # Logging simplificado para AWS Academy
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = aws_cloudwatch_log_group.sensor_logs.name
          "awslogs-region"        = var.aws_region
          "awslogs-stream-prefix" = "ecs"
          "awslogs-create-group"  = "true"
        }
      }

      # Puerto para health check
      portMappings = [
        {
          containerPort = 8080
          protocol      = "tcp"
        }
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

# ========================================
# ECS SERVICE - UN SOLO CONTAINER
# ========================================

# ECS Service para mantener el sensor corriendo
resource "aws_ecs_service" "sensor_service" {
  name            = "${var.project_name}-sensor-service"
  cluster         = aws_ecs_cluster.sensor_cluster.id
  task_definition = aws_ecs_task_definition.sensor_task.arn
  desired_count   = 1 # Solo un container
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = [aws_subnet.analizador_private_subnet.id]
    security_groups  = [aws_security_group.ecs_mirror.id]
    assign_public_ip = false
  }

  # No auto-scaling, solo un container (desired_count = 1)

  # Health check grace period
  health_check_grace_period_seconds = 60

  tags = {
    Name        = "${var.project_name}-sensor-service"
    Environment = var.environment
    Project     = var.project_name
    Type        = "ECS-Service"
  }

  depends_on = [aws_ecs_task_definition.sensor_task]
}

# ========================================
# CLOUDWATCH LOGS
# ========================================

# CloudWatch Log Group para el sensor
resource "aws_cloudwatch_log_group" "sensor_logs" {
  name              = "/ecs/${var.project_name}-sensor"
  retention_in_days = 7 # Mínimo para costos

  tags = {
    Name        = "${var.project_name}-sensor-logs"
    Environment = var.environment
    Project     = var.project_name
  }
}

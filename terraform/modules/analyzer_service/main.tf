data "aws_caller_identity" "current" {}
data "aws_region" "current" {}

resource "aws_cloudwatch_log_group" "sensor" {
  name              = "/aws/ecs/net-mirror-sensor"
  retention_in_days = 7
  tags              = var.tags
}

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

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = var.tags
}

resource "aws_vpc_endpoint" "sagemaker_runtime" {
  vpc_id              = var.vpc_id
  service_name        = "com.amazonaws.${var.region}.sagemaker.runtime"
  vpc_endpoint_type   = "Interface"
  private_dns_enabled = true
  subnet_ids          = var.private_subnet_ids
  security_group_ids  = [aws_security_group.sensor.id]
  tags                = var.tags
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
    cpu_architecture        = "ARM64"
    operating_system_family = "LINUX"
  }

  container_definitions = jsonencode([
    {
      name         = "sensor",
      image        = var.container_image,
      essential    = true,
      portMappings = [{ containerPort = 4789, protocol = "udp" }],
      environment = [
        { name = "SM_ENDPOINT_NAME", value = var.sagemaker_endpoint_name }
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

resource "aws_lb" "nlb" {
  name               = "mirror-nlb"
  internal           = true
  load_balancer_type = "network"
  subnets            = var.private_subnet_ids
  tags               = var.tags
}

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

resource "aws_lb_listener" "udp" {
  load_balancer_arn = aws_lb.nlb.arn
  port              = 4789
  protocol          = "UDP"

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.tg.arn
  }
}

resource "aws_ecs_service" "service" {
  name            = "mirror-sensor"
  cluster         = aws_ecs_cluster.cluster.id
  task_definition = aws_ecs_task_definition.task.arn
  desired_count   = var.min_capacity
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = var.private_subnet_ids
    security_groups  = [aws_security_group.sensor.id]
    assign_public_ip = false
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.tg.arn
    container_name   = "sensor"
    container_port   = 4789
  }

  lifecycle { ignore_changes = [desired_count] }
  depends_on = [aws_lb_listener.udp]
  tags       = var.tags
}

resource "aws_appautoscaling_target" "ecs" {
  max_capacity       = var.max_capacity
  min_capacity       = var.min_capacity
  resource_id        = "service/${aws_ecs_cluster.cluster.name}/${aws_ecs_service.service.name}"
  scalable_dimension = "ecs:service:DesiredCount"
  service_namespace  = "ecs"
}

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

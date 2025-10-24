# Data sources para el módulo VPC Primaria

# Usar el role LabRole existente para ECS
data "aws_iam_role" "lab_role" {
  name = "LabRole"
}

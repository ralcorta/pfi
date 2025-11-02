############################################
# PROVIDER & BASE
############################################
terraform {
  required_version = ">= 1.0"
  required_providers {
    aws  = { source = "hashicorp/aws", version = "~> 5.0" }
    http = { source = "hashicorp/http", version = "~> 3.4" }
  }
}

provider "aws" {
  region = var.aws_region
  default_tags { tags = var.tags }
}

############################################
# REMOTE STATE - Leer outputs del analizador
############################################
data "terraform_remote_state" "analizer" {
  backend = "local"

  config = {
    path = "${path.root}/../analizer/terraform.tfstate"
  }

  # Permitir que falle si el analizador no está desplegado todavía
  # Las variables tendrán valores por defecto que se pueden sobrescribir
}


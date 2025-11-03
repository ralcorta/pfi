variable "aws_region" { default = "us-east-1" }
variable "account_id" { default = "339712899854" }
variable "project_name" { default = "sensor-analyzer" }
variable "environment" { default = "production" }
variable "tags" {
  description = "Tagging por defecto"
  type        = map(string)
  default     = {}
}

variable "availability_zone_1" {
  description = "Primera zona de disponibilidad"
}
variable "availability_zone_2" {
  description = "Segunda zona de disponibilidad"
}

variable "vpc_2_cidr" { default = "10.20.0.0/16" }
variable "vpc_2_public_subnet_cidr" { default = "10.20.1.0/24" }
variable "vpc_2_private_subnet_cidr" { default = "10.20.2.0/24" }
variable "key_name" {
  description = "Nombre de la clave SSH para instancias EC2"
}
variable "client_ami_id" {
  default     = "ami-0c02fb55956c7d316"
  description = "AMI ID para la instancia cliente"
}

variable "client_email" {
  description = "Email del cliente registrado en el dashboard para obtener config automática"
  type        = string
}

variable "api_url" {
  description = <<-EOT
    URL completa del endpoint de la API para obtener la configuración del cliente.
    Debe incluir el endpoint completo: http://<nlb-dns>/v1/clients/terraform-config
    Si esta vacio (default), se obtendra automaticamente del remote state del analizador.
    
    Ejemplo: http://sensor-analyzer-app-nlb-xxx.elb.us-east-1.amazonaws.com/v1/clients/terraform-config
  EOT
  type        = string
  default     = ""
}

variable "transit_gateway_id" {
  description = "ID del Transit Gateway para conectar VPCs. Si está vacio, se obtendra automaticamente del remote state del analizador."
  type        = string
  default     = ""
}

variable "vpc_1_cidr" {
  description = "CIDR de la VPC del analizador (para rutas Transit Gateway). Si está vacio, se obtendra automaticamente del remote state del analizador."
  type        = string
  default     = ""
}


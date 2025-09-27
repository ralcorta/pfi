variable "region" { type = string }
variable "vpc_id" { type = string }
variable "private_subnet_ids" { type = list(string) }
variable "allowed_cidrs" { type = list(string) }
variable "container_image" {
  type = string
}

variable "sagemaker_endpoint_name" {
  type = string
}

variable "min_capacity" {
  type    = number
  default = 1
}

variable "max_capacity" {
  type    = number
  default = 5
}

variable "cpu_target_percent" {
  type    = number
  default = 80
}

variable "tags" {
  type    = map(string)
  default = {}
}

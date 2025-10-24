variable "region" { type = string }
variable "vpc_id" { type = string }
variable "private_subnet_ids" { type = list(string) }
variable "public_subnet_ids" { type = list(string) }
variable "allowed_cidrs" { type = list(string) }
variable "container_image" {
  type = string
}

variable "sagemaker_endpoint_name" {
  type = string
}


variable "tags" {
  type    = map(string)
  default = {}
}

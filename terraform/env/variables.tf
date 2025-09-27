variable "region" { type = string }
variable "analyzer_vpc_id" { type = string }
variable "analyzer_subnets" { type = list(string) }
variable "container_image" { type = string }
variable "sagemaker_endpoint" {
  type = string
}

variable "allowed_ingress_cidr" {
  type = string
}

variable "tags" {
  type    = map(string)
  default = {}
}

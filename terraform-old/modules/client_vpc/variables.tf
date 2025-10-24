variable "region" { type = string }
variable "allowed_ingress_cidr" {
  type = string
}

variable "nlb_arn" {
  type = string
}

variable "tags" {
  type    = map(string)
  default = {}
}

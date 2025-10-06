module "analyzer" {
  source                  = "../modules/analyzer_service"
  region                  = var.region
  vpc_id                  = var.analyzer_vpc_id
  private_subnet_ids      = var.analyzer_subnets
  public_subnet_ids       = var.analyzer_subnets
  allowed_cidrs           = ["172.31.0.0/16"]
  container_image         = var.container_image
  sagemaker_endpoint_name = var.sagemaker_endpoint
  min_capacity            = 1
  max_capacity            = 5
  cpu_target_percent      = 80
  tags                    = var.tags
}

# module "client" {
#   source               = "../modules/client_vpc"
#   region               = var.region
#   nlb_arn              = module.analyzer.nlb_arn
#   allowed_ingress_cidr = var.allowed_ingress_cidr
#   tags                 = var.tags
# }

output "nlb_dns" { value = module.analyzer.nlb_dns }
output "nlb_arn" { value = module.analyzer.nlb_arn }
output "alb_dns" { value = module.analyzer.alb_dns }
# output "client_vpc_id" { value = module.client.client_vpc_id }

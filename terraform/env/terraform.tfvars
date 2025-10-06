region          = "us-east-1"
analyzer_vpc_id = "vpc-01c47e35bacf9d921"
analyzer_subnets = [
  "subnet-0394f1c697668afb6",
  "subnet-016ef34ab9b5d64f0",
  "subnet-0f84a9edb6e6164d3",
  "subnet-096dc00a35a9ebe82",
  "subnet-09de370d51e9bdb18",
  "subnet-00377007e619fdad5",
]
container_image      = "339712899854.dkr.ecr.us-east-1.amazonaws.com/mirror-sensor:latest"
sagemaker_endpoint   = "sm-detector"
allowed_ingress_cidr = "0.0.0.0/0"

tags = {
  Project = "NetMirror-ML"
  Env     = "production"
}

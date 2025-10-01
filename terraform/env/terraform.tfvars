region          = "us-east-1"
analyzer_vpc_id = "vpc-04f3ea9a31c5074e6"
analyzer_subnets = [
  "subnet-08183d25308a7b30d",
  "subnet-0dc22891c19569ebb",
  "subnet-0f5a6094224b28196",
  "subnet-0a51ede7059f05a4d",
  "subnet-06eea1669cf32203c",
  "subnet-00d8a8a7f5e57e86e"
]
container_image      = "123456789012.dkr.ecr.us-east-1.amazonaws.com/mirror-sensor:latest"
sagemaker_endpoint   = "sm-detector"
allowed_ingress_cidr = "131.229.145.26"

tags = {
  Project = "NetMirror-ML"
  Env     = "academy"
}



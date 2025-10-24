data "aws_ami" "al2" {
  most_recent = true
  owners      = ["amazon"]

  filter {
    name   = "name"
    values = ["amzn2-ami-hvm-*-x86_64-gp2"]
  }
}

resource "aws_vpc" "client" {
  cidr_block = "10.100.0.0/16"
  tags       = merge(var.tags, { Name = "ClientVPC" })
}

resource "aws_subnet" "public_a" {
  vpc_id                  = aws_vpc.client.id
  cidr_block              = "10.100.1.0/24"
  availability_zone       = "${var.region}a"
  map_public_ip_on_launch = true
  tags                    = merge(var.tags, { Name = "ClientPublicA" })
}

resource "aws_internet_gateway" "igw" {
  vpc_id = aws_vpc.client.id
  tags   = var.tags
}

resource "aws_route_table" "rt_public" {
  vpc_id = aws_vpc.client.id
  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.igw.id
  }
  tags = var.tags
}

resource "aws_route_table_association" "rt_assoc" {
  subnet_id      = aws_subnet.public_a.id
  route_table_id = aws_route_table.rt_public.id
}

resource "aws_security_group" "ec2" {
  name        = "sg-client-ec2"
  description = "SSH opcional"
  vpc_id      = aws_vpc.client.id

  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = [var.allowed_ingress_cidr]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = var.tags
}

resource "aws_instance" "dummy" {
  ami                         = data.aws_ami.al2.id
  instance_type               = "t3.micro"
  subnet_id                   = aws_subnet.public_a.id
  vpc_security_group_ids      = [aws_security_group.ec2.id]
  associate_public_ip_address = true
  tags                        = merge(var.tags, { Name = "DummyClientEC2" })
}

resource "aws_ec2_traffic_mirror_filter" "all" {
  description = "Allow all"
  tags        = var.tags
}

resource "aws_ec2_traffic_mirror_filter_rule" "ingress" {
  traffic_mirror_filter_id = aws_ec2_traffic_mirror_filter.all.id
  rule_number              = 1
  rule_action              = "accept"
  traffic_direction        = "ingress"
  destination_cidr_block   = "0.0.0.0/0"
  source_cidr_block        = "0.0.0.0/0"
  protocol                 = -1
}

resource "aws_ec2_traffic_mirror_filter_rule" "egress" {
  traffic_mirror_filter_id = aws_ec2_traffic_mirror_filter.all.id
  rule_number              = 1
  rule_action              = "accept"
  traffic_direction        = "egress"
  destination_cidr_block   = "0.0.0.0/0"
  source_cidr_block        = "0.0.0.0/0"
  protocol                 = -1
}

resource "aws_ec2_traffic_mirror_target" "target_nlb" {
  network_load_balancer_arn = var.nlb_arn
  description               = "NLB Target for ECS Sensor"
  tags                      = var.tags
}

resource "aws_ec2_traffic_mirror_session" "session" {
  network_interface_id     = aws_instance.dummy.primary_network_interface_id
  traffic_mirror_target_id = aws_ec2_traffic_mirror_target.target_nlb.id
  traffic_mirror_filter_id = aws_ec2_traffic_mirror_filter.all.id
  session_number           = 1
  tags                     = var.tags
}

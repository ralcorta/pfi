output "client_vpc_id" { value = aws_vpc.client.id }
output "client_subnet_id" { value = aws_subnet.public_a.id }
output "dummy_instance_id" { value = aws_instance.dummy.id }

output "instance_public_ip" {
  description = "The public IP address of the EC2 instance."
  value       = aws_instance.app_server.public_ip
}

output "instance_public_dns" {
  description = "The public DNS name of the EC2 instance."
  value       = aws_instance.app_server.public_dns
}

output "vpc_id" {
  description = "The ID of the created VPC."
  value       = aws_vpc.app_vpc.id
}

output "security_group_id" {
  description = "The ID of the created Security Group."
  value       = aws_security_group.app_sg.id
}
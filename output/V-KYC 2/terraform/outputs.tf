output "vpc_id" {
  description = "The ID of the VPC"
  value       = aws_vpc.main.id
}

output "ec2_public_ip" {
  description = "The public IP address of the EC2 instance"
  value       = aws_instance.app_server.public_ip
}

output "ec2_private_ip" {
  description = "The private IP address of the EC2 instance"
  value       = aws_instance.app_server.private_ip
}

output "rds_endpoint" {
  description = "The endpoint of the RDS PostgreSQL instance"
  value       = aws_db_instance.postgres.address
}

output "rds_port" {
  description = "The port of the RDS PostgreSQL instance"
  value       = aws_db_instance.postgres.port
}

output "s3_bucket_name" {
  description = "The name of the S3 bucket for recordings"
  value       = aws_s3_bucket.recordings.id
}

output "ssh_command" {
  description = "SSH command to connect to the EC2 instance"
  value       = "ssh -i ~/.ssh/id_rsa ubuntu@${aws_instance.app_server.public_ip}" # Adjust key path and user
}
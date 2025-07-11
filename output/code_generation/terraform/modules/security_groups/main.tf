variable "project_name" {
  description = "Name of the project."
  type        = string
}

variable "environment" {
  description = "Deployment environment."
  type        = string
}

variable "vpc_id" {
  description = "The ID of the VPC to create security groups in."
  type        = string
}

# Security Group for Application Load Balancer (ALB)
# Allows inbound HTTP/HTTPS traffic from anywhere
resource "aws_security_group" "alb_sg" {
  name        = "${var.project_name}-${var.environment}-alb-sg"
  description = "Security group for ALB, allowing HTTP/HTTPS traffic"
  vpc_id      = var.vpc_id

  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "Allow HTTP from anywhere"
  }

  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "Allow HTTPS from anywhere"
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
    description = "Allow all outbound traffic"
  }

  tags = {
    Name        = "${var.project_name}-${var.environment}-alb-sg"
    Project     = var.project_name
    Environment = var.environment
  }
}

# Security Group for Application Instances (EC2/ECS/EKS nodes)
# Allows inbound traffic from ALB, SSH from specific IPs (for management)
resource "aws_security_group" "app_sg" {
  name        = "${var.project_name}-${var.environment}-app-sg"
  description = "Security group for application instances"
  vpc_id      = var.vpc_id

  # Inbound from ALB (HTTP/FastAPI port)
  ingress {
    from_port       = 8000 # FastAPI default port
    to_port         = 8000
    protocol        = "tcp"
    security_groups = [aws_security_group.alb_sg.id]
    description     = "Allow traffic from ALB"
  }

  # Inbound SSH for management (restrict to specific IPs in production)
  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"] # WARNING: Restrict this to your office/VPN IP in production!
    description = "Allow SSH from anywhere (for demo, restrict in prod)"
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
    description = "Allow all outbound traffic"
  }

  tags = {
    Name        = "${var.project_name}-${var.environment}-app-sg"
    Project     = var.project_name
    Environment = var.environment
  }
}

# Outputs
output "alb_sg_id" {
  description = "The ID of the ALB security group."
  value       = aws_security_group.alb_sg.id
}

output "app_sg_id" {
  description = "The ID of the application security group."
  value       = aws_security_group.app_sg.id
}
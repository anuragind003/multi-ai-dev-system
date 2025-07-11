# This Terraform configuration is a placeholder for deploying the Docker host.
# In a real-world scenario, you would provision an EC2 instance, VPC, security groups,
# and potentially an ECS cluster or Kubernetes cluster.

# Configure the AWS provider
provider "aws" {
  region = "us-east-1" # Choose your desired AWS region
}

# --- Placeholder for a simple EC2 instance to run Docker Compose ---
# This is a minimal example. For production, consider:
# - Dedicated VPC, subnets, route tables, internet gateway
# - More robust security groups (e.g., limiting SSH access)
# - IAM roles for EC2 instance
# - User data script to install Docker and Docker Compose
# - Auto Scaling Group for high availability
# - Load Balancer (ALB) in front of the application

resource "aws_vpc" "main" {
  cidr_block = "10.0.0.0/16"
  tags = {
    Name = "fastapi-elk-vpc"
  }
}

resource "aws_subnet" "public" {
  vpc_id            = aws_vpc.main.id
  cidr_block        = "10.0.1.0/24"
  availability_zone = "${var.aws_region}a"
  map_public_ip_on_launch = true
  tags = {
    Name = "fastapi-elk-public-subnet"
  }
}

resource "aws_internet_gateway" "gw" {
  vpc_id = aws_vpc.main.id
  tags = {
    Name = "fastapi-elk-igw"
  }
}

resource "aws_route_table" "public" {
  vpc_id = aws_vpc.main.id
  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.gw.id
  }
  tags = {
    Name = "fastapi-elk-public-rt"
  }
}

resource "aws_route_table_association" "public" {
  subnet_id      = aws_subnet.public.id
  route_table_id = aws_route_table.public.id
}

resource "aws_security_group" "fastapi_elk_sg" {
  name        = "fastapi-elk-sg"
  description = "Allow HTTP, HTTPS, SSH, and ELK ports"
  vpc_id      = aws_vpc.main.id

  ingress {
    description = "SSH from anywhere"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"] # Restrict this in production!
  }

  ingress {
    description = "HTTP from anywhere (FastAPI)"
    from_port   = 8000
    to_port     = 8000
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    description = "Kibana from anywhere"
    from_port   = 5601
    to_port     = 5601
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    description = "Elasticsearch from anywhere (for testing/direct access)"
    from_port   = 9200
    to_port     = 9200
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    description = "Logstash TCP input from anywhere"
    from_port   = 5000
    to_port     = 5000
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "fastapi-elk-sg"
  }
}

resource "aws_instance" "docker_host" {
  ami           = "ami-053b0d53c279acc90" # Ubuntu Server 22.04 LTS (HVM), SSD Volume Type - us-east-1
  instance_type = "t3.medium" # t3.medium or t3.large recommended for ELK stack
  subnet_id     = aws_subnet.public.id
  vpc_security_group_ids = [aws_security_group.fastapi_elk_sg.id]
  key_name      = "your-ssh-key" # Replace with your SSH key pair name
  associate_public_ip_address = true

  user_data = <<-EOF
              #!/bin/bash
              sudo apt-get update -y
              sudo apt-get install -y apt-transport-https ca-certificates curl software-properties-common
              curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg
              echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
              sudo apt-get update -y
              sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
              sudo usermod -aG docker ubuntu
              # Install Docker Compose V2 (docker-compose-plugin)
              sudo systemctl enable docker
              sudo systemctl start docker
              EOF

  tags = {
    Name = "FastAPI-ELK-Docker-Host"
  }
}

output "public_ip" {
  description = "The public IP address of the Docker host"
  value       = aws_instance.docker_host.public_ip
}

variable "aws_region" {
  description = "The AWS region to deploy resources in."
  type        = string
  default     = "us-east-1"
}
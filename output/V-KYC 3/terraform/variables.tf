# variables.tf - Terraform variable definitions

variable "aws_region" {
  description = "The AWS region to deploy resources in."
  type        = string
  default     = "us-east-1"
}

variable "project_name" {
  description = "Name of the project, used for resource tagging."
  type        = string
  default     = "fastapi-operational-demo"
}

variable "vpc_cidr_block" {
  description = "CIDR block for the VPC."
  type        = string
  default     = "10.0.0.0/16"
}

variable "public_subnet_cidr_block" {
  description = "CIDR block for the public subnet."
  type        = string
  default     = "10.0.1.0/24"
}

variable "ami_id" {
  description = "The AMI ID for the EC2 instance (e.g., Ubuntu 22.04 LTS)."
  type        = string
  # Find latest Ubuntu LTS AMI for your region:
  # aws ec2 describe-images --owners 099720109477 --filters "Name=name,Values=ubuntu/images/hvm-ssd/ubuntu-jammy-22.04-amd64-server-*" "Name=state,Values=available" --query "sort_by(Images, &CreationDate)[-1].ImageId" --output text
  default     = "ami-053b0d53c279acc90" # Example: Ubuntu Server 22.04 LTS (HVM), SSD Volume Type - us-east-1
}

variable "instance_type" {
  description = "The EC2 instance type."
  type        = string
  default     = "t3.medium" # Or t3.small for smaller loads
}

variable "public_key_path" {
  description = "Path to the SSH public key file (e.g., ~/.ssh/id_rsa.pub)."
  type        = string
  default     = "~/.ssh/id_rsa.pub" # IMPORTANT: Change this to your actual public key path
}
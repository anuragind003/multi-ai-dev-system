# variables.tf
# Terraform variables for AWS EC2 deployment

variable "aws_region" {
  description = "The AWS region to deploy resources in."
  type        = string
  default     = "us-east-1" # Example region
}

variable "ami_id" {
  description = "The AMI ID for the EC2 instance (e.g., Ubuntu 20.04 LTS HVM SSD)."
  type        = string
  # Find latest Ubuntu LTS AMI for your region:
  # aws ec2 describe-images --owners 099720109477 --filters "Name=name,Values=ubuntu/images/hvm-ssd/ubuntu-focal-20.04-amd64-server-*" "Name=state,Values=available" --query "reverse(sort_by(Images, &CreationDate))[:1].ImageId" --output text
  default     = "ami-053b04d48d070660f" # Example: Ubuntu Server 20.04 LTS (HVM), SSD Volume Type, us-east-1
}

variable "instance_type" {
  description = "The EC2 instance type."
  type        = string
  default     = "t3.micro" # Cost-effective for testing
}

variable "key_pair_name" {
  description = "The name of the EC2 Key Pair to use for SSH access."
  type        = string
  # Ensure you have created this key pair in AWS console or via `aws ec2 create-key-pair`
  # Example: default = "my-ec2-key"
}

variable "app_name" {
  description = "Name of the application, used for tagging resources."
  type        = string
  default     = "fastapi-monolith"
}

variable "environment" {
  description = "Deployment environment (e.g., staging, production)."
  type        = string
  default     = "staging"
}

variable "create_vpc" {
  description = "Set to true to create a new VPC, subnet, and IGW. Set to false to use default VPC."
  type        = bool
  default     = false # Set to true if you want a dedicated VPC
}
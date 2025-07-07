terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 4.0"
    }
  }
}

provider "aws" {
  region = "us-west-2" # Replace with your region
}

resource "aws_instance" "backend" {
  ami           = "ami-0c55b31ad2299a701" # Replace with your AMI ID
  instance_type = "t2.micro"
  # ... other configurations ...
}

# ... other Terraform resources ...
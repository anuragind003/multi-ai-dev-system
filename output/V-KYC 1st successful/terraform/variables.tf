variable "aws_region" {
  description = "The AWS region to deploy resources into."
  type        = string
  default     = "us-east-1"
}

variable "project_name" {
  description = "The name of the project, used for naming resources."
  type        = string
  default     = "fastapi-app"
}

variable "environment" {
  description = "The deployment environment (e.g., development, staging, production)."
  type        = string
  default     = "production"
}

variable "ecr_repository_name" {
  description = "Name of the ECR repository for the application image."
  type        = string
  default     = "fastapi-production-service"
}

variable "ecs_cluster_name" {
  description = "Name of the ECS cluster."
  type        = string
  default     = "fastapi-production-cluster"
}

variable "ecs_service_name" {
  description = "Name of the ECS service."
  type        = string
  default     = "fastapi-production-service"
}

variable "task_cpu" {
  description = "The number of CPU units reserved for the container. (e.g., 256, 512, 1024)"
  type        = number
  default     = 256 # 0.25 vCPU
}

variable "task_memory" {
  description = "The amount of memory (in MiB) reserved for the container. (e.g., 512, 1024, 2048)"
  type        = number
  default     = 512 # 0.5 GB
}

variable "desired_task_count" {
  description = "The initial number of desired running tasks for the service."
  type        = number
  default     = 1
}

variable "min_task_count" {
  description = "The minimum number of tasks for auto-scaling."
  type        = number
  default     = 1
}

variable "max_task_count" {
  description = "The maximum number of tasks for auto-scaling."
  type        = number
  default     = 5
}
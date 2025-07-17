output "alb_dns_name" {
  description = "The DNS name of the Application Load Balancer."
  value       = aws_lb.app_alb.dns_name
}

output "ecs_cluster_name" {
  description = "The name of the ECS cluster."
  value       = aws_ecs_cluster.main.name
}

output "ecs_service_name" {
  description = "The name of the ECS service."
  value       = aws_ecs_service.app_service.name
}

output "ecr_repository_url" {
  description = "The URL of the ECR repository."
  value       = aws_ecr_repository.app_repo.repository_url
}

output "cloudwatch_log_group_name" {
  description = "The name of the CloudWatch Log Group for ECS logs."
  value       = aws_cloudwatch_log_group.ecs_logs.name
}
# Configure the AWS Provider
provider "aws" {
  region = var.aws_region
}

# --- VPC and Networking (Minimal for example, use existing VPC in production) ---
resource "aws_vpc" "main" {
  cidr_block = "10.0.0.0/16"
  enable_dns_hostnames = true
  enable_dns_support   = true
  tags = {
    Name = "${var.project_name}-${var.environment}-vpc"
  }
}

resource "aws_subnet" "public" {
  count             = 2 # Create 2 public subnets for high availability
  vpc_id            = aws_vpc.main.id
  cidr_block        = cidrsubnet(aws_vpc.main.cidr_block, 8, count.index) # 10.0.0.0/24, 10.0.1.0/24
  availability_zone = data.aws_availability_zones.available.names[count.index]
  map_public_ip_on_launch = true
  tags = {
    Name = "${var.project_name}-${var.environment}-public-subnet-${count.index}"
  }
}

resource "aws_internet_gateway" "gw" {
  vpc_id = aws_vpc.main.id
  tags = {
    Name = "${var.project_name}-${var.environment}-igw"
  }
}

resource "aws_route_table" "public" {
  vpc_id = aws_vpc.main.id
  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.gw.id
  }
  tags = {
    Name = "${var.project_name}-${var.environment}-public-rt"
  }
}

resource "aws_route_table_association" "public" {
  count          = length(aws_subnet.public)
  subnet_id      = aws_subnet.public[count.index].id
  route_table_id = aws_route_table.public.id
}

data "aws_availability_zones" "available" {
  state = "available"
}

# --- Security Group for ALB and ECS ---
resource "aws_security_group" "alb_sg" {
  name        = "${var.project_name}-${var.environment}-alb-sg"
  description = "Allow HTTP/HTTPS inbound traffic to ALB"
  vpc_id      = aws_vpc.main.id

  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
  ingress {
    from_port   = 443
    to_port     = 443
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
    Name = "${var.project_name}-${var.environment}-alb-sg"
  }
}

resource "aws_security_group" "ecs_sg" {
  name        = "${var.project_name}-${var.environment}-ecs-sg"
  description = "Allow traffic from ALB to ECS tasks"
  vpc_id      = aws_vpc.main.id

  ingress {
    from_port       = 8000 # FastAPI app port
    to_port         = 8000
    protocol        = "tcp"
    security_groups = [aws_security_group.alb_sg.id] # Only allow traffic from ALB
  }
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"] # Allow all outbound traffic (e.g., to databases, external APIs)
  }
  tags = {
    Name = "${var.project_name}-${var.environment}-ecs-sg"
  }
}

# --- ECR Repository ---
resource "aws_ecr_repository" "app_repo" {
  name                 = var.ecr_repository_name
  image_tag_mutability = "MUTABLE" # Or IMMUTABLE for stricter control
  image_scanning_configuration {
    scan_on_push = true
  }
  tags = {
    Name = "${var.project_name}-${var.environment}-ecr"
  }
}

# --- ECS Cluster ---
resource "aws_ecs_cluster" "main" {
  name = var.ecs_cluster_name
  tags = {
    Name = "${var.project_name}-${var.environment}-ecs-cluster"
  }
}

# --- IAM Roles for ECS ---
resource "aws_iam_role" "ecs_task_execution_role" {
  name = "${var.project_name}-${var.environment}-ecs-task-execution-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Action = "sts:AssumeRole",
        Effect = "Allow",
        Principal = {
          Service = "ecs-tasks.amazonaws.com"
        }
      }
    ]
  })
  tags = {
    Name = "${var.project_name}-${var.environment}-ecs-task-execution-role"
  }
}

resource "aws_iam_role_policy_attachment" "ecs_task_execution_role_policy" {
  role       = aws_iam_role.ecs_task_execution_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

resource "aws_iam_role_policy_attachment" "ecs_task_execution_secrets_manager_policy" {
  role       = aws_iam_role.ecs_task_execution_role.name
  policy_arn = "arn:aws:iam::aws:policy/SecretsManagerReadWrite" # Or more granular policy
}

resource "aws_iam_role" "ecs_task_role" {
  name = "${var.project_name}-${var.environment}-ecs-task-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Action = "sts:AssumeRole",
        Effect = "Allow",
        Principal = {
          Service = "ecs-tasks.amazonaws.com"
        }
      }
    ]
  })
  tags = {
    Name = "${var.project_name}-${var.environment}-ecs-task-role"
  }
}

# --- CloudWatch Log Group ---
resource "aws_cloudwatch_log_group" "ecs_logs" {
  name              = "/ecs/${var.ecs_service_name}"
  retention_in_days = 30 # Adjust retention as needed
  tags = {
    Name = "${var.project_name}-${var.environment}-ecs-logs"
  }
}

# --- Secrets Manager (Example) ---
resource "aws_secretsmanager_secret" "app_secret_key" {
  name        = "${var.project_name}/${var.environment}/my-app-secret-key"
  description = "Secret key for the FastAPI application"
  tags = {
    Name = "${var.project_name}-${var.environment}-app-secret-key"
  }
}

resource "aws_secretsmanager_secret_version" "app_secret_key_version" {
  secret_id     = aws_secretsmanager_secret.app_secret_key.id
  secret_string = jsonencode({
    MY_SECRET_KEY = "super_secret_value_from_secrets_manager" # Replace with actual secret
  })
}

# --- ECS Task Definition ---
resource "aws_ecs_task_definition" "app_task" {
  family                   = var.ecs_service_name
  cpu                      = var.task_cpu
  memory                   = var.task_memory
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  execution_role_arn       = aws_iam_role.ecs_task_execution_role.arn
  task_role_arn            = aws_iam_role.ecs_task_role.arn

  container_definitions = jsonencode([
    {
      name      = var.ecs_service_name
      image     = "${aws_ecr_repository.app_repo.repository_url}:latest" # Image will be updated by CI/CD
      cpu       = var.task_cpu
      memory    = var.task_memory
      essential = true
      portMappings = [
        {
          containerPort = 8000
          hostPort      = 8000
          protocol      = "tcp"
        }
      ]
      environment = [
        {
          name  = "APP_ENV"
          value = var.environment
        }
      ]
      secrets = [
        {
          name      = "MY_SECRET_KEY"
          valueFrom = aws_secretsmanager_secret.app_secret_key.arn
        }
      ]
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = aws_cloudwatch_log_group.ecs_logs.name
          "awslogs-region"        = var.aws_region
          "awslogs-stream-prefix" = "ecs"
        }
      }
      healthCheck = {
        command     = ["CMD-SHELL", "curl -f http://localhost:8000/health || exit 1"]
        interval    = 30
        timeout     = 10
        retries     = 3
        startPeriod = 5
      }
    }
  ])
  tags = {
    Name = "${var.project_name}-${var.environment}-app-task"
  }
}

# --- Application Load Balancer (ALB) ---
resource "aws_lb" "app_alb" {
  name               = "${var.project_name}-${var.environment}-alb"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [aws_security_group.alb_sg.id]
  subnets            = aws_subnet.public[*].id
  tags = {
    Name = "${var.project_name}-${var.environment}-alb"
  }
}

resource "aws_lb_target_group" "app_tg" {
  name        = "${var.project_name}-${var.environment}-tg"
  port        = 8000 # Container port
  protocol    = "HTTP"
  vpc_id      = aws_vpc.main.id
  target_type = "ip" # Fargate uses IP targets

  health_check {
    path                = "/health"
    protocol            = "HTTP"
    matcher             = "200"
    interval            = 30
    timeout             = 5
    healthy_threshold   = 2
    unhealthy_threshold = 2
  }
  tags = {
    Name = "${var.project_name}-${var.environment}-tg"
  }
}

resource "aws_lb_listener" "http_listener" {
  load_balancer_arn = aws_lb.app_alb.arn
  port              = 80
  protocol          = "HTTP"

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.app_tg.arn
  }
  tags = {
    Name = "${var.project_name}-${var.environment}-http-listener"
  }
}

# Optional: HTTPS listener with ACM certificate
# resource "aws_lb_listener" "https_listener" {
#   load_balancer_arn = aws_lb.app_alb.arn
#   port              = 443
#   protocol          = "HTTPS"
#   ssl_policy        = "ELBSecurityPolicy-2016-08"
#   certificate_arn   = "arn:aws:acm:YOUR_REGION:YOUR_ACCOUNT_ID:certificate/YOUR_CERT_ID" # Replace with your ACM certificate ARN

#   default_action {
#     type             = "forward"
#     target_group_arn = aws_lb_target_group.app_tg.arn
#   }
# }

# --- ECS Service ---
resource "aws_ecs_service" "app_service" {
  name            = var.ecs_service_name
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.app_task.arn
  desired_count   = var.desired_task_count
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = aws_subnet.public[*].id
    security_groups  = [aws_security_group.ecs_sg.id]
    assign_public_ip = true # Fargate tasks need public IP if in public subnet
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.app_tg.arn
    container_name   = var.ecs_service_name
    container_port   = 8000
  }

  # Auto Scaling
  lifecycle {
    ignore_changes = [desired_count] # Let auto-scaling manage desired_count
  }
  tags = {
    Name = "${var.project_name}-${var.environment}-app-service"
  }
}

# --- Auto Scaling Policy ---
resource "aws_appautoscaling_target" "ecs_target" {
  max_capacity       = var.max_task_count
  min_capacity       = var.min_task_count
  resource_id        = "service/${aws_ecs_cluster.main.name}/${aws_ecs_service.app_service.name}"
  scalable_dimension = "ecs:service:DesiredCount"
  service_namespace  = "ecs"
}

resource "aws_appautoscaling_policy" "ecs_cpu_scaling" {
  name               = "${var.project_name}-${var.environment}-cpu-scaling-policy"
  policy_type        = "TargetTrackingScaling"
  resource_id        = aws_appautoscaling_target.ecs_target.resource_id
  scalable_dimension = aws_appautoscaling_target.ecs_target.scalable_dimension
  service_namespace  = aws_appautoscaling_target.ecs_target.service_namespace

  target_tracking_scaling_policy_configuration {
    predefined_metric_specification {
      predefined_metric_type = "ECSServiceAverageCPUUtilization"
    }
    target_value = 70 # Target 70% CPU utilization
    scale_in_cooldown  = 300 # 5 minutes
    scale_out_cooldown = 60  # 1 minute
  }
}

resource "aws_appautoscaling_policy" "ecs_memory_scaling" {
  name               = "${var.project_name}-${var.environment}-memory-scaling-policy"
  policy_type        = "TargetTrackingScaling"
  resource_id        = aws_appautoscaling_target.ecs_target.resource_id
  scalable_dimension = aws_appautoscaling_target.ecs_target.scalable_dimension
  service_namespace  = aws_appautoscaling_target.ecs_target.service_namespace

  target_tracking_scaling_policy_configuration {
    predefined_metric_specification {
      predefined_metric_type = "ECSServiceAverageMemoryUtilization"
    }
    target_value = 70 # Target 70% Memory utilization
    scale_in_cooldown  = 300 # 5 minutes
    scale_out_cooldown = 60  # 1 minute
  }
}
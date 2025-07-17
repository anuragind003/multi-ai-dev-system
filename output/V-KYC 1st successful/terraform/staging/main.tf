# Configure the AWS Provider
provider "aws" {
  region = var.aws_region
}

# Variables for configuration
variable "aws_region" {
  description = "The AWS region to deploy to"
  type        = string
  default     = "us-east-1"
}

variable "instance_type" {
  description = "The EC2 instance type for the staging server"
  type        = string
  default     = "t3.medium" # Choose an appropriate instance type
}

variable "ami_id" {
  description = "The AMI ID for the EC2 instance (Ubuntu 22.04 LTS HVM EBS-backed)"
  type        = string
  # Find latest Ubuntu 22.04 LTS AMI for your region:
  # aws ec2 describe-images --owners 099720109477 --filters "Name=name,Values=ubuntu/images/hvm-ssd/ubuntu-jammy-22.04-amd64-server-*" "Name=state,Values=available" --query "sort_by(Images, &CreationDate)[-1].ImageId" --output text
  default     = "ami-053b04d416776735e" # Example for us-east-1, update as needed
}

variable "key_name" {
  description = "The name of the EC2 Key Pair to allow SSH access"
  type        = string
  default     = "your-ssh-key" # IMPORTANT: Change this to your actual SSH key pair name
}

variable "image_tag" {
  description = "The Docker image tag to deploy (e.g., git SHA)"
  type        = string
}

variable "ecr_repository" {
  description = "The full ECR repository URL (e.g., 123456789012.dkr.ecr.us-east-1.amazonaws.com/fastapi-operational-demo)"
  type        = string
}

# --- Networking ---

resource "aws_vpc" "main" {
  cidr_block = "10.0.0.0/16"
  tags = {
    Name = "fastapi-staging-vpc"
  }
}

resource "aws_subnet" "public" {
  vpc_id                  = aws_vpc.main.id
  cidr_block              = "10.0.1.0/24"
  map_public_ip_on_launch = true
  availability_zone       = "${var.aws_region}a"
  tags = {
    Name = "fastapi-staging-public-subnet"
  }
}

resource "aws_internet_gateway" "gw" {
  vpc_id = aws_vpc.main.id
  tags = {
    Name = "fastapi-staging-igw"
  }
}

resource "aws_route_table" "public" {
  vpc_id = aws_vpc.main.id
  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.gw.id
  }
  tags = {
    Name = "fastapi-staging-public-rt"
  }
}

resource "aws_route_table_association" "public" {
  subnet_id      = aws_subnet.public.id
  route_table_id = aws_route_table.public.id
}

# --- Security Group ---

resource "aws_security_group" "app_sg" {
  vpc_id      = aws_vpc.main.id
  name        = "fastapi-staging-sg"
  description = "Allow HTTP, HTTPS, SSH, and app ports"

  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"] # WARNING: Restrict this to your IP for production
    description = "Allow SSH access"
  }

  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"] # WARNING: Restrict this for production
    description = "Allow HTTP access (for health checks or direct access)"
  }

  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"] # WARNING: Restrict this for production
    description = "Allow HTTPS access"
  }

  ingress {
    from_port   = 8000 # FastAPI app port
    to_port     = 8000
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"] # WARNING: Restrict this for production
    description = "Allow FastAPI app port"
  }

  ingress {
    from_port   = 9090 # Prometheus UI
    to_port     = 9090
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"] # WARNING: Restrict this for production
    description = "Allow Prometheus UI"
  }

  ingress {
    from_port   = 3000 # Grafana UI
    to_port     = 3000
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"] # WARNING: Restrict this for production
    description = "Allow Grafana UI"
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
    description = "Allow all outbound traffic"
  }

  tags = {
    Name = "fastapi-staging-app-sg"
  }
}

# --- EC2 Instance ---

resource "aws_instance" "app_server" {
  ami                    = var.ami_id
  instance_type          = var.instance_type
  subnet_id              = aws_subnet.public.id
  vpc_security_group_ids = [aws_security_group.app_sg.id]
  key_name               = var.key_name
  associate_public_ip_address = true

  # User data to install Docker, Docker Compose, and run the application
  user_data = <<-EOF
              #!/bin/bash
              sudo apt-get update -y
              sudo apt-get install -y apt-transport-https ca-certificates curl software-properties-common
              curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg
              echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
              sudo apt-get update -y
              sudo apt-get install -y docker-ce docker-ce-cli containerd.io
              sudo usermod -aG docker ubuntu # Add ubuntu user to docker group
              sudo curl -L "https://github.com/docker/compose/releases/download/v2.23.3/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
              sudo chmod +x /usr/local/bin/docker-compose

              # Create app directory and copy docker-compose.prod.yml and .env.prod
              mkdir -p /home/ubuntu/app
              cd /home/ubuntu/app

              # Create .env.prod file with sensitive variables
              cat << EOT > .env.prod
              APP_SECRET_KEY="${var.image_tag}-staging-secret" # Use image tag as part of secret for demo
              LOG_LEVEL="INFO"
              POSTGRES_USER="prod_user"
              POSTGRES_PASSWORD="prod_password_secure_me"
              POSTGRES_DB="prod_fastapidb"
              POSTGRES_HOST="db"
              POSTGRES_PORT="5432"
              DATABASE_URL="postgresql://prod_user:prod_password_secure_me@db:5432/prod_fastapidb"
              GF_SECURITY_ADMIN_USER="admin"
              GF_SECURITY_ADMIN_PASSWORD="secure_grafana_admin_password"
              GF_SERVER_ROOT_URL="http://${self.public_ip}:3000"
              EOT

              # Create prometheus.yml
              cat << EOT > prometheus.yml
              global:
                scrape_interval: 15s
                evaluation_interval: 15s
              scrape_configs:
                - job_name: 'prometheus'
                  static_configs:
                    - targets: ['localhost:9090']
                - job_name: 'fastapi_app'
                  metrics_path: '/metrics'
                  static_configs:
                    - targets: ['app:8000']
                  relabel_configs:
                    - source_labels: [__address__]
                      regex: '(.+):8000'
                      target_label: instance
                      replacement: '$1'
                - job_name: 'node_exporter'
                  static_configs:
                    - targets: ['node_exporter:9100']
              EOT

              # Create grafana provisioning directories and files
              mkdir -p grafana/provisioning/datasources
              mkdir -p grafana/provisioning/dashboards
              mkdir -p grafana/dashboards

              cat << EOT > grafana/provisioning/datasources/datasource.yml
              apiVersion: 1
              datasources:
                - name: Prometheus
                  type: prometheus
                  uid: prometheus
                  access: proxy
                  url: http://prometheus:9090
                  isDefault: true
                  version: 1
                  editable: true
              EOT

              cat << EOT > grafana/provisioning/dashboards/dashboard.yml
              apiVersion: 1
              providers:
                - name: 'FastAPI Dashboards'
                  orgId: 1
                  folder: ''
                  type: file
                  disableDeletion: false
                  editable: true
                  options:
                    path: /var/lib/grafana/dashboards
              EOT

              # Copy the example dashboard JSON (simplified for user data)
              # In a real scenario, you'd fetch this from S3 or a config management tool
              cat << EOT > grafana/dashboards/fastapi_dashboard.json
              {
                "annotations": {"list": [{"builtIn": 1,"datasource": {"type": "datasource","uid": "grafana"},"enable": true,"hide": true,"iconColor": "rgba(0, 211, 255, 1)","name": "Annotations & Alerts","type": "dashboard"}]},
                "editable": true, "graphTooltip": 0, "id": 1, "links": [], "liveNow": false,
                "panels": [
                  {"datasource": {"type": "prometheus","uid": "prometheus"},"fieldConfig": {"defaults": {"color": {"mode": "palette-classic"},"custom": {"axisCenteredZero": false,"axisColorMode": "text","axisLabel": "","axisPlacement": "auto","barAlignment": 0,"drawStyle": "line","fillOpacity": 0,"gradientMode": "none","hideFrom": {"legend": false,"tooltip": false,"viz": false},"lineInterpolation": "linear","lineStyle": {"fill": "solid"},"lineWidth": 1,"pointSize": 5,"scaleDistribution": {"type": "linear"},"showPoints": "auto","spanNulls": false,"stacking": {"group": "A","mode": "none"},"thresholdsStyle": {"mode": "off"}},"mappings": [],"thresholds": {"mode": "absolute","steps": [{"color": "green","value": null},{"color": "red","value": 80}]},"unit": "short"}},"gridPos": {"h": 8,"w": 12,"x": 0,"y": 0},"id": 2,"options": {"legend": {"calcs": [],"displayMode": "list","placement": "bottom","showLegend": true},"tooltip": {"mode": "single","sort": "none"}},"targets": [{"datasource": {"type": "prometheus","uid": "prometheus"},"editorMode": "builder","expr": "sum(rate(http_requests_total{job=\"fastapi_app\"}[5m])) by (method, path)","legendFormat": "{{method}} {{path}}","range": true,"refId": "A"}],"title": "HTTP Request Rate (per second)","type": "timeseries"},
                  {"datasource": {"type": "prometheus","uid": "prometheus"},"fieldConfig": {"defaults": {"color": {"mode": "palette-classic"},"custom": {"axisCenteredZero": false,"axisColorMode": "text","axisLabel": "","axisPlacement": "auto","barAlignment": 0,"drawStyle": "line","fillOpacity": 0,"gradientMode": "none","hideFrom": {"legend": false,"tooltip": false,"viz": false},"lineInterpolation": "linear","lineStyle": {"fill": "solid"},"lineWidth": 1,"pointSize": 5,"scaleDistribution": {"type": "linear"},"showPoints": "auto","spanNulls": false,"stacking": {"group": "A","mode": "none"},"thresholdsStyle": {"mode": "off"}},"mappings": [],"thresholds": {"mode": "absolute","steps": [{"color": "green","value": null},{"color": "red","value": 80}]},"unit": "s"}},"gridPos": {"h": 8,"w": 12,"x": 12,"y": 0},"id": 4,"options": {"legend": {"calcs": [],"displayMode": "list","placement": "bottom","showLegend": true},"tooltip": {"mode": "single","sort": "none"}},"targets": [{"datasource": {"type": "prometheus","uid": "prometheus"},"editorMode": "builder","expr": "histogram_quantile(0.99, sum(rate(http_request_duration_seconds_bucket{job=\"fastapi_app\"}[5m])) by (le, method, path))","legendFormat": "{{method}} {{path}} 99th Percentile Latency","range": true,"refId": "A"},{"datasource": {"type": "prometheus","uid": "prometheus"},"editorMode": "builder","expr": "histogram_quantile(0.50, sum(rate(http_request_duration_seconds_bucket{job=\"fastapi_app\"}[5m])) by (le, method, path))","legendFormat": "{{method}} {{path}} 50th Percentile Latency","range": true,"refId": "B"}],"title": "HTTP Request Latency (P50, P99)","type": "timeseries"},
                  {"datasource": {"type": "prometheus","uid": "prometheus"},"fieldConfig": {"defaults": {"color": {"mode": "palette-classic"},"custom": {"axisCenteredZero": false,"axisColorMode": "text","axisLabel": "","axisPlacement": "auto","barAlignment": 0,"drawStyle": "line","fillOpacity": 0,"gradientMode": "none","hideFrom": {"legend": false,"tooltip": false,"viz": false},"lineInterpolation": "linear","lineStyle": {"fill": "solid"},"lineWidth": 1,"pointSize": 5,"scaleDistribution": {"type": "linear"},"showPoints": "auto","spanNulls": false,"stacking": {"group": "A","mode": "none"},"thresholdsStyle": {"mode": "off"}},"mappings": [],"thresholds": {"mode": "absolute","steps": [{"color": "green","value": null},{"color": "red","value": 80}]},"unit": "percent"}},"gridPos": {"h": 8,"w": 12,"x": 0,"y": 8},"id": 6,"options": {"legend": {"calcs": [],"displayMode": "list","placement": "bottom","showLegend": true},"tooltip": {"mode": "single","sort": "none"}},"targets": [{"datasource": {"type": "prometheus","uid": "prometheus"},"editorMode": "builder","expr": "sum(rate(http_requests_total{job=\"fastapi_app\", code=~\"5..\"}[5m])) by (path) / sum(rate(http_requests_total{job=\"fastapi_app\"}[5m])) by (path) * 100","legendFormat": "{{path}} Error Rate","range": true,"refId": "A"}],"title": "HTTP Error Rate (5xx)","type": "timeseries"},
                  {"datasource": {"type": "prometheus","uid": "prometheus"},"fieldConfig": {"defaults": {"color": {"mode": "palette-classic"},"custom": {"axisCenteredZero": false,"axisColorMode": "text","axisLabel": "","axisPlacement": "auto","barAlignment": 0,"drawStyle": "line","fillOpacity": 0,"gradientMode": "none","hideFrom": {"legend": false,"tooltip": false,"viz": false},"lineInterpolation": "linear","lineStyle": {"fill": "solid"},"lineWidth": 1,"pointSize": 5,"scaleDistribution": {"type": "linear"},"showPoints": "auto","spanNulls": false,"stacking": {"group": "A","mode": "none"},"thresholdsStyle": {"mode": "off"}},"mappings": [],"thresholds": {"mode": "absolute","steps": [{"color": "green","value": null},{"color": "red","value": 80}]},"unit": "bytes"}},"gridPos": {"h": 8,"w": 12,"x": 12,"y": 8},"id": 8,"options": {"legend": {"calcs": [],"displayMode": "list","placement": "bottom","showLegend": true},"tooltip": {"mode": "single","sort": "none"}},"targets": [{"datasource": {"type": "prometheus","uid": "prometheus"},"editorMode": "builder","expr": "sum(container_memory_usage_bytes{image=~\"fastapi-operational-demo.*\"}) by (name)","legendFormat": "{{name}} Memory Usage","range": true,"refId": "A"},{"datasource": {"type": "prometheus","uid": "prometheus"},"editorMode": "builder","expr": "sum(rate(container_cpu_usage_seconds_total{image=~\"fastapi-operational-demo.*\"}[5m])) by (name)","legendFormat": "{{name}} CPU Usage","range": true,"refId": "B"}],"title": "Application Container Resources (Memory/CPU)","type": "timeseries"}
                ],
                "refresh": "5s", "schemaVersion": 38, "style": "dark", "tags": ["fastapi","application","demo"],
                "templating": {"list": []}, "time": {"from": "now-1h","to": "now"},
                "timepicker": {"refresh_intervals": ["5s","10s","30s","1m","5m","15m","30m","1h","2h","1d"],"time_options": ["5m","15m","1h","6h","12h","24h","2d","7d","30d"]},
                "timezone": "", "title": "FastAPI Application Overview", "uid": "fastapi-app-overview", "version": 1, "weekStart": ""
              }
              EOT

              # Create docker-compose.prod.yml
              cat << EOT > docker-compose.prod.yml
              version: '3.8'
              services:
                app:
                  image: ${var.ecr_repository}:${var.image_tag}
                  ports:
                    - "8000:8000"
                  env_file:
                    - .env.prod
                  depends_on:
                    db:
                      condition: service_healthy
                  restart: always
                  healthcheck:
                    test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
                    interval: 30s
                    timeout: 10s
                    retries: 3
                    start_period: 10s

                db:
                  image: postgres:15-alpine
                  env_file:
                    - .env.prod
                  volumes:
                    - db_data:/var/lib/postgresql/data
                  restart: always
                  healthcheck:
                    test: ["CMD-SHELL", "pg_isready -U \$\$POSTGRES_USER -d \$\$POSTGRES_DB"]
                    interval: 10s
                    timeout: 5s
                    retries: 5

                prometheus:
                  image: prom/prometheus:v2.48.0
                  container_name: prometheus
                  ports:
                    - "9090:9090"
                  volumes:
                    - ./prometheus.yml:/etc/prometheus/prometheus.yml
                    - prometheus_data:/prometheus
                  command:
                    - '--config.file=/etc/prometheus/prometheus.yml'
                    - '--storage.tsdb.path=/prometheus'
                    - '--web.enable-lifecycle'
                  restart: always
                  depends_on:
                    - app
                    - node_exporter

                grafana:
                  image: grafana/grafana:10.2.2
                  container_name: grafana
                  ports:
                    - "3000:3000"
                  volumes:
                    - grafana_data:/var/lib/grafana
                    - ./grafana/provisioning/datasources:/etc/grafana/provisioning/datasources
                    - ./grafana/provisioning/dashboards:/etc/grafana/provisioning/dashboards
                    - ./grafana/dashboards:/var/lib/grafana/dashboards
                  env_file:
                    - .env.prod
                  restart: always
                  depends_on:
                    - prometheus

                node_exporter:
                  image: prom/node-exporter:v1.7.0
                  container_name: node_exporter
                  ports:
                    - "9100:9100"
                  command:
                    - '--path.rootfs=/host'
                  volumes:
                    - /:/host:ro,rslave
                  restart: always

              volumes:
                db_data:
                prometheus_data:
                grafana_data:
              EOT

              # Login to ECR and pull the image
              aws ecr get-login-password --region ${var.aws_region} | docker login --username AWS --password-stdin ${var.ecr_repository}
              docker pull ${var.ecr_repository}:${var.image_tag}

              # Run Docker Compose
              docker-compose -f docker-compose.prod.yml up -d
              EOF

  tags = {
    Name        = "fastapi-staging-server"
    Environment = "Staging"
    Project     = "FastAPIOperationalDemo"
  }
}

# --- Outputs ---

output "public_ip" {
  description = "The public IP address of the staging server"
  value       = aws_instance.app_server.public_ip
}

output "app_url" {
  description = "The URL of the FastAPI application on staging"
  value       = "http://${aws_instance.app_server.public_ip}:8000"
}

output "prometheus_url" {
  description = "The URL of the Prometheus UI on staging"
  value       = "http://${aws_instance.app_server.public_ip}:9090"
}

output "grafana_url" {
  description = "The URL of the Grafana UI on staging"
  value       = "http://${aws_instance.app_server.public_ip}:3000"
}
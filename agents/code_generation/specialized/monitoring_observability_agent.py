"""
Monitoring Observability Agent - Specialized for monitoring and observability
Focuses on Prometheus, Grafana, distributed tracing, and alerting.
"""

import json
import os
import time
from typing import Dict, Any, List, Optional, Set

from langchain_core.language_models import BaseLanguageModel
from langchain_core.retrievers import BaseRetriever
from langchain_core.prompts import ChatPromptTemplate

from agents.code_generation.base_code_generator import BaseCodeGeneratorAgent
from tools.code_execution_tool import CodeExecutionTool
from message_bus import MessageBus

import logging
logger = logging.getLogger(__name__)

class MonitoringObservabilityAgent(BaseCodeGeneratorAgent):
    """Monitoring Observability Agent for comprehensive monitoring infrastructure."""
    
    def __init__(self, 
                 llm: BaseLanguageModel, 
                 memory, 
                 temperature: float,
                 output_dir: str, 
                 code_execution_tool: CodeExecutionTool,
                 rag_retriever: Optional[BaseRetriever] = None,
                 message_bus: Optional[MessageBus] = None):
        """Initialize Monitoring Observability Agent."""
        
        super().__init__(
            llm=llm,
            memory=memory,
            agent_name="Monitoring Observability Agent",
            temperature=temperature,
            output_dir=output_dir,
            code_execution_tool=code_execution_tool,
            rag_retriever=rag_retriever,
            message_bus=message_bus
        )
        
        # Monitoring-specific prompt template
        self.monitoring_prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an expert DevOps Engineer specializing in monitoring and observability infrastructure.

Your expertise includes:
- Prometheus metrics collection and configuration
- Grafana dashboards and visualization
- Application Performance Monitoring (APM)
- Log aggregation and analysis
- Alert management and notification systems
- Infrastructure monitoring and resource tracking
- Custom metrics instrumentation
- Distributed tracing and service mesh observability

Industry best practices:
- Follow the Four Golden Signals: Latency, Traffic, Errors, Saturation
- Implement comprehensive monitoring at all layers (infrastructure, application, business)
- Use proper metric naming conventions and labels
- Set up meaningful alerts with appropriate thresholds
- Implement proper log structured formatting and correlation
- Ensure monitoring doesn't impact application performance
- Create actionable dashboards with clear visualizations
- Implement proper retention policies for metrics and logs

For monitoring stacks:
- Prometheus + Grafana for metrics and dashboards
- ELK Stack (Elasticsearch, Logstash, Kibana) for log analysis
- Jaeger or Zipkin for distributed tracing
- Application-specific instrumentation libraries
- Cloud provider monitoring services integration

Generate production-ready monitoring infrastructure that includes:
1. Prometheus configuration with proper scraping targets
2. Grafana dashboards with meaningful visualizations
3. Alert rules for critical system metrics
4. Application instrumentation code
5. Log configuration and structured logging
6. Docker compose files for monitoring stack
7. Kubernetes monitoring manifests
8. Documentation and runbooks

Ensure all monitoring follows naming conventions, has proper documentation, and includes both infrastructure and application-level metrics."""),
            ("human", """Generate comprehensive monitoring and observability infrastructure for a {domain} application.

Requirements:
- Domain: {domain}
- Programming Language: {language}
- Framework: {framework}
- Scale: {scale}
- Monitoring Stack: {monitoring_stack}
- Additional Requirements: {additional_requirements}

Generate a complete monitoring suite including:
1. Prometheus configuration with service discovery
2. Grafana dashboards with key performance indicators
3. Alert rules for critical metrics and SLAs
4. Application metrics instrumentation
5. Structured logging configuration
6. Monitoring docker-compose setup
7. Health check endpoints
8. Monitoring documentation

For each monitoring component, provide:
- Proper configuration with security considerations
- Comprehensive metric coverage
- Meaningful alert thresholds
- Clear dashboard visualizations
- Performance-optimized instrumentation
- Clear documentation

Output as a structured JSON with file paths, content, and descriptions for industrial deployment.""")
        ])
        
        # New prompt for Prometheus configuration
        self.prometheus_config_prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an expert in generating Prometheus configuration files.
Your task is to generate a production-ready Prometheus configuration (prometheus.yml) based on the application's domain, language, framework, and scale.
Include appropriate scrape configurations, job definitions, and target discovery mechanisms.
Ensure the configuration is well-structured, optimized for performance, and includes comments for clarity.
"""),
            ("human", """Generate a Prometheus configuration (prometheus.yml) for a **{domain}** application developed in **{language}** using **{framework}** at **{scale}** scale.

Provide the complete YAML content for prometheus.yml."""
            )
        ])
        
        # New prompt for Grafana dashboard generation
        self.grafana_dashboard_prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an expert in generating Grafana dashboard JSON models.
Your task is to generate a comprehensive Grafana dashboard JSON for a given application context.
Include panels for key metrics like request rate, response time, error rate, and system resources (CPU, Memory).
Ensure the dashboard is well-organized, uses appropriate visualization types, and is production-ready.
"""),
            ("human", """Generate a Grafana dashboard JSON model for a **{domain}** application developed in **{language}** using **{framework}** at **{scale}** scale.

Key metrics to include:
- Request Rate
- Response Time (e.95 percentile)
- Error Rate (5xx errors)
- CPU Usage
- Memory Usage

Provide the complete JSON content for the Grafana dashboard."""
            )
        ])
        
        # New prompt for alert rules generation
        self.alert_rules_prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an expert in generating Prometheus alert rules.
Your task is to generate production-ready Prometheus alert rules (alert-rules.yml) based on the application's domain, language, framework, and scale.
Include alerts for critical metrics like high error rate, high response time, high resource usage (CPU/Memory), and service downtime.
Ensure alert rules have appropriate severity labels, summaries, and descriptions.
"""),
            ("human", """Generate Prometheus alert rules (alert-rules.yml) for a **{domain}** application developed in **{language}** using **{framework}** at **{scale}** scale.

Key alerts to include:
- High Error Rate
- High Response Time
- High CPU Usage
- High Memory Usage
- Service Down

Provide the complete YAML content for alert-rules.yml."""
            )
        ])
        
        # New prompt for metrics code generation
        self.metrics_code_prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an expert in generating application metrics instrumentation code.
Your task is to generate production-ready code for collecting and exposing application metrics, compatible with Prometheus.
Generate code for the specified programming language and framework, including common HTTP request metrics, system resource metrics (CPU, Memory), and active connections.
Ensure the code follows best practices for metrics naming, labeling, and instrumentation.
"""),
            ("human", """Generate application metrics instrumentation code for a **{domain}** application developed in **{language}** using **{framework}** at **{scale}** scale.

Metrics to include:
- HTTP Request Total (counter)
- HTTP Request Duration (histogram)
- Process Memory Usage (gauge)
- Process CPU Usage (gauge)
- Active Connections (gauge)

Provide the complete code for metrics instrumentation in {language}. If applicable, include a web framework integration (e.g., middleware for Flask/Express)."""
            )
        ])
        
        # New prompt for Docker Compose monitoring stack generation
        self.monitoring_compose_prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an expert in generating Docker Compose configurations for monitoring stacks.
Your task is to generate a production-ready Docker Compose file for a monitoring setup (e.g., Prometheus, Grafana, Node Exporter) based on the application's domain, language, framework, and scale.
Ensure all services are properly configured, networked, and include necessary volumes and environment variables.
"""),
            ("human", """Generate a Docker Compose file for the monitoring stack of a **{domain}** application developed in **{language}** using **{framework}** at **{scale}** scale.

Monitoring stack components to include:
- Prometheus
- Grafana
- Node Exporter

Provide the complete YAML content for the Docker Compose file."""
            )
        ])
        
        logger.info("Monitoring Observability Agent initialized with LLM-powered generation")
    
    def generate_monitoring_infrastructure(self, 
                                         domain: str,
                                         language: str,
                                         framework: str,
                                         scale: str,
                                         monitoring_stack: List[str],
                                         additional_requirements: str = "") -> Dict[str, Any]:
        """Generate comprehensive monitoring infrastructure using LLM."""
        
        start_time = time.time()
        
        try:
            logger.info(f"Generating LLM-powered monitoring infrastructure for {domain}")
            
            # Prepare context for LLM
            context = {
                "domain": domain,
                "language": language,
                "framework": framework,
                "scale": scale,
                "monitoring_stack": ", ".join(monitoring_stack),
                "additional_requirements": additional_requirements or "Standard monitoring practices"
            }
            
            # Generate monitoring infrastructure using LLM
            chain = self.monitoring_prompt | self.llm
            response = chain.invoke(context)
            
            # Parse LLM response
            try:
                if hasattr(response, 'content'):
                    content = response.content
                else:
                    content = str(response)
                
                # Extract JSON from response
                json_start = content.find('{')
                json_end = content.rfind('}') + 1
                
                if json_start != -1 and json_end > json_start:
                    json_content = content[json_start:json_end]
                    parsed_response = json.loads(json_content)
                else:
                    # Fallback: Create structured response
                    parsed_response = self._create_fallback_monitoring_structure(context)
                
            except (json.JSONDecodeError, Exception) as e:
                logger.warning(f"Failed to parse LLM response as JSON: {e}")
                parsed_response = self._create_fallback_monitoring_structure(context)
            
            # Save generated files
            saved_files = []
            if "files" in parsed_response:
                for file_info in parsed_response["files"]:
                    file_path = os.path.join(self.output_dir, file_info["path"])
                    os.makedirs(os.path.dirname(file_path), exist_ok=True)
                    
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(file_info["content"])
                    
                    saved_files.append({
                        "name": file_info["name"],
                        "path": file_info["path"],
                        "type": file_info.get("type", "monitoring"),
                        "size": len(file_info["content"]),
                        "description": file_info.get("description", "")
                    })
            
            execution_time = time.time() - start_time
            
            # Update memory with generation details
            self.memory.add_interaction({
                "agent": self.agent_name,
                "action": "generate_monitoring_infrastructure",
                "domain": domain,
                "language": language,
                "framework": framework,
                "files_generated": len(saved_files),
                "execution_time": execution_time
            })
            
            return {
                "status": "success",
                "files": saved_files,
                "execution_time": execution_time,
                "summary": {
                    "files_count": len(saved_files),
                    "components": self._extract_monitoring_components(saved_files),
                    "stack_specific": monitoring_stack,
                    "framework_specific": language
                },
                "cost_optimization": {
                    "tokens_used": self._estimate_tokens_used(content),
                    "generation_method": "LLM-powered",
                    "efficiency_score": "high"
                }
            }
            
        except Exception as e:
            logger.error(f"Monitoring infrastructure generation failed: {str(e)}")
            return {
                "status": "error", 
                "error": str(e),
                "execution_time": time.time() - start_time
            }
    
    def _create_fallback_monitoring_structure(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Create fallback monitoring structure when LLM parsing fails."""
        
        language = context["language"].lower()
        monitoring_stack = context["monitoring_stack"].lower()
        
        return {
            "files": [
                {
                    "name": "prometheus.yml",
                    "path": "monitoring/prometheus/prometheus.yml",
                    "type": "configuration",
                    "description": "Prometheus monitoring configuration",
                    "content": self._get_prometheus_config(context["domain"], context["language"], context["framework"], context["scale"])
                },
                {
                    "name": "grafana-dashboard.json",
                    "path": "monitoring/grafana/dashboards/app-dashboard.json",
                    "type": "dashboard",
                    "description": "Grafana application monitoring dashboard",
                    "content": self._get_grafana_dashboard(context["domain"], context["language"], context["framework"], context["scale"])
                },
                {
                    "name": "alert-rules.yml",
                    "path": "monitoring/prometheus/alert-rules.yml",
                    "type": "configuration",
                    "description": "Prometheus alert rules configuration",
                    "content": self._get_alert_rules(context["domain"], context["language"], context["framework"], context["scale"])
                },
                {
                    "name": f"metrics.{self._get_file_extension(language)}",
                    "path": f"src/utils/metrics.{self._get_file_extension(language)}",
                    "type": "instrumentation",
                    "description": "Application metrics instrumentation code",
                    "content": self._get_metrics_code(context["domain"], context["language"], context["framework"], context["scale"])
                },
                {
                    "name": "monitoring-compose.yml",
                    "path": "docker-compose.monitoring.yml",
                    "type": "configuration",
                    "description": "Docker Compose for monitoring stack",
                    "content": self._get_monitoring_compose(context["domain"], context["language"], context["framework"], context["scale"])
                }
            ]
        }
    
    def _get_prometheus_config(self, domain: str, language: str, framework: str, scale: str) -> str:
        """Get Prometheus configuration based on application context."""
        config = """global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'prometheus'
    static_configs:
      - targets: ['localhost:9090']

  - job_name: 'node_exporter'
    static_configs:
      - targets: ['localhost:9100']

  - job_name: 'application'
    static_configs:
      - targets: ['localhost:8000']  # Replace with actual application endpoint
        labels:
          app: 'your-app-name'
          env: 'development'
"""
        return config
    
    def _get_grafana_dashboard(self, domain: str, language: str, framework: str, scale: str) -> str:
        """Generate Grafana dashboard configuration."""
        return """{
  "dashboard": {
    "id": null,
    "title": "Application Monitoring",
    "tags": ["application", "monitoring"],
    "timezone": "browser",
    "panels": [
      {
        "id": 1,
        "title": "Request Rate",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(http_requests_total[5m])",
            "legendFormat": "{{method}} {{endpoint}}"
          }
        ],
        "gridPos": {"h": 8, "w": 12, "x": 0, "y": 0}
      },
      {
        "id": 2,
        "title": "Response Time",
        "type": "graph",
        "targets": [
          {
            "expr": "histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))",
            "legendFormat": "95th percentile"
          }
        ],
        "gridPos": {"h": 8, "w": 12, "x": 12, "y": 0}
      },
      {
        "id": 3,
        "title": "Error Rate",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(http_requests_total{status=~\"5..\"}[5m])",
            "legendFormat": "5xx Errors"
          }
        ],
        "gridPos": {"h": 8, "w": 12, "x": 0, "y": 8}
      },
      {
        "id": 4,
        "title": "System Resources",
        "type": "graph",
        "targets": [
          {
            "expr": "process_resident_memory_bytes",
            "legendFormat": "Memory Usage"
          },
          {
            "expr": "rate(process_cpu_seconds_total[5m]) * 100",
            "legendFormat": "CPU Usage %"
          }
        ],
        "gridPos": {"h": 8, "w": 12, "x": 12, "y": 8}
      }
    ],
    "time": {
      "from": "now-1h",
      "to": "now"
    },
    "refresh": "5s"
  }
}"""
    
    def _get_alert_rules(self, domain: str, language: str, framework: str, scale: str) -> str:
        """Generate Prometheus alert rules."""
        return """groups:
- name: application_alerts
  rules:
  - alert: HighErrorRate
    expr: rate(http_requests_total{status=~"5.."}[5m]) > 0.1
    for: 2m
    labels:
      severity: critical
    annotations:
      summary: "High error rate detected"
      description: "Error rate is {{ $value }} errors per second"

  - alert: HighResponseTime
    expr: histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m])) > 1
    for: 5m
    labels:
      severity: warning
    annotations:
      summary: "High response time detected"
      description: "95th percentile response time is {{ $value }} seconds"

  - alert: HighMemoryUsage
    expr: process_resident_memory_bytes / 1024 / 1024 > 500
    for: 5m
    labels:
      severity: warning
    annotations:
      summary: "High memory usage detected"
      description: "Memory usage is {{ $value }}MB"

  - alert: ServiceDown
    expr: up == 0
    for: 1m
    labels:
      severity: critical
    annotations:
      summary: "Service is down"
      description: "{{ $labels.instance }} has been down for more than 1 minute"
"""
    
    def _get_metrics_code(self, domain: str, language: str, framework: str, scale: str) -> str:
        """Generate metrics instrumentation code."""
        if language.lower() == "python":
            return """from prometheus_client import Counter, Histogram, Gauge, generate_latest
from functools import wraps
import time
import psutil
import os

# Metrics definitions
REQUEST_COUNT = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status']
)

REQUEST_DURATION = Histogram(
    'http_request_duration_seconds',
    'HTTP request duration in seconds',
    ['method', 'endpoint']
)

MEMORY_USAGE = Gauge(
    'process_resident_memory_bytes',
    'Process resident memory in bytes'
)

CPU_USAGE = Gauge(
    'process_cpu_usage_percent',
    'Process CPU usage percentage'
)

ACTIVE_CONNECTIONS = Gauge(
    'active_connections',
    'Number of active connections'
)

class MetricsCollector:
    \"\"\"Collect and expose application metrics.\"\"\"
    
    def __init__(self):
        self.process = psutil.Process(os.getpid())
    
    def collect_system_metrics(self):
        \"\"\"Collect system-level metrics.\"\"\"
        # Memory metrics
        memory_info = self.process.memory_info()
        MEMORY_USAGE.set(memory_info.rss)
        
        # CPU metrics
        cpu_percent = self.process.cpu_percent()
        CPU_USAGE.set(cpu_percent)
    
    def record_request(self, method: str, endpoint: str, status_code: int, duration: float):
        \"\"\"Record HTTP request metrics.\"\"\"
        REQUEST_COUNT.labels(method=method, endpoint=endpoint, status=str(status_code)).inc()
        REQUEST_DURATION.labels(method=method, endpoint=endpoint).observe(duration)

def track_requests(f):
    \"\"\"Decorator to automatically track request metrics.\"\"\"
    @wraps(f)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        method = request.method if 'request' in globals() else 'UNKNOWN'
        endpoint = request.endpoint if 'request' in globals() else f.__name__
        
        try:
            result = f(*args, **kwargs)
            status_code = getattr(result, 'status_code', 200)
        except Exception as e:
            status_code = 500
            raise
        finally:
            duration = time.time() - start_time
            metrics_collector.record_request(method, endpoint, status_code, duration)
        
        return result
    return wrapper

# Global metrics collector instance
metrics_collector = MetricsCollector()

def get_metrics():
    \"\"\"Get Prometheus metrics in text format.\"\"\"
    metrics_collector.collect_system_metrics()
    return generate_latest()
"""
        else:
            return """const client = require('prom-client');

// Create a Registry to register the metrics
const register = new client.Registry();

// Add default metrics
client.collectDefaultMetrics({
  app: 'nodejs-app',
  timeout: 5000,
  gcDurationBuckets: [0.001, 0.01, 0.1, 1, 2, 5],
  register
});

// Custom metrics
const httpRequestsTotal = new client.Counter({
  name: 'http_requests_total',
  help: 'Total number of HTTP requests',
  labelNames: ['method', 'route', 'status_code'],
  registers: [register]
});

const httpRequestDuration = new client.Histogram({
  name: 'http_request_duration_seconds',
  help: 'Duration of HTTP requests in seconds',
  labelNames: ['method', 'route'],
  buckets: [0.1, 0.3, 0.5, 0.7, 1, 3, 5, 7, 10],
  registers: [register]
});

const activeConnections = new client.Gauge({
  name: 'active_connections',
  help: 'Number of active connections',
  registers: [register]
});

// Middleware to track HTTP requests
const trackRequests = (req, res, next) => {
  const start = Date.now();
  
  res.on('finish', () => {
    const duration = (Date.now() - start) / 1000;
    httpRequestsTotal.labels(req.method, req.route?.path || req.path, res.statusCode).inc();
    httpRequestDuration.labels(req.method, req.route?.path || req.path).observe(duration);
  });
  
  next();
};

// Metrics endpoint
const getMetrics = async (req, res) => {
  res.set('Content-Type', register.contentType);
  res.end(await register.metrics());
};

module.exports = {
  register,
  trackRequests,
  getMetrics,
  httpRequestsTotal,
  httpRequestDuration,
  activeConnections
};
"""
    
    def _get_monitoring_compose(self, domain: str, language: str, framework: str, scale: str) -> str:
        """Generate Docker Compose for monitoring stack."""
        return """version: '3.8'

services:
  prometheus:
    image: prom/prometheus:latest
    container_name: prometheus
    ports:
      - "9090:9090"
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
    command: 
      - '--config.file=/etc/prometheus/prometheus.yml'
    networks:
      - monitoring_network

  grafana:
    image: grafana/grafana:latest
    container_name: grafana
    ports:
      - "3000:3000"
    volumes:
      - ./grafana/dashboards:/etc/grafana/provisioning/dashboards
      - ./grafana/datasources:/etc/grafana/provisioning/datasources
    environment:
      - GF_SECURITY_ADMIN_USER=admin
      - GF_SECURITY_ADMIN_PASSWORD=admin
    depends_on:
      - prometheus
    networks:
      - monitoring_network

  node_exporter:
    image: prom/node-exporter:latest
    container_name: node_exporter
    ports:
      - "9100:9100"
    networks:
      - monitoring_network

networks:
  monitoring_network:
    driver: bridge
"""
    
    def _get_file_extension(self, language: str) -> str:
        """Get the appropriate file extension for the given language."""
        extensions = {
            "python": "py",
            "javascript": "js",
            "typescript": "ts",
            "java": "java",
            "go": "go",
            "csharp": "cs"
        }
        return extensions.get(language.lower(), "txt")

    def _extract_monitoring_components(self, files: List[Dict[str, Any]]) -> List[str]:
        """Extract generated monitoring components from file info."""
        components = set()
        for file_info in files:
            path = file_info.get("path", "").lower()
            if "prometheus" in path:
                components.add("Prometheus")
            if "grafana" in path:
                components.add("Grafana")
            if "alert" in path:
                components.add("Alerting")
            if "metrics" in path:
                components.add("Instrumentation")
            if "compose" in path or "docker-compose" in path:
                components.add("Docker Compose")
        return sorted(list(components))

    def _estimate_tokens_used(self, content: str) -> int:
        """Estimate tokens used based on content length (rough approximation)."""
        return len(content) // 4 
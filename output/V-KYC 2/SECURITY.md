# Security Best Practices for FastAPI Monolithic Application

This document outlines the security measures and best practices implemented and recommended for the FastAPI monolithic application.

## 1. Secrets Management
*   **Development:** For local development, sensitive information (e.g., database credentials, API keys) is stored in a `.env` file, which is excluded from version control (`.gitignore`).
*   **CI/CD:** In GitLab CI/CD, all sensitive variables (AWS credentials, SSH keys, application secrets) are stored as **CI/CD Variables** with `Protected` and `Masked` flags enabled.
*   **Production:** For production deployments, it is highly recommended to use a dedicated secrets management service like:
    *   **AWS Secrets Manager:** For storing and retrieving database credentials, API keys, etc.
    *   **HashiCorp Vault:** For more advanced secrets management across multiple environments.
    *   **Environment Variables:** While used, ensure they are injected securely (e.g., via Docker secrets, Kubernetes secrets, or directly from a secrets manager). Avoid hardcoding secrets.

## 2. Vulnerability Scanning
*   **Docker Image Scanning (Trivy):** The CI/CD pipeline includes a `security_scan_image` job that uses [Trivy](https://aquasec.com/products/trivy/) to scan the built Docker image for known vulnerabilities in OS packages and application dependencies.
    *   **Action:** Review scan reports and update base images or dependencies to address critical and high-severity vulnerabilities.
*   **Static Application Security Testing (SAST - Bandit):** The `security_scan_code` job uses [Bandit](https://bandit.readthedocs.io/en/latest/) to find common security issues in Python code.
    *   **Action:** Address findings from Bandit reports. Prioritize issues based on severity and context.

## 3. Network Security
*   **Security Groups (AWS EC2):** The Terraform configuration (`terraform/main.tf`) defines a security group that:
    *   Allows SSH access (port 22) from `0.0.0.0/0` (for convenience in this example). **In production, restrict SSH access to known IP ranges (e.g., your office VPN, bastion host).**
    *   Allows HTTP (port 80) and HTTPS (port 443) from `0.0.0.0/0`.
    *   Allows application port (8000) from `0.0.0.0/0`. **In production, restrict this to your Load Balancer's security group or specific trusted IPs.**
*   **HTTPS Enforcement:**
    *   It is critical to enforce HTTPS for all production traffic.
    *   If using an AWS Application Load Balancer (ALB), configure it to terminate SSL/TLS and forward traffic to the EC2 instance over HTTP.
    *   Alternatively, deploy a reverse proxy (e.g., Nginx, Caddy) on the EC2 instance to handle SSL/TLS termination and proxy requests to the FastAPI application.
*   **Firewall:** Ensure the EC2 instance's internal firewall (e.g., `ufw` on Ubuntu) is configured to only allow necessary inbound connections.

## 4. Application Security
*   **Input Validation:** FastAPI's Pydantic models automatically handle input validation, preventing common injection attacks (SQL injection, XSS) to a good extent. Always ensure proper validation for all incoming data.
*   **Error Handling:** Avoid exposing sensitive information in error messages (e.g., stack traces, database connection strings). Use generic error messages for public consumption.
*   **CORS:** Implement Cross-Origin Resource Sharing (CORS) policies to restrict which domains can access your API. FastAPI provides `CORSMiddleware`.
*   **Rate Limiting:** Implement rate limiting to prevent abuse and denial-of-service (DoS) attacks. This can be done at the application level (e.g., `fastapi-limiter`) or at the load balancer/API Gateway level.
*   **Authentication & Authorization:**
    *   Use robust authentication mechanisms (e.g., OAuth2, JWT).
    *   Implement role-based access control (RBAC) or attribute-based access control (ABAC) for fine-grained authorization.
*   **Dependency Management:** Regularly update application dependencies to patch known vulnerabilities. Use `pip-audit` or `safety` to check for vulnerable dependencies.
*   **HTTP Security Headers:** Configure your web server or FastAPI application to send security-enhancing HTTP headers (e.g., `X-Content-Type-Options`, `X-Frame-Options`, `Strict-Transport-Security`, `Content-Security-Policy`).

## 5. Least Privilege
*   **IAM Roles:** The EC2 instance is launched with an IAM role (`ec2_app_role`) that has minimal necessary permissions. Grant only the permissions required for the application to function (e.g., S3 access if needed, RDS connectivity). Avoid using root credentials.
*   **Non-Root User in Docker:** The `Dockerfile` creates and runs the application as a non-root user (`appuser`) to minimize the impact of a container breakout.
*   **File Permissions:** Ensure proper file permissions on the EC2 instance and within the Docker container to prevent unauthorized access to sensitive files.

## 6. Logging and Monitoring
*   **Security Logging:** Ensure application logs capture relevant security events (e.g., failed login attempts, access to sensitive resources).
*   **Alerting:** Configure alerts in your monitoring system (Prometheus/Grafana) for suspicious activities, high error rates, or security-related metrics.

## 7. Regular Audits and Updates
*   **Security Audits:** Conduct regular security audits and penetration testing.
*   **Software Updates:** Keep the operating system, Docker, and all application dependencies up-to-date to benefit from the latest security patches.
*   **GitLab Runner Security:** Ensure your GitLab Runners are secured, isolated, and updated. Use specific runners for sensitive jobs if necessary.

By following these guidelines, you can significantly enhance the security posture of your FastAPI application.
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
from starlette.types import ASGIApp, Receive, Scope, Send

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp):
        super().__init__(app)

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        self.add_security_headers(response)
        return response

    def add_security_headers(self, response: Response):
        # X-Content-Type-Options: Prevents browsers from MIME-sniffing a response away from the declared content-type.
        response.headers["X-Content-Type-Options"] = "nosniff"

        # X-Frame-Options: Prevents clickjacking attacks by forbidding embedding the page in an iframe.
        response.headers["X-Frame-Options"] = "DENY"

        # X-XSS-Protection: Enables the XSS filter in browsers.
        response.headers["X-XSS-Protection"] = "1; mode=block"

        # Strict-Transport-Security (HSTS): Enforces secure (HTTPS) connections to the server.
        # Max-age should be long (e.g., 1 year = 31536000 seconds) in production.
        # includeSubDomains is recommended if all subdomains are HTTPS.
        # preload is for submitting your domain to browser HSTS preload lists.
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains; preload"

        # Referrer-Policy: Controls how much referrer information is included with requests.
        response.headers["Referrer-Policy"] = "no-referrer-when-downgrade"

        # Content-Security-Policy (CSP): Mitigates XSS and other injection attacks.
        # This is a very strict example. Adjust 'default-src' and other directives
        # based on your application's needs (e.g., if you use external scripts, fonts, images).
        # 'self' allows resources from the same origin.
        # 'unsafe-inline' for styles/scripts is generally discouraged but sometimes necessary for quick setup.
        # Consider using nonces or hashes for inline scripts/styles in production.
        # Example: "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; font-src 'self';"
        # For Swagger UI/Redoc, you might need to relax 'script-src' and 'style-src' or use specific hashes/nonces.
        # For simplicity in this example, we'll use a slightly more permissive one that works with default FastAPI docs.
        response.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; img-src 'self' data:; font-src 'self' https://fonts.gstatic.com;"

        # Feature-Policy / Permissions-Policy (newer standard): Controls browser features.
        # Example: "geolocation 'none'; microphone 'none';"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=()"
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from config import settings
from utils.logger import get_logger

logger = get_logger(__name__)

def add_cors_and_security_headers(app: FastAPI):
    """
    Configures CORS middleware and adds custom security headers to the FastAPI application.
    """
    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
        allow_methods=settings.CORS_ALLOW_METHODS,
        allow_headers=settings.CORS_ALLOW_HEADERS,
    )
    logger.info(f"CORS configured with origins: {settings.CORS_ORIGINS}")

    # Add custom security headers middleware
    @app.middleware("http")
    async def add_security_headers(request: Request, call_next):
        """
        Middleware to add common security headers to all responses.
        """
        response = await call_next(request)
        
        # X-Content-Type-Options: Prevents browsers from MIME-sniffing a response away from the declared content-type.
        response.headers["X-Content-Type-Options"] = "nosniff"
        
        # X-Frame-Options: Prevents clickjacking attacks by controlling whether the page can be embedded in an iframe.
        response.headers["X-Frame-Options"] = "DENY"
        
        # X-XSS-Protection: Enables the XSS filter in most modern web browsers.
        response.headers["X-XSS-Protection"] = "1; mode=block"
        
        # Referrer-Policy: Controls how much referrer information is included with requests.
        response.headers["Referrer-Policy"] = "no-referrer-when-downgrade"
        
        # Strict-Transport-Security (HSTS): Forces all communication over HTTPS.
        # Max-age should be long (e.g., 1 year = 31536000 seconds) in production.
        # includeSubDomains is important for protecting subdomains.
        # preload is for submitting your domain to browser HSTS preload lists.
        if not settings.DEBUG_MODE: # Only apply HSTS in production
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains; preload"
        
        # Content-Security-Policy (CSP): Prevents a wide range of attacks, including XSS and data injection.
        # This is a basic example; a real CSP should be carefully crafted for your application.
        # response.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline';"
        
        # Permissions-Policy (formerly Feature-Policy): Allows or disallows the use of browser features.
        # Example: disallow camera and microphone access
        # response.headers["Permissions-Policy"] = "camera=(), microphone=()"

        logger.debug(f"Security headers added for request to {request.url.path}")
        return response
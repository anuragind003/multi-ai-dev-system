"""
Middleware for tracking agent temperature metrics in API requests.
"""
from fastapi import Request
import time
from typing import Callable
import json
import os
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

class TemperatureMetricsMiddleware(BaseHTTPMiddleware):
    """
    Middleware that tracks agent-specific temperature metrics 
    and execution times for all API requests.
    """
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Skip processing for OpenAPI and documentation endpoints
        if request.url.path in ["/openapi.json", "/docs", "/redoc", "/docs/oauth2-redirect"]:
            return await call_next(request)
            
        # Start timer
        start_time = time.time()
        
        # Check if request contains temperature strategy data
        temp_strategy = {}
        
        # For POST requests with JSON body
        if request.method == "POST" and "application/json" in request.headers.get("content-type", ""):
            try:
                body_bytes = await request.body()
                if body_bytes:
                    try:
                        body = json.loads(body_bytes.decode())
                        temp_strategy = body.get("temperature_strategy", {})
                    except json.JSONDecodeError:
                        pass
                        
                # Add the body back to the request so it can be read again
                async def receive():
                    return {"type": "http.request", "body": body_bytes}
                
                request._receive = receive
            except Exception:
                # If there's any error reading the body, just continue
                pass
        
        # Execute the request handler
        response = await call_next(request)
        
        # Calculate execution time
        execution_time = time.time() - start_time
        
        # Log metrics
        if temp_strategy:
            # Add temperature metrics to response headers for tracking
            response.headers["X-Agent-Temperatures"] = ",".join([
                f"{agent}:{temp}" for agent, temp in temp_strategy.items()
            ])
            response.headers["X-Execution-Time"] = f"{execution_time:.3f}s"
            
            # Log detailed metrics for monitoring
            print(f"API Request completed in {execution_time:.3f}s with temperature strategy: {temp_strategy}")
        
        return response
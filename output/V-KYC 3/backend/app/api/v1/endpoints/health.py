from fastapi import APIRouter, status, Response

router = APIRouter()

@router.get("/health", summary="Health Check", response_description="Service health status")
async def health_check():
    """
    Performs a health check on the service.
    Returns 200 OK if the service is running.
    """
    return {"status": "ok", "message": "Service is healthy"}

@router.get("/liveness", summary="Liveness Probe", status_code=status.HTTP_200_OK)
async def liveness_probe(response: Response):
    """
    Liveness probe for Kubernetes.
    Indicates if the application is running.
    """
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return {"status": "Liveness OK"}

@router.get("/readiness", summary="Readiness Probe", status_code=status.HTTP_200_OK)
async def readiness_probe(response: Response):
    """
    Readiness probe for Kubernetes.
    Indicates if the application is ready to serve traffic (e.g., DB connection, external services).
    """
    # In a real application, you would check database connections,
    # external service availability, etc.
    # For now, we assume it's always ready if it's alive.
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return {"status": "Readiness OK"}
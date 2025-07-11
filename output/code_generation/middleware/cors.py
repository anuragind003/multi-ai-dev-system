from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import settings
from utils.logger import get_logger

logger = get_logger(__name__)

def add_cors_middleware(app: FastAPI):
    """
    Adds CORS (Cross-Origin Resource Sharing) middleware to the FastAPI application.
    Configures allowed origins, methods, headers, and credentials based on settings.
    """
    logger.info(f"Adding CORS middleware. Allowed origins: {settings.CORS_ORIGINS}")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=settings.CORS_CREDENTIALS,
        allow_methods=settings.CORS_METHODS,
        allow_headers=settings.CORS_HEADERS,
    )
    logger.info("CORS middleware added.")

if __name__ == "__main__":
    # Example of how to use this function
    from fastapi.testclient import TestClient

    test_app = FastAPI()
    add_cors_middleware(test_app)

    @test_app.get("/")
    def read_root():
        return {"message": "Hello CORS!"}

    client = TestClient(test_app)

    # Test with an allowed origin
    response = client.get("/", headers={"Origin": "http://localhost:3000"})
    print(f"Response from allowed origin: {response.headers.get('Access-Control-Allow-Origin')}")
    assert response.headers.get("Access-Control-Allow-Origin") == "http://localhost:3000"

    # Test with a disallowed origin (if not '*' is allowed)
    response = client.get("/", headers={"Origin": "http://evil.com"})
    print(f"Response from disallowed origin: {response.headers.get('Access-Control-Allow-Origin')}")
    # Depending on CORS configuration, this might be None or the first allowed origin
    # If allow_origins is specific, it should not return http://evil.com
    assert response.headers.get("Access-Control-Allow-Origin") != "http://evil.com"
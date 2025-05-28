from functools import wraps
from flask import request, jsonify, make_response
from werkzeug.exceptions import HTTPException, InternalServerError
from pydantic import BaseModel, ValidationError
import logging

# Configure logging for the decorators
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def api_response(f):
    """
    Decorator to standardize API responses and handle exceptions.
    It wraps the function to return a JSON response with 'status', 'message', and 'data'.
    Handles Flask's HTTPException (e.g., BadRequest, NotFound) and general Exceptions.

    The decorated function should return:
    - (data, status_code): where data is the payload for the 'data' key, and status_code is the HTTP status.
    - data: where data is the payload for the 'data' key, implying a 200 OK status.
    - (response_dict, status_code): where response_dict is an already structured dictionary
                                    containing 'status', 'message', and optionally 'data'/'errors'.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            # Execute the decorated function
            result = f(*args, **kwargs)

            # Determine status code and actual data
            if isinstance(result, tuple) and len(result) == 2:
                data, status_code = result
            else:
                data = result
                status_code = 200 # Default to OK

            # Check if the function already returned a structured response
            if isinstance(data, dict) and 'status' in data and 'message' in data:
                final_response = data
            else:
                # Otherwise, wrap the result in a standard success response
                final_response = {
                    "status": "success",
                    "message": "Operation successful",
                    "data": data
                }

            return make_response(jsonify(final_response), status_code)

        except HTTPException as e:
            # Handle Flask/Werkzeug HTTP exceptions (e.g., 400, 404, 401)
            logger.warning(f"HTTP Exception: {e.code} - {e.description}")
            return make_response(jsonify({
                "status": "error",
                "message": e.description,
                "errors": getattr(e, 'data', None) # Custom data attached to HTTPException
            }), e.code)
        except Exception as e:
            # Handle any other unexpected exceptions
            logger.exception(f"An unexpected internal server error occurred: {e}")
            return make_response(jsonify({
                "status": "error",
                "message": "An internal server error occurred.",
                "errors": str(e)
            }), InternalServerError.code)
    return decorated_function

def validate_request(schema: type[BaseModel]):
    """
    Decorator to validate incoming JSON request body against a Pydantic schema.
    If validation fails, it returns a 400 Bad Request response with validation errors.
    If successful, it passes the validated data as a keyword argument 'validated_data'
    to the decorated function.

    Args:
        schema (BaseModel): The Pydantic model to validate the request body against.
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not request.is_json:
                logger.warning("Request Content-Type is not application/json.")
                return make_response(jsonify({
                    "status": "error",
                    "message": "Request must be JSON",
                    "errors": "Content-Type must be application/json"
                }), 400)
            try:
                data = request.get_json()
                if data is None:
                    logger.warning("Request body is empty or not valid JSON.")
                    return make_response(jsonify({
                        "status": "error",
                        "message": "Request body is empty or malformed JSON",
                        "errors": "Expected a JSON payload"
                    }), 400)

                # Use Pydantic's model_validate for validation (Pydantic v2)
                validated_data = schema.model_validate(data)
                kwargs['validated_data'] = validated_data # Pass validated data to the function
                return f(*args, **kwargs)
            except ValidationError as e:
                logger.warning(f"Request validation error: {e.errors()}")
                return make_response(jsonify({
                    "status": "error",
                    "message": "Invalid request data",
                    "errors": e.errors() # Pydantic's detailed validation errors
                }), 400)
            except Exception as e:
                logger.exception(f"Error processing request body: {e}")
                return make_response(jsonify({
                    "status": "error",
                    "message": "Failed to parse or process request body",
                    "errors": str(e)
                }), 400)
        return decorated_function
    return decorator

def requires_auth(f):
    """
    Placeholder decorator for authentication.
    In a real application, this would verify user credentials (e.g., JWT, API Key, OAuth token).
    For the MVP, it serves as a structural placeholder.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Example: Check for an 'Authorization' header
        # auth_header = request.headers.get('Authorization')
        # if not auth_header:
        #     logger.warning("Authentication required: Missing Authorization header.")
        #     return make_response(jsonify({"status": "error", "message": "Authentication required"}), 401)
        #
        # # Basic example: Check for a specific API key
        # expected_api_key = "YOUR_SECRET_API_KEY" # This should come from config/env vars
        # if auth_header != f"Bearer {expected_api_key}":
        #     logger.warning("Authentication failed: Invalid API key.")
        #     return make_response(jsonify({"status": "error", "message": "Invalid credentials"}), 401)

        logger.info("Authentication placeholder passed. (Implement actual authentication logic here)")
        return f(*args, **kwargs)
    return decorated_function
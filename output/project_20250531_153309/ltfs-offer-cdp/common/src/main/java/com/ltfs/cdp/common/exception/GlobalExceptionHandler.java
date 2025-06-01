package com.ltfs.cdp.common.exception;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpStatus;
import org.springframework.http.HttpStatusCode;
import org.springframework.http.ResponseEntity;
import org.springframework.http.converter.HttpMessageNotReadableException;
import org.springframework.validation.FieldError;
import org.springframework.web.bind.MethodArgumentNotValidException;
import org.springframework.web.bind.annotation.ControllerAdvice;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.context.request.ServletWebRequest;
import org.springframework.web.context.request.WebRequest;
import org.springframework.web.servlet.NoHandlerFoundException;
import org.springframework.web.servlet.mvc.method.annotation.ResponseEntityExceptionHandler;
import org.springframework.dao.DataIntegrityViolationException;

import jakarta.validation.ConstraintViolationException;
import java.time.LocalDateTime;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.stream.Collectors;

/**
 * Centralized Spring @ControllerAdvice for handling common exceptions and returning standardized error responses.
 * This class extends {@link ResponseEntityExceptionHandler} to leverage Spring's default exception handling
 * for common Spring MVC exceptions, and overrides/adds custom handlers for specific scenarios.
 * It provides a consistent error response structure for the LTFS Offer CDP application, ensuring
 * that API consumers receive predictable and informative error messages.
 */
@ControllerAdvice
@Slf4j // Lombok annotation for logging, providing a logger instance named 'log'
public class GlobalExceptionHandler extends ResponseEntityExceptionHandler {

    /**
     * Handles validation errors for @RequestBody objects.
     * This method is invoked when a method argument annotated with @Valid or @Validated fails validation.
     * It collects all field errors and returns a 400 Bad Request response with details about each invalid field.
     *
     * @param ex The MethodArgumentNotValidException that occurred.
     * @param headers The headers of the request.
     * @param status The HTTP status code.
     * @param request The current web request.
     * @return A ResponseEntity containing the standardized ErrorResponse.
     */
    @Override
    protected ResponseEntity<Object> handleMethodArgumentNotValid(MethodArgumentNotValidException ex,
                                                                  HttpHeaders headers,
                                                                  HttpStatusCode status,
                                                                  WebRequest request) {
        log.error("Validation error for request body: {}", ex.getMessage());

        // Collect all field errors into a map (field name -> error message)
        Map<String, String> errors = ex.getBindingResult().getFieldErrors().stream()
                .collect(Collectors.toMap(
                        FieldError::getField,
                        fieldError -> fieldError.getDefaultMessage() != null ? fieldError.getDefaultMessage() : "Validation error",
                        (existing, replacement) -> existing, // Merge function for duplicate keys, keep existing
                        LinkedHashMap::new // Use LinkedHashMap to preserve the order of errors
                ));

        ErrorResponse errorResponse = new ErrorResponse(
                LocalDateTime.now(),
                HttpStatus.BAD_REQUEST.value(),
                HttpStatus.BAD_REQUEST.getReasonPhrase(),
                "Validation failed for request body. Please check the provided data.",
                getRequestPath(request),
                errors
        );
        return new ResponseEntity<>(errorResponse, HttpStatus.BAD_REQUEST);
    }

    /**
     * Handles cases where the request body is malformed or unreadable (e.g., invalid JSON syntax,
     * missing required parts, or incorrect data types that prevent deserialization).
     * Returns a 400 Bad Request response.
     *
     * @param ex The HttpMessageNotReadableException that occurred.
     * @param headers The headers of the request.
     * @param status The HTTP status code.
     * @param request The current web request.
     * @return A ResponseEntity containing the standardized ErrorResponse.
     */
    @Override
    protected ResponseEntity<Object> handleHttpMessageNotReadable(HttpMessageNotReadableException ex,
                                                                  HttpHeaders headers,
                                                                  HttpStatusCode status,
                                                                  WebRequest request) {
        log.error("Malformed JSON request or unreadable message: {}", ex.getMessage());
        ErrorResponse errorResponse = new ErrorResponse(
                LocalDateTime.now(),
                HttpStatus.BAD_REQUEST.value(),
                HttpStatus.BAD_REQUEST.getReasonPhrase(),
                "Malformed JSON request body or unreadable message. Please check your request syntax.",
                getRequestPath(request),
                null
        );
        return new ResponseEntity<>(errorResponse, HttpStatus.BAD_REQUEST);
    }

    /**
     * Handles cases where no handler (controller method) is found for the incoming request URI.
     * This typically results in a 404 Not Found error.
     * Note: This handler requires `spring.mvc.throw-exception-if-no-handler-found=true`
     * and `spring.web.resources.add-mappings=false` in `application.properties` to be effective.
     *
     * @param ex The NoHandlerFoundException that occurred.
     * @param headers The headers of the request.
     * @param status The HTTP status code.
     * @param request The current web request.
     * @return A ResponseEntity containing the standardized ErrorResponse.
     */
    @Override
    protected ResponseEntity<Object> handleNoHandlerFoundException(NoHandlerFoundException ex,
                                                                   HttpHeaders headers,
                                                                   HttpStatusCode status,
                                                                   WebRequest request) {
        log.warn("No handler found for {} {}: {}", ex.getHttpMethod(), ex.getRequestURL(), ex.getMessage());
        ErrorResponse errorResponse = new ErrorResponse(
                LocalDateTime.now(),
                HttpStatus.NOT_FOUND.value(),
                HttpStatus.NOT_FOUND.getReasonPhrase(),
                "The requested resource was not found. Please check the URL.",
                getRequestPath(request),
                null
        );
        return new ResponseEntity<>(errorResponse, HttpStatus.NOT_FOUND);
    }

    /**
     * Handles exceptions related to JSR 303/380 bean validation constraints
     * (e.g., @RequestParam, @PathVariable validation, or validation triggered manually on service layer).
     * Returns a 400 Bad Request response with details about the constraint violations.
     *
     * @param ex The ConstraintViolationException that occurred.
     * @param request The current web request.
     * @return A ResponseEntity containing the standardized ErrorResponse.
     */
    @ExceptionHandler(ConstraintViolationException.class)
    public ResponseEntity<Object> handleConstraintViolation(ConstraintViolationException ex, WebRequest request) {
        log.error("Constraint violation for request parameters/path variables: {}", ex.getMessage());

        // Collect all constraint violations into a map (property path -> error message)
        Map<String, String> errors = ex.getConstraintViolations().stream()
                .collect(Collectors.toMap(
                        violation -> violation.getPropertyPath().toString(),
                        violation -> violation.getMessage() != null ? violation.getMessage() : "Constraint violation",
                        (existing, replacement) -> existing,
                        LinkedHashMap::new
                ));

        ErrorResponse errorResponse = new ErrorResponse(
                LocalDateTime.now(),
                HttpStatus.BAD_REQUEST.value(),
                HttpStatus.BAD_REQUEST.getReasonPhrase(),
                "Validation failed for request parameters or path variables. Please check the provided values.",
                getRequestPath(request),
                errors
        );
        return new ResponseEntity<>(errorResponse, HttpStatus.BAD_REQUEST);
    }

    /**
     * Handles exceptions related to data integrity violations, typically from database operations.
     * This can occur due to unique constraint violations, foreign key violations, or other database-level
     * constraints being violated during data persistence. Returns a 409 Conflict response.
     *
     * @param ex The DataIntegrityViolationException that occurred.
     * @param request The current web request.
     * @return A ResponseEntity containing the standardized ErrorResponse.
     */
    @ExceptionHandler(DataIntegrityViolationException.class)
    public ResponseEntity<Object> handleDataIntegrityViolation(DataIntegrityViolationException ex, WebRequest request) {
        log.error("Data integrity violation: {}", ex.getMessage());
        String errorMessage = "A data integrity constraint was violated. This might be due to duplicate entries or invalid data relationships.";
        HttpStatus status = HttpStatus.CONFLICT; // Often 409 Conflict for unique constraints

        // In a real application, you might inspect ex.getCause() to provide more specific messages
        // based on the underlying database exception (e.g., PSQLException for PostgreSQL,
        // which could indicate a unique constraint violation by error code).

        ErrorResponse errorResponse = new ErrorResponse(
                LocalDateTime.now(),
                status.value(),
                status.getReasonPhrase(),
                errorMessage,
                getRequestPath(request),
                null
        );
        return new ResponseEntity<>(errorResponse, status);
    }

    // --- Custom/Project-Specific Exceptions ---
    // These exceptions would typically be defined in separate files within the same package
    // (e.g., com.ltfs.cdp.common.exception.ResourceNotFoundException.java).
    // For the purpose of generating a single runnable file, they are included as static inner classes.

    /**
     * Handles a generic "Resource Not Found" exception.
     * This would typically be a custom exception thrown by service layers when a requested entity
     * (e.g., Customer, Offer, Campaign) is not found in the system.
     * Returns a 404 Not Found response.
     *
     * @param ex The ResourceNotFoundException that occurred.
     * @param request The current web request.
     * @return A ResponseEntity containing the standardized ErrorResponse.
     */
    @ExceptionHandler(ResourceNotFoundException.class)
    public ResponseEntity<Object> handleResourceNotFoundException(ResourceNotFoundException ex, WebRequest request) {
        log.warn("Resource not found: {}", ex.getMessage());
        ErrorResponse errorResponse = new ErrorResponse(
                LocalDateTime.now(),
                HttpStatus.NOT_FOUND.value(),
                HttpStatus.NOT_FOUND.getReasonPhrase(),
                ex.getMessage(), // Use the exception's message as the detailed error message
                getRequestPath(request),
                null
        );
        return new ResponseEntity<>(errorResponse, HttpStatus.NOT_FOUND);
    }

    /**
     * Handles a generic "Bad Request" exception.
     * This would typically be a custom exception thrown by service layers for business rule violations
     * that result in a 400 error (e.g., invalid input data that passes basic validation but fails
     * more complex business logic, like deduplication rules).
     * Returns a 400 Bad Request response.
     *
     * @param ex The BadRequestException that occurred.
     * @param request The current web request.
     * @return A ResponseEntity containing the standardized ErrorResponse.
     */
    @ExceptionHandler(BadRequestException.class)
    public ResponseEntity<Object> handleBadRequestException(BadRequestException ex, WebRequest request) {
        log.warn("Bad request: {}", ex.getMessage());
        ErrorResponse errorResponse = new ErrorResponse(
                LocalDateTime.now(),
                HttpStatus.BAD_REQUEST.value(),
                HttpStatus.BAD_REQUEST.getReasonPhrase(),
                ex.getMessage(), // Use the exception's message as the detailed error message
                getRequestPath(request),
                null
        );
        return new ResponseEntity<>(errorResponse, HttpStatus.BAD_REQUEST);
    }

    /**
     * Handles any other unhandled exceptions. This is a catch-all handler for unexpected errors
     * that were not specifically caught by other @ExceptionHandler methods.
     * Logs the full stack trace for debugging and returns a 500 Internal Server Error response.
     *
     * @param ex The Exception that occurred.
     * @param request The current web request.
     * @return A ResponseEntity containing the standardized ErrorResponse.
     */
    @ExceptionHandler(Exception.class)
    public ResponseEntity<Object> handleAllExceptions(Exception ex, WebRequest request) {
        log.error("An unexpected error occurred: {}", ex.getMessage(), ex); // Log stack trace for unexpected errors
        ErrorResponse errorResponse = new ErrorResponse(
                LocalDateTime.now(),
                HttpStatus.INTERNAL_SERVER_ERROR.value(),
                HttpStatus.INTERNAL_SERVER_ERROR.getReasonPhrase(),
                "An unexpected error occurred. Please try again later or contact support.",
                getRequestPath(request),
                null
        );
        return new ResponseEntity<>(errorResponse, HttpStatus.INTERNAL_SERVER_ERROR);
    }

    /**
     * Helper method to extract the request URI from the WebRequest.
     * This provides the 'path' field for the ErrorResponse.
     *
     * @param request The current web request.
     * @return The request URI as a String, or "unknown" if it cannot be determined.
     */
    private String getRequestPath(WebRequest request) {
        if (request instanceof ServletWebRequest) {
            return ((ServletWebRequest) request).getRequest().getRequestURI();
        }
        return "unknown"; // Fallback if path cannot be determined
    }

    // --- Inner classes for custom exceptions and ErrorResponse DTO for self-containment ---
    // In a multi-file project, these would typically be in their own respective .java files
    // within the com.ltfs.cdp.common.exception package. They are included here to make
    // this single file directly runnable and self-contained.

    /**
     * A generic custom exception for resources not found (HTTP 404).
     * This exception should be thrown by service layers when a requested entity does not exist.
     */
    public static class ResourceNotFoundException extends RuntimeException {
        public ResourceNotFoundException(String message) {
            super(message);
        }
    }

    /**
     * A generic custom exception for bad requests/business rule violations (HTTP 400).
     * This exception should be thrown by service layers when input data is invalid based on
     * business rules, even if it passes basic structural validation.
     */
    public static class BadRequestException extends RuntimeException {
        public BadRequestException(String message) {
            super(message);
        }
    }

    /**
     * DTO (Data Transfer Object) for standardized error responses returned by the API.
     * This ensures a consistent format for all error messages across the application.
     * Uses Lombok annotations for boilerplate code (getters, setters, constructors).
     */
    @Data
    @AllArgsConstructor
    @NoArgsConstructor
    public static class ErrorResponse {
        private LocalDateTime timestamp; // The time when the error occurred
        private int status;              // The HTTP status code (e.g., 400, 404, 500)
        private String error;            // The HTTP status reason phrase (e.g., "Bad Request", "Not Found")
        private String message;          // A detailed, human-readable error message
        private String path;             // The request URI that caused the error
        private Map<String, String> details; // Optional: For validation errors, a map of fieldName -> errorMessage
    }
}
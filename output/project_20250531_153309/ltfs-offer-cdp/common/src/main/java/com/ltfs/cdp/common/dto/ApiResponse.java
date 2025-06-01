package com.ltfs.cdp.common.dto;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * Standardized wrapper for API responses across the LTFS Offer CDP system.
 * This class provides a consistent structure for all API responses,
 * including a success indicator, a descriptive message, and the actual data payload.
 * It leverages Lombok annotations to reduce boilerplate code.
 *
 * @param <T> The type of the data payload.
 */
@Data // Generates getters, setters, toString, equals, and hashCode methods
@NoArgsConstructor // Generates a no-argument constructor
@AllArgsConstructor // Generates a constructor with all fields as arguments
@Builder // Provides a builder pattern for object creation, enabling fluent object construction
public class ApiResponse<T> {

    /**
     * Indicates whether the API operation was successful.
     * True if the operation succeeded, false otherwise. This boolean flag
     * provides a quick way for clients to determine the outcome of a request.
     */
    private boolean success;

    /**
     * A descriptive message providing details about the API response.
     * This can be a success message (e.g., "Customer profile updated successfully"),
     * an error message (e.g., "Validation failed: Invalid customer ID"), or any
     * relevant informational message.
     */
    private String message;

    /**
     * The actual data payload returned by the API.
     * This can be any object (e.g., CustomerDTO, OfferDTO), a list of objects,
     * or null if no specific data is returned (e.g., for a successful deletion).
     * The generic type {@code T} allows flexibility in the data type.
     */
    private T data;

    /**
     * Static factory method to create a successful API response with a data payload.
     * This method simplifies the creation of common success responses.
     *
     * @param data The data payload to be returned.
     * @param message A success message describing the outcome of the operation.
     * @param <T> The type of the data payload.
     * @return A new ApiResponse instance indicating success with the provided data and message.
     */
    public static <T> ApiResponse<T> success(T data, String message) {
        return ApiResponse.<T>builder()
                .success(true)
                .message(message)
                .data(data)
                .build();
    }

    /**
     * Static factory method to create a successful API response without a specific data payload.
     * This is useful for operations that complete successfully but do not return any specific
     * entity or collection (e.g., a successful update or delete operation).
     *
     * @param message A success message describing the outcome of the operation.
     * @param <T> The type of the data payload (can be Void or Object if no data is expected).
     * @return A new ApiResponse instance indicating success with only a message.
     */
    public static <T> ApiResponse<T> success(String message) {
        return ApiResponse.<T>builder()
                .success(true)
                .message(message)
                .data(null) // No specific data payload for this type of success response
                .build();
    }

    /**
     * Static factory method to create an error API response without a specific data payload.
     * This method is used for general error scenarios where no specific error details
     * need to be returned in the data field.
     *
     * @param message An error message describing the issue that occurred.
     * @param <T> The type of the data payload (will be null for general errors).
     * @return A new ApiResponse instance indicating an error with the provided message.
     */
    public static <T> ApiResponse<T> error(String message) {
        return ApiResponse.<T>builder()
                .success(false)
                .message(message)
                .data(null) // No data payload for general error responses
                .build();
    }

    /**
     * Static factory method to create an error API response with a specific data payload.
     * This is particularly useful for scenarios like validation errors, where the 'data' field
     * can contain a structured object or list detailing the specific validation failures
     * (e.g., a map of field names to error messages).
     *
     * @param data The data payload, often containing structured error details (e.g., a list of validation errors).
     * @param message An error message describing the issue.
     * @param <T> The type of the data payload.
     * @return A new ApiResponse instance indicating an error with the provided data and message.
     */
    public static <T> ApiResponse<T> error(T data, String message) {
        return ApiResponse.<T>builder()
                .success(false)
                .message(message)
                .data(data)
                .build();
    }
}
package com.ltfs.cdp.common.dto;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import javax.validation.constraints.Min;
import javax.validation.constraints.Positive;

/**
 * DTO (Data Transfer Object) for handling common pagination request parameters.
 * This class encapsulates parameters such as page number, page size, and sorting criteria
 * that are typically used in paginated API endpoints.
 *
 * <p>It uses Lombok annotations for boilerplate code generation (getters, setters,
 * constructors, builder pattern) and Javax Validation annotations for basic input validation.</p>
 */
@Data
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class PaginationRequest {

    /**
     * The current page number to retrieve.
     * This is typically 0-indexed, meaning the first page is 0.
     * Must be a non-negative value.
     * Default value is 0 if not explicitly provided.
     */
    @Min(value = 0, message = "Page number must be non-negative.")
    @Builder.Default
    private Integer page = 0;

    /**
     * The maximum number of items to be returned per page.
     * Must be a positive value.
     * Default value is 10 if not explicitly provided.
     */
    @Positive(message = "Page size must be positive.")
    @Builder.Default
    private Integer size = 10;

    /**
     * The field name by which the results should be sorted.
     * This string should correspond to a valid field in the entity being queried.
     * Can be null if no specific sorting is required.
     * Example: "customerName", "offerAmount".
     */
    private String sortBy;

    /**
     * The sorting order (direction) for the {@code sortBy} field.
     * Uses the {@link SortDirection} enum to restrict values to 'ASC' (ascending) or 'DESC' (descending).
     * Can be null if no specific sorting is required or if {@code sortBy} is null.
     */
    private SortDirection sortOrder;

    /**
     * Enum representing the possible sorting directions.
     * Provides a clear and type-safe way to specify sort order.
     */
    public enum SortDirection {
        /**
         * Ascending order (e.g., A-Z, 0-9).
         */
        ASC,
        /**
         * Descending order (e.g., Z-A, 9-0).
         */
        DESC
    }
}
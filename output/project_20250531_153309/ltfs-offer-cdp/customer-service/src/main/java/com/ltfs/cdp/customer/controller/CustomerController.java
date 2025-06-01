package com.ltfs.cdp.customer.controller;

import com.ltfs.cdp.customer.exception.ResourceNotFoundException;
import com.ltfs.cdp.customer.model.CustomerProfileDTO;
import com.ltfs.cdp.customer.model.DeduplicationStatusDTO;
import com.ltfs.cdp.customer.model.DeduplicationStatusUpdateDTO;
import com.ltfs.cdp.customer.model.CustomerSegmentationRequestDTO;
import com.ltfs.cdp.customer.service.CustomerService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;

/**
 * REST Controller for managing customer-related operations in the LTFS Offer CDP system.
 * This controller handles requests for retrieving customer profiles, managing deduplication status,
 * and performing customer segmentation queries.
 *
 * It interacts with the CustomerService to perform business logic and data retrieval.
 *
 * Assumed external dependencies (DTOs, Service, Exception) are imported from their respective packages.
 * In a real production-grade project, these would be defined in separate files within the project structure.
 */
@RestController
@RequestMapping("/api/v1/customers")
public class CustomerController {

    private final CustomerService customerService;

    /**
     * Constructs a CustomerController with the necessary CustomerService dependency.
     * Spring's @Autowired annotation handles the dependency injection,
     * ensuring the CustomerService implementation is provided by the Spring context.
     *
     * @param customerService The service layer for customer-related operations.
     */
    @Autowired
    public CustomerController(CustomerService customerService) {
        this.customerService = customerService;
    }

    /**
     * Retrieves a single customer profile by their unique customer ID.
     * This endpoint provides a single profile view of the customer for Consumer Loan Products,
     * fulfilling a core functional requirement of the CDP system through deduplication.
     *
     * @param customerId The unique identifier of the customer (e.g., UUID, internal ID).
     * @return A {@link ResponseEntity} containing the {@link CustomerProfileDTO} if found (HTTP 200 OK),
     *         or a 404 Not Found status if the customer does not exist.
     *         Returns 500 Internal Server Error for unexpected issues.
     */
    @GetMapping("/{customerId}")
    public ResponseEntity<CustomerProfileDTO> getCustomerProfile(@PathVariable String customerId) {
        try {
            CustomerProfileDTO customerProfile = customerService.getCustomerProfileById(customerId);
            return ResponseEntity.ok(customerProfile);
        } catch (ResourceNotFoundException e) {
            // In a real application, a logger (e.g., SLF4J) would be used here.
            // logger.warn("Customer profile not found for ID: {}", customerId, e);
            return ResponseEntity.status(HttpStatus.NOT_FOUND).build();
        } catch (Exception e) {
            // Catch any other unexpected exceptions and return a 500 Internal Server Error.
            // logger.error("An unexpected error occurred while fetching customer profile for ID: {}", customerId, e);
            return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR).build();
        }
    }

    /**
     * Retrieves the deduplication status for a specific customer.
     * This is crucial for understanding if a customer has been deduped against the 'live book' (Customer 360)
     * before offers are finalized, as per functional requirements. It also supports applying dedupe logic
     * across all Consumer Loan (CL) products.
     *
     * @param customerId The unique identifier of the customer.
     * @return A {@link ResponseEntity} containing the {@link DeduplicationStatusDTO} if found (HTTP 200 OK),
     *         or a 404 Not Found status if the customer or their deduplication status record does not exist.
     *         Returns 500 Internal Server Error for unexpected issues.
     */
    @GetMapping("/{customerId}/deduplication-status")
    public ResponseEntity<DeduplicationStatusDTO> getDeduplicationStatus(@PathVariable String customerId) {
        try {
            DeduplicationStatusDTO status = customerService.getDeduplicationStatus(customerId);
            return ResponseEntity.ok(status);
        } catch (ResourceNotFoundException e) {
            // logger.warn("Deduplication status not found for customer ID: {}", customerId, e);
            return ResponseEntity.status(HttpStatus.NOT_FOUND).build();
        } catch (Exception e) {
            // logger.error("An unexpected error occurred while fetching deduplication status for ID: {}", customerId, e);
            return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR).build();
        }
    }

    /**
     * Updates the deduplication status for a specific customer.
     * This endpoint allows for managing the deduplication state, which is vital for the CDP system's
     * ability to apply dedupe logic across various Consumer Loan products and manage offer eligibility.
     *
     * @param customerId The unique identifier of the customer.
     * @param updateDTO The Data Transfer Object containing the new deduplication status.
     * @return A {@link ResponseEntity} with 200 OK if updated successfully, or 404 Not Found if the customer
     *         does not exist. Returns 500 Internal Server Error for unexpected issues.
     */
    @PutMapping("/{customerId}/deduplication-status")
    public ResponseEntity<Void> updateDeduplicationStatus(
            @PathVariable String customerId,
            @RequestBody DeduplicationStatusUpdateDTO updateDTO) {
        try {
            customerService.updateDeduplicationStatus(customerId, updateDTO);
            return ResponseEntity.ok().build(); // Or ResponseEntity.noContent().build() for 204 No Content
        } catch (ResourceNotFoundException e) {
            // logger.warn("Customer not found for ID: {} during deduplication status update.", customerId, e);
            return ResponseEntity.status(HttpStatus.NOT_FOUND).build();
        } catch (Exception e) {
            // logger.error("An unexpected error occurred while updating deduplication status for ID: {}", customerId, e);
            return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR).build();
        }
    }

    /**
     * Performs a customer segmentation query based on provided criteria.
     * This endpoint supports retrieving customers based on various attributes (e.g., product type,
     * loan status, demographics, deduplication status) for targeted campaigns or specific analysis,
     * enabling faster processing of customer data.
     *
     * @param requestDTO The Data Transfer Object containing the segmentation criteria.
     * @return A {@link ResponseEntity} containing a list of {@link CustomerProfileDTO}s matching the criteria (HTTP 200 OK).
     *         Returns an empty list if no customers match the criteria.
     *         Returns 500 Internal Server Error on unexpected issues.
     */
    @PostMapping("/segmentation/search")
    public ResponseEntity<List<CustomerProfileDTO>> searchCustomersBySegmentation(
            @RequestBody CustomerSegmentationRequestDTO requestDTO) {
        try {
            List<CustomerProfileDTO> segmentedCustomers = customerService.searchCustomersBySegmentation(requestDTO);
            return ResponseEntity.ok(segmentedCustomers);
        } catch (Exception e) {
            // logger.error("An unexpected error occurred during customer segmentation search.", e);
            return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR).build();
        }
    }

    // Note on Error Handling:
    // For production-grade applications, it is highly recommended to implement a global exception handler
    // using Spring's @ControllerAdvice and @ExceptionHandler annotations. This provides a centralized
    // mechanism for handling exceptions across all controllers, leading to cleaner code and consistent
    // error responses (e.g., using Problem Details for HTTP APIs).
    // The current implementation uses individual try-catch blocks for demonstration within a single file context.
}
package com.ltfs.cdp.customer.controller;

import com.ltfs.cdp.customer.dto.CustomerDTO;
import com.ltfs.cdp.customer.exception.ResourceNotFoundException;
import com.ltfs.cdp.customer.service.CustomerService;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.validation.FieldError;
import org.springframework.web.bind.MethodArgumentNotValidException;
import org.springframework.web.bind.annotation.*;

import javax.validation.Valid;
import java.util.List;

/**
 * REST Controller for managing customer profiles and triggering deduplication processes.
 * This controller handles incoming HTTP requests related to customer data,
 * delegating business logic to the {@link CustomerService}.
 * It provides endpoints for CRUD operations on customer profiles and
 * an endpoint to initiate the customer deduplication process.
 */
@RestController
@RequestMapping("/api/v1/customers") // Base path for customer-related API endpoints
public class CustomerController {

    private final CustomerService customerService;

    /**
     * Constructs a new CustomerController with the given CustomerService.
     * Spring's dependency injection automatically provides the CustomerService instance.
     * @param customerService The service layer component responsible for customer business logic.
     */
    public CustomerController(CustomerService customerService) {
        this.customerService = customerService;
    }

    /**
     * Creates a new customer profile in the system.
     *
     * @param customerDTO The data transfer object containing the details of the customer to be created.
     *                    It is validated using JSR 303 annotations defined in CustomerDTO.
     * @return A {@link ResponseEntity} containing the created {@link CustomerDTO} with its assigned ID
     *         and an HTTP status of 201 (Created).
     */
    @PostMapping
    public ResponseEntity<CustomerDTO> createCustomer(@Valid @RequestBody CustomerDTO customerDTO) {
        CustomerDTO createdCustomer = customerService.createCustomer(customerDTO);
        return new ResponseEntity<>(createdCustomer, HttpStatus.CREATED);
    }

    /**
     * Retrieves a specific customer profile by their unique identifier.
     *
     * @param id The unique ID of the customer to retrieve. This ID is extracted from the URL path.
     * @return A {@link ResponseEntity} containing the {@link CustomerDTO} of the found customer
     *         and an HTTP status of 200 (OK).
     * @throws ResourceNotFoundException if no customer is found with the provided ID.
     *                                   This exception is handled by the controller's exception handler.
     */
    @GetMapping("/{id}")
    public ResponseEntity<CustomerDTO> getCustomerById(@PathVariable Long id) {
        CustomerDTO customer = customerService.getCustomerById(id);
        return ResponseEntity.ok(customer);
    }

    /**
     * Retrieves a list of all customer profiles.
     * <p>
     * Note: For production systems with large datasets, this endpoint should typically
     * implement pagination (e.g., using Pageable) to avoid performance issues.
     * </p>
     * @return A {@link ResponseEntity} containing a {@link List} of {@link CustomerDTO}s
     *         and an HTTP status of 200 (OK).
     */
    @GetMapping
    public ResponseEntity<List<CustomerDTO>> getAllCustomers() {
        List<CustomerDTO> customers = customerService.getAllCustomers();
        return ResponseEntity.ok(customers);
    }

    /**
     * Updates an existing customer profile identified by their unique ID.
     *
     * @param id The unique ID of the customer to update.
     * @param customerDTO The data transfer object containing the updated details for the customer.
     *                    It is validated using JSR 303 annotations.
     * @return A {@link ResponseEntity} containing the updated {@link CustomerDTO}
     *         and an HTTP status of 200 (OK).
     * @throws ResourceNotFoundException if no customer is found with the provided ID.
     */
    @PutMapping("/{id}")
    public ResponseEntity<CustomerDTO> updateCustomer(@PathVariable Long id, @Valid @RequestBody CustomerDTO customerDTO) {
        CustomerDTO updatedCustomer = customerService.updateCustomer(id, customerDTO);
        return ResponseEntity.ok(updatedCustomer);
    }

    /**
     * Deletes a customer profile identified by their unique ID.
     *
     * @param id The unique ID of the customer to delete.
     * @return A {@link ResponseEntity} with no content and an HTTP status of 204 (No Content),
     *         indicating successful deletion.
     * @throws ResourceNotFoundException if no customer is found with the provided ID.
     */
    @DeleteMapping("/{id}")
    public ResponseEntity<Void> deleteCustomer(@PathVariable Long id) {
        customerService.deleteCustomer(id);
        return ResponseEntity.noContent().build(); // 204 No Content
    }

    /**
     * Triggers the customer deduplication process.
     * This endpoint initiates an asynchronous operation to identify and merge duplicate customer records.
     * The actual deduplication logic is handled by the service layer, potentially involving
     * event-driven components or background jobs as per the microservices architecture.
     *
     * @return A {@link ResponseEntity} with a confirmation message and an HTTP status of 202 (Accepted),
     *         indicating that the request for deduplication has been accepted for processing.
     */
    @PostMapping("/deduplicate")
    public ResponseEntity<String> triggerDeduplication() {
        // The service layer will handle the actual triggering of the deduplication process.
        // This might involve publishing an event to a message broker (e.g., Kafka)
        // or invoking an asynchronous method.
        customerService.triggerDeduplicationProcess();
        return new ResponseEntity<>("Deduplication process initiated successfully.", HttpStatus.ACCEPTED);
    }

    /**
     * Exception handler for {@link ResourceNotFoundException}.
     * This method catches {@link ResourceNotFoundException} thrown by the service layer
     * and maps it to an HTTP 404 (Not Found) status.
     *
     * @param ex The caught {@link ResourceNotFoundException}.
     * @return A {@link ResponseEntity} containing the exception message and HTTP status 404.
     */
    @ExceptionHandler(ResourceNotFoundException.class)
    @ResponseStatus(HttpStatus.NOT_FOUND) // Ensures HTTP 404 is returned
    public ResponseEntity<String> handleResourceNotFoundException(ResourceNotFoundException ex) {
        return new ResponseEntity<>(ex.getMessage(), HttpStatus.NOT_FOUND);
    }

    /**
     * Exception handler for {@link MethodArgumentNotValidException}.
     * This method catches validation exceptions that occur when request body arguments
     * fail JSR 303 validation (e.g., @NotNull, @Size).
     * It constructs a user-friendly error message detailing the validation failures.
     *
     * @param ex The caught {@link MethodArgumentNotValidException}.
     * @return A {@link ResponseEntity} containing a concatenated string of validation errors
     *         and an HTTP status of 400 (Bad Request).
     */
    @ExceptionHandler(MethodArgumentNotValidException.class)
    @ResponseStatus(HttpStatus.BAD_REQUEST) // Ensures HTTP 400 is returned
    public ResponseEntity<String> handleValidationExceptions(MethodArgumentNotValidException ex) {
        StringBuilder errors = new StringBuilder();
        ex.getBindingResult().getAllErrors().forEach((error) -> {
            // Check if the error is a FieldError to get the field name
            if (error instanceof FieldError) {
                String fieldName = ((FieldError) error).getField();
                String errorMessage = error.getDefaultMessage();
                errors.append(fieldName).append(": ").append(errorMessage).append("; ");
            } else {
                // For global object errors (e.g., @Valid on a class level constraint)
                errors.append(error.getObjectName()).append(": ").append(error.getDefaultMessage()).append("; ");
            }
        });
        // Return a more descriptive error message
        return new ResponseEntity<>("Validation Error: " + errors.toString().trim(), HttpStatus.BAD_REQUEST);
    }
}
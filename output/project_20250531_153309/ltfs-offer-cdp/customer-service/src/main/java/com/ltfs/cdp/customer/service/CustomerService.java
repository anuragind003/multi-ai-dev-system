package com.ltfs.cdp.customer.service;

import com.ltfs.cdp.customer.dto.CustomerDTO;
import com.ltfs.cdp.customer.entity.Customer;
import com.ltfs.cdp.customer.exception.CustomerNotFoundException;
import com.ltfs.cdp.customer.exception.ValidationException;
import com.ltfs.cdp.customer.mapper.CustomerMapper;
import com.ltfs.cdp.customer.repository.CustomerRepository;
import com.ltfs.cdp.customer.event.CustomerCreatedEvent;
import com.ltfs.cdp.customer.event.CustomerProfileUpdatedEvent;
import com.ltfs.cdp.customer.service.DeduplicationService.DeduplicationResult;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.context.ApplicationEventPublisher;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.lang.reflect.Field;
import java.util.Map;
import java.util.UUID;

/**
 * Core service for managing customer data within the LTFS Offer CDP.
 * This service orchestrates customer data processing, including validation,
 * deduplication, profile creation, and attribute updates. It acts as the
 * central point for all customer-related business logic.
 */
@Service
public class CustomerService {

    private static final Logger log = LoggerFactory.getLogger(CustomerService.class);

    private final CustomerRepository customerRepository;
    private final CustomerMapper customerMapper;
    private final DeduplicationService deduplicationService;
    private final ValidationService validationService;
    private final ApplicationEventPublisher eventPublisher;

    /**
     * Constructor for CustomerService, injecting required dependencies.
     * Spring's dependency injection will automatically provide these beans.
     *
     * @param customerRepository The repository for Customer entities, handling database interactions.
     * @param customerMapper The mapper for converting between Customer DTOs and entities.
     * @param deduplicationService The service responsible for applying complex deduplication logic.
     * @param validationService The service responsible for validating incoming customer data.
     * @param eventPublisher The Spring ApplicationEventPublisher for publishing domain events
     *                       (e.g., CustomerCreatedEvent, CustomerProfileUpdatedEvent).
     */
    public CustomerService(CustomerRepository customerRepository,
                           CustomerMapper customerMapper,
                           DeduplicationService deduplicationService,
                           ValidationService validationService,
                           ApplicationEventPublisher eventPublisher) {
        this.customerRepository = customerRepository;
        this.customerMapper = customerMapper;
        this.deduplicationService = deduplicationService;
        this.validationService = validationService;
        this.eventPublisher = eventPublisher;
    }

    /**
     * Processes incoming customer data, performing validation, deduplication,
     * and either creating a new customer profile or updating an existing one.
     * This is the primary entry point for new customer data from sources like Offermart.
     * The method ensures data integrity and consistency by applying business rules.
     *
     * @param customerDTO The CustomerDTO containing the incoming customer data.
     *                    This DTO is expected to have basic customer attributes.
     * @return The CustomerDTO representing the created or updated customer profile,
     *         including its unique CDP customer ID.
     * @throws ValidationException If the incoming customer data fails basic column-level validation
     *                             (e.g., missing required fields, invalid formats).
     * @throws IllegalStateException If an unexpected state occurs during deduplication (e.g.,
     *                               a duplicate is identified but the matched customer entity is null).
     */
    @Transactional
    public CustomerDTO processCustomerData(CustomerDTO customerDTO) {
        log.info("Initiating customer data processing for PAN: {}, Mobile: {}",
                customerDTO.getPanNumber(), customerDTO.getMobileNumber());

        // 1. Perform basic column-level validation on the incoming DTO.
        // This ensures data quality before proceeding with business logic.
        try {
            validationService.validate(customerDTO);
            log.debug("Customer data validation successful for PAN: {}, Mobile: {}.",
                    customerDTO.getPanNumber(), customerDTO.getMobileNumber());
        } catch (ValidationException e) {
            log.error("Validation failed for incoming customer data (PAN: {}, Mobile: {}): {}",
                    customerDTO.getPanNumber(), customerDTO.getMobileNumber(), e.getMessage());
            throw e; // Re-throw to be handled by a global exception handler (e.g., @ControllerAdvice)
        }

        // 2. Apply deduplication logic to identify if the incoming data corresponds
        //    to an existing customer profile or a new one.
        DeduplicationResult deduplicationResult = deduplicationService.deduplicate(customerDTO);

        Customer processedCustomer;
        if (deduplicationResult.isDuplicate()) {
            // If a duplicate is found, update the existing customer profile.
            Customer existingCustomer = deduplicationResult.getMatchedCustomer();
            if (existingCustomer == null) {
                // This scenario indicates an internal inconsistency in the deduplication service.
                log.error("Deduplication identified a duplicate but returned a null matched customer for PAN: {}, Mobile: {}. This indicates a logic error.",
                        customerDTO.getPanNumber(), customerDTO.getMobileNumber());
                throw new IllegalStateException("Deduplication error: Matched customer not found despite being identified as a duplicate.");
            }

            log.info("Duplicate customer found. Updating existing profile with ID: {} using strategy: {}",
                    existingCustomer.getCustomerId(), deduplicationResult.getDeduplicationStrategyApplied());

            // Update the existing entity with new data from the DTO.
            // The mapper handles merging relevant fields.
            customerMapper.updateEntityFromDto(customerDTO, existingCustomer);
            processedCustomer = customerRepository.save(existingCustomer); // Persist changes

            // Publish an event indicating a customer profile update.
            // This allows other microservices or event consumers to react to the change.
            eventPublisher.publishEvent(new CustomerProfileUpdatedEvent(this,
                    processedCustomer.getCustomerId(), "Offermart", "Attributes updated via deduplication"));
            log.info("Customer profile with ID {} updated successfully via deduplication.", processedCustomer.getCustomerId());

        } else {
            // If no duplicate is found, create a new customer profile.
            log.info("No duplicate found for PAN: {}, Mobile: {}. Creating a new customer profile.",
                    customerDTO.getPanNumber(), customerDTO.getMobileNumber());

            Customer newCustomer = customerMapper.toEntity(customerDTO);
            // Generate a unique customer ID for the new CDP customer profile.
            // This ID serves as the primary business key for the customer in CDP.
            String newCdpCustomerId = "CDP-" + UUID.randomUUID().toString();
            newCustomer.setCustomerId(newCdpCustomerId);

            processedCustomer = customerRepository.save(newCustomer); // Persist the new customer

            // Publish an event indicating a new customer creation.
            eventPublisher.publishEvent(new CustomerCreatedEvent(this,
                    processedCustomer.getCustomerId(), "Offermart"));
            log.info("New customer profile created with ID: {}", processedCustomer.getCustomerId());
        }

        // Return the DTO representation of the processed (created or updated) customer.
        return customerMapper.toDto(processedCustomer);
    }

    /**
     * Retrieves a single customer profile by its unique CDP customer ID.
     * This method provides a single profile view of the customer.
     *
     * @param customerId The unique identifier of the customer in CDP (e.g., "CDP-UUID").
     * @return The CustomerDTO representing the found customer profile.
     * @throws CustomerNotFoundException If no customer is found with the given ID,
     *                                   indicating the requested profile does not exist.
     */
    @Transactional(readOnly = true) // Read-only transaction for performance optimization
    public CustomerDTO getCustomerProfile(String customerId) {
        log.debug("Attempting to retrieve customer profile for ID: {}", customerId);
        Customer customer = customerRepository.findByCustomerId(customerId)
                .orElseThrow(() -> {
                    log.warn("Customer not found for ID: {}", customerId);
                    return new CustomerNotFoundException("Customer with ID " + customerId + " not found.");
                });
        log.info("Customer profile retrieved successfully for ID: {}", customerId);
        return customerMapper.toDto(customer);
    }

    /**
     * Updates specific attributes of an existing customer profile.
     * This method allows for partial updates based on a map of attribute names and their new values.
     * It uses reflection to dynamically set fields, providing flexibility for attribute updates.
     *
     * @param customerId The unique identifier of the customer to update.
     * @param attributes A map where keys are attribute names (expected to match Customer entity field names)
     *                   and values are the new values for those attributes.
     * @return The CustomerDTO representing the updated customer profile.
     * @throws CustomerNotFoundException If no customer is found with the given ID.
     * @throws IllegalArgumentException If an attribute name in the map does not correspond to a valid field
     *                                  in the Customer entity.
     * @throws RuntimeException If there's an unexpected error during attribute update (e.g., reflection issues).
     */
    @Transactional
    public CustomerDTO updateCustomerAttributes(String customerId, Map<String, Object> attributes) {
        log.info("Attempting to update attributes for customer ID: {}. Attributes: {}", customerId, attributes.keySet());

        Customer existingCustomer = customerRepository.findByCustomerId(customerId)
                .orElseThrow(() -> {
                    log.warn("Customer not found for ID: {} during attribute update.", customerId);
                    return new CustomerNotFoundException("Customer with ID " + customerId + " not found.");
                });

        boolean attributesChanged = false;
        for (Map.Entry<String, Object> entry : attributes.entrySet()) {
            String attributeName = entry.getKey();
            Object newValue = entry.getValue();

            try {
                // Use reflection to set the field value dynamically.
                // This allows for generic attribute updates without specific setter methods for each field.
                Field field = Customer.class.getDeclaredField(attributeName);
                field.setAccessible(true); // Allow access to private fields

                Object oldValue = field.get(existingCustomer);

                // Only update if the new value is different from the old value to avoid unnecessary database writes.
                if (newValue != null && !newValue.equals(oldValue)) {
                    field.set(existingCustomer, newValue);
                    attributesChanged = true;
                    log.debug("Updated attribute '{}' for customer {}: Old='{}', New='{}'",
                            attributeName, customerId, oldValue, newValue);
                } else if (newValue == null && oldValue != null) {
                    // Handle case where new value is null and old value is not, effectively clearing the attribute.
                    field.set(existingCustomer, null);
                    attributesChanged = true;
                    log.debug("Cleared attribute '{}' for customer {}: Old='{}', New='null'",
                            attributeName, customerId, oldValue);
                }

            } catch (NoSuchFieldException e) {
                log.error("Attempted to update non-existent attribute '{}' for customer ID: {}. Please check attribute name.", attributeName, customerId);
                throw new IllegalArgumentException("Invalid attribute name: " + attributeName + ". Attribute does not exist in Customer entity.", e);
            } catch (IllegalAccessException e) {
                log.error("Failed to access attribute '{}' for customer ID: {}. Check field accessibility.", attributeName, customerId, e);
                throw new RuntimeException("Error updating customer attribute: " + attributeName + ". Access denied.", e);
            }
        }

        if (attributesChanged) {
            Customer updatedCustomer = customerRepository.save(existingCustomer); // Persist changes
            // Publish an event indicating that specific attributes of a customer profile have been updated.
            eventPublisher.publishEvent(new CustomerProfileUpdatedEvent(this,
                    updatedCustomer.getCustomerId(), "Internal", "Specific attributes updated: " + attributes.keySet()));
            log.info("Customer profile with ID {} attributes updated successfully.", updatedCustomer.getCustomerId());
            return customerMapper.toDto(updatedCustomer);
        } else {
            log.info("No attributes changed for customer ID: {}. Skipping database save.", customerId);
            return customerMapper.toDto(existingCustomer); // Return current state if no changes were applied
        }
    }

    /**
     * Deletes a customer profile by its unique CDP customer ID.
     * In a production CDP, actual deletion might be replaced by soft-deletion
     * or archival processes to maintain historical data integrity and audit trails.
     * For this implementation, it performs a hard delete.
     *
     * @param customerId The unique identifier of the customer to delete.
     * @throws CustomerNotFoundException If no customer is found with the given ID,
     *                                   indicating the profile to be deleted does not exist.
     */
    @Transactional
    public void deleteCustomerProfile(String customerId) {
        log.info("Attempting to delete customer profile for ID: {}", customerId);
        Customer customer = customerRepository.findByCustomerId(customerId)
                .orElseThrow(() -> {
                    log.warn("Customer not found for ID: {} during deletion attempt.", customerId);
                    return new CustomerNotFoundException("Customer with ID " + customerId + " not found for deletion.");
                });

        customerRepository.delete(customer); // Perform the deletion
        // Optionally, publish a CustomerDeletedEvent to notify other services
        // eventPublisher.publishEvent(new CustomerDeletedEvent(this, customerId, "Internal"));
        log.info("Customer profile with ID {} deleted successfully.", customerId);
    }
}
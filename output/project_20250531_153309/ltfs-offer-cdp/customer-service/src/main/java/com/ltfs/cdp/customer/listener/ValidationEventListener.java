package com.ltfs.cdp.customer.listener;

import com.ltfs.cdp.customer.event.CustomerDataValidatedEvent;
import com.ltfs.cdp.customer.model.Customer;
import com.ltfs.cdp.customer.dto.CustomerDTO;
import com.ltfs.cdp.customer.service.DeduplicationService;
import com.ltfs.cdp.customer.service.CustomerService;
import com.ltfs.cdp.customer.exception.DeduplicationException;
import com.ltfs.cdp.customer.exception.CustomerPersistenceException;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.context.event.EventListener;
import org.springframework.stereotype.Component;
import org.springframework.transaction.annotation.Transactional;

/**
 * ValidationEventListener is a Spring component that listens for
 * {@link CustomerDataValidatedEvent}s. Upon receiving such an event,
 * it orchestrates the subsequent steps of customer data processing,
 * specifically deduplication and persistence into the Customer Data Platform (CDP).
 *
 * This listener acts as a bridge between the initial data validation stage
 * and the core customer profile management functionalities.
 */
@Component
public class ValidationEventListener {

    private static final Logger log = LoggerFactory.getLogger(ValidationEventListener.class);

    private final DeduplicationService deduplicationService;
    private final CustomerService customerService;

    /**
     * Constructs a new ValidationEventListener with necessary service dependencies.
     * Spring's dependency injection will automatically provide instances of
     * {@link DeduplicationService} and {@link CustomerService}.
     *
     * @param deduplicationService The service responsible for applying deduplication logic.
     * @param customerService The service responsible for persisting customer data.
     */
    public ValidationEventListener(DeduplicationService deduplicationService, CustomerService customerService) {
        this.deduplicationService = deduplicationService;
        this.customerService = customerService;
    }

    /**
     * Handles the {@link CustomerDataValidatedEvent}. This method is automatically
     * invoked by Spring's event mechanism when a {@code CustomerDataValidatedEvent}
     * is published.
     *
     * The process involves:
     * 1. Logging the reception of the event.
     * 2. Calling the {@link DeduplicationService} to process the validated customer data.
     *    This step applies complex deduplication rules, including checking against
     *    the 'live book' (Customer 360) and specific logic for 'Top-up' loan offers.
     *    The deduplication service returns a {@link Customer} entity ready for persistence,
     *    or {@code null} if the data is identified as a duplicate that should be ignored.
     * 3. If a customer entity is returned by the deduplication service, it is then
     *    persisted using the {@link CustomerService}. This handles both new customer
     *    creation and updates to existing customer profiles.
     * 4. Comprehensive error handling is in place to catch and log exceptions
     *    that may occur during deduplication or persistence, ensuring the listener
     *    remains robust.
     *
     * The {@code @Transactional} annotation ensures that the entire operation
     * (deduplication and persistence) is atomic. If any part of this process fails,
     * the transaction will be rolled back, maintaining data consistency.
     *
     * @param event The {@link CustomerDataValidatedEvent} containing the validated
     *              {@link CustomerDTO} and a correlation ID for tracing.
     */
    @EventListener
    @Transactional
    public void handleCustomerDataValidatedEvent(CustomerDataValidatedEvent event) {
        CustomerDTO validatedCustomerData = event.getCustomerData();
        String correlationId = event.getCorrelationId();

        log.info("Received CustomerDataValidatedEvent for correlationId: {}. Initiating deduplication and persistence for customer data.", correlationId);

        try {
            // Step 1: Perform deduplication on the validated customer data.
            // The deduplication service determines if the customer is new, an update,
            // or a duplicate to be ignored based on predefined rules (e.g., PAN, Mobile, Loan Type).
            Customer dedupedCustomer = deduplicationService.processCustomerForDeduplication(validatedCustomerData);

            if (dedupedCustomer == null) {
                // If the deduplication service returns null, it signifies that the incoming
                // customer data was identified as a duplicate that should not be persisted
                // or update an existing profile (e.g., specific Top-up loan rules).
                log.info("Customer data for correlationId: {} was identified as a duplicate to be ignored or processed elsewhere by deduplication service. No persistence needed.", correlationId);
                return; // Exit the method as no further persistence is required for this event.
            }

            // Step 2: Persist the deduped customer data.
            // This method handles both saving new customer records and updating existing ones.
            Customer savedCustomer = customerService.saveOrUpdateCustomer(dedupedCustomer);
            log.info("Successfully processed and persisted customer with CDP ID: {} (Offermart ID: {}) for correlationId: {}. Deduplication Status: {}",
                     savedCustomer.getCdpCustomerId(), savedCustomer.getOffermartCustomerId(), correlationId, savedCustomer.getDeduplicationStatus());

        } catch (DeduplicationException e) {
            // Catch specific exceptions related to the deduplication process.
            log.error("Deduplication failed for correlationId: {}. Error: {}", correlationId, e.getMessage(), e);
            // Depending on business requirements, a failure event could be published here,
            // or the event could be routed to a dead-letter queue for manual review.
        } catch (CustomerPersistenceException e) {
            // Catch specific exceptions related to the customer persistence process.
            log.error("Customer persistence failed after deduplication for correlationId: {}. Error: {}", correlationId, e.getMessage(), e);
            // Similar error handling considerations as for DeduplicationException.
        } catch (Exception e) {
            // Catch any other unexpected exceptions to prevent the application from crashing
            // and ensure proper logging for debugging.
            log.error("An unexpected error occurred while processing CustomerDataValidatedEvent for correlationId: {}. Error: {}", correlationId, e.getMessage(), e);
        }
    }
}
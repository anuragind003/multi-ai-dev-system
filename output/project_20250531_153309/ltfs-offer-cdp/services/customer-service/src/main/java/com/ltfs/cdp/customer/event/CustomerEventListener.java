package com.ltfs.cdp.customer.event;

import com.ltfs.cdp.customer.service.CustomerService;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.context.event.EventListener;
import org.springframework.stereotype.Component;
import org.springframework.transaction.annotation.Transactional;

/**
 * CustomerEventListener
 *
 * <p>Listens for various customer-related events within the CDP system.
 * This component is responsible for triggering subsequent actions like
 * customer profile updates, deduplication processes, or data validation
 * based on incoming events from other services (e.g., data ingestion from Offermart).</p>
 *
 * <p>It acts as a bridge between event publication and the core business logic
 * handled by the {@link CustomerService}.</p>
 */
@Component
public class CustomerEventListener {

    private static final Logger log = LoggerFactory.getLogger(CustomerEventListener.class);

    private final CustomerService customerService;

    /**
     * Constructs a new CustomerEventListener with the given CustomerService.
     * Spring automatically injects the {@link CustomerService} bean.
     *
     * @param customerService The service responsible for customer-related business logic,
     *                        including deduplication and profile management.
     */
    public CustomerEventListener(CustomerService customerService) {
        this.customerService = customerService;
    }

    /**
     * <p>Listens for {@link CustomerDataIngestedEvent}.</p>
     *
     * <p>This event is typically published when new customer data has been successfully
     * ingested into the CDP system from an external source like Offermart.
     * Upon receiving this event, the listener triggers the deduplication process
     * and potential customer profile updates for the ingested customer.</p>
     *
     * <p>The method is marked {@code @Transactional} to ensure that all operations
     * triggered by this event (e.g., multiple database writes within the service layer)
     * are atomic. If any part of the processing fails, the transaction will roll back.</p>
     *
     * @param event The {@link CustomerDataIngestedEvent} containing details of the ingested customer,
     *              such as customer ID and the source system.
     */
    @EventListener
    @Transactional
    public void handleCustomerDataIngestedEvent(CustomerDataIngestedEvent event) {
        // Log the reception of the event for auditing and debugging purposes.
        log.info("Received CustomerDataIngestedEvent for customer ID: '{}' from source system: '{}'. Initiating processing...",
                event.customerId(), event.sourceSystem());

        try {
            // Step 1: Trigger the deduplication logic for the newly ingested customer data.
            // This involves comparing the new data against existing customer profiles in the 'live book' (Customer 360).
            // The CustomerService will handle the complex deduplication rules, including product-specific logic.
            customerService.processCustomerForDeduplication(event.customerId(), event.sourceSystem());

            // Step 2: After (or as part of) deduplication, update the customer's single profile view.
            // This might involve merging data from different sources, updating customer scores,
            // or linking the new data to an existing master customer profile.
            customerService.updateCustomerProfile(event.customerId());

            // Log successful processing.
            log.info("Successfully processed CustomerDataIngestedEvent for customer ID: '{}'.", event.customerId());

        } catch (Exception e) {
            // Log the error with full stack trace for detailed debugging.
            // This catch block ensures that even if an error occurs during processing,
            // the application doesn't crash and the error is recorded.
            log.error("Error processing CustomerDataIngestedEvent for customer ID: '{}'. Error: {}",
                    event.customerId(), e.getMessage(), e);

            // In a production environment, consider more advanced error handling strategies:
            // - Publishing a "CustomerProcessingFailedEvent" to a dead-letter queue for manual review or retry.
            // - Using Spring's @Retryable annotation or a retry mechanism for transient errors.
            // - Implementing a circuit breaker pattern for external service failures.
            // - Throwing a custom exception to be handled by a global exception handler.
            // For this example, simple logging is sufficient, but re-throwing a custom runtime exception
            // allows for consistent error handling upstream (e.g., by Spring's transaction manager).
            throw new CustomerEventProcessingException("Failed to process customer data for ID: " + event.customerId(), e);
        }
    }

    /**
     * <p>Listens for {@link CustomerProfileUpdatedEvent}.</p>
     *
     * <p>This event could be published by other internal services when a customer's
     * profile attributes (e.g., address, contact information, loan status) have been updated.
     * Receiving this event might trigger a re-evaluation for offer eligibility,
     * a lightweight profile consistency check, or a re-indexing of customer data.</p>
     *
     * @param event The {@link CustomerProfileUpdatedEvent} containing the ID of the customer
     *              whose profile has been updated.
     */
    @EventListener
    public void handleCustomerProfileUpdatedEvent(CustomerProfileUpdatedEvent event) {
        log.info("Received CustomerProfileUpdatedEvent for customer ID: '{}'. Initiating profile re-evaluation...",
                event.customerId());

        try {
            // Example: Re-evaluate customer's eligibility for certain offers based on updated profile.
            // Or trigger a specific service method to re-validate the profile data.
            // The CustomerService will determine the exact actions needed for a profile update.
            customerService.updateCustomerProfile(event.customerId());

            log.info("Successfully processed CustomerProfileUpdatedEvent for customer ID: '{}'.", event.customerId());
        } catch (Exception e) {
            log.error("Error processing CustomerProfileUpdatedEvent for customer ID: '{}'. Error: {}",
                    event.customerId(), e.getMessage(), e);
            // Re-throw a custom runtime exception for consistent error handling.
            throw new CustomerEventProcessingException("Failed to re-evaluate customer profile for ID: " + event.customerId(), e);
        }
    }

    // --- Assumed External Dependencies for Compilation ---
    // For this CustomerEventListener.java file to compile and run, the following classes
    // are assumed to be defined elsewhere in the project (e.g., in their own .java files):
    //
    // 1. com.ltfs.cdp.customer.service.CustomerService:
    //    public interface CustomerService {
    //        void processCustomerForDeduplication(String customerId, String sourceSystem);
    //        void updateCustomerProfile(String customerId);
    //    }
    //
    // 2. com.ltfs.cdp.customer.event.CustomerDataIngestedEvent:
    //    public record CustomerDataIngestedEvent(String customerId, String sourceSystem) {}
    //    (Or a similar POJO class with customerId and sourceSystem properties and getters)
    //
    // 3. com.ltfs.cdp.customer.event.CustomerProfileUpdatedEvent:
    //    public record CustomerProfileUpdatedEvent(String customerId) {}
    //    (Or a similar POJO class with a customerId property and getter)
    //
    // 4. com.ltfs.cdp.customer.event.CustomerEventProcessingException:
    //    public class CustomerEventProcessingException extends RuntimeException {
    //        public CustomerEventProcessingException(String message) { super(message); }
    //        public CustomerEventProcessingException(String message, Throwable cause) { super(message, cause); }
    //    }
}
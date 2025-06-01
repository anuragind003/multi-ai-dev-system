package com.ltfs.cdp.customer.event;

import com.ltfs.cdp.customer.model.dto.CustomerValidatedDataDTO;
import org.springframework.context.ApplicationEvent;

/**
 * Represents an event that is triggered after customer data has successfully
 * passed initial column-level validation within the CDP system.
 *
 * This event serves as a signal that the validated customer data is now ready
 * for subsequent processing steps, specifically the deduplication logic.
 *
 * The event carries the {@link CustomerValidatedDataDTO} as its payload,
 * encapsulating all the necessary customer attributes that have been
 * confirmed as valid and consistent.
 *
 * This class extends {@link ApplicationEvent} to integrate with Spring's
 * event publishing and listening mechanism, allowing for a decoupled
 * and asynchronous flow between validation and deduplication components.
 */
public class CustomerDataValidatedEvent extends ApplicationEvent {

    /**
     * The validated customer data payload.
     * This DTO contains all the customer attributes that have passed
     * the initial validation checks and are now prepared for deduplication.
     * It is crucial that this DTO contains sufficient information
     * for the deduplication process to identify and match customers.
     */
    private final CustomerValidatedDataDTO customerValidatedData;

    /**
     * Constructs a new {@code CustomerDataValidatedEvent}.
     *
     * @param source The object on which the event initially occurred.
     *               Typically, this would be the service component responsible
     *               for performing the customer data validation.
     * @param customerValidatedData The {@link CustomerValidatedDataDTO}
     *                              containing the customer data that has been
     *                              successfully validated. This payload is
     *                              immutable once the event is created.
     * @throws IllegalArgumentException if {@code source} is null, as required by {@link ApplicationEvent}.
     */
    public CustomerDataValidatedEvent(Object source, CustomerValidatedDataDTO customerValidatedData) {
        super(source); // Call the superclass constructor with the event source
        // It's good practice to ensure the payload is not null if it's critical for event processing.
        // For this event, validated customer data is essential.
        if (customerValidatedData == null) {
            throw new IllegalArgumentException("Validated customer data cannot be null for CustomerDataValidatedEvent.");
        }
        this.customerValidatedData = customerValidatedData;
    }

    /**
     * Retrieves the validated customer data payload associated with this event.
     *
     * @return The {@link CustomerValidatedDataDTO} instance containing the
     *         customer information that has passed validation.
     */
    public CustomerValidatedDataDTO getCustomerValidatedData() {
        return customerValidatedData;
    }

    /**
     * Provides a concise string representation of this event, primarily for
     * logging and debugging purposes.
     * It includes the class name of the event source and the string representation
     * of the customer validated data payload.
     *
     * @return A string representation of the {@code CustomerDataValidatedEvent}.
     */
    @Override
    public String toString() {
        return "CustomerDataValidatedEvent{" +
               "source=" + (getSource() != null ? getSource().getClass().getSimpleName() : "UNKNOWN_SOURCE") +
               ", customerValidatedData=" + customerValidatedData + // Rely on CustomerValidatedDataDTO's toString()
               '}';
    }
}
package com.ltfs.cdp.common.event;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.LocalDateTime;
import java.util.UUID;

/**
 * Represents an event indicating that customer data has been updated in the CDP system.
 * This event is designed to be consumed by other microservices to react to customer profile changes,
 * ensuring data consistency and enabling real-time processing for offers and campaigns.
 *
 * <p>The event carries essential information about the update, including a unique event ID,
 * the timestamp of the update, the ID of the customer affected, and a snapshot of the
 * updated customer details.
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class CustomerUpdatedEvent {

    /**
     * A unique identifier for this specific event instance.
     * Useful for tracing and idempotency in event processing across distributed systems.
     */
    private UUID eventId;

    /**
     * The timestamp when this event was generated, indicating when the customer data update occurred.
     * This helps in maintaining the order of events and for auditing purposes.
     */
    private LocalDateTime timestamp;

    /**
     * The unique identifier of the customer whose data has been updated.
     * This ID serves as the primary key for identifying the customer in the CDP.
     */
    private String customerId; // Assuming customerId is a String (e.g., UUID or internal system ID)

    /**
     * A payload containing the updated customer details.
     * This provides a snapshot of the customer's profile after the update,
     * allowing consumers to react without necessarily querying the database immediately.
     * It should contain key attributes relevant for downstream processing (e.g., name, contact info, status).
     */
    private CustomerPayload updatedCustomerDetails;

    /**
     * Static nested class representing the payload of updated customer details.
     * This DTO should contain the most relevant and frequently used customer attributes
     * that are part of the customer's single profile view.
     *
     * <p>For a real-world scenario, this DTO might be a separate class in a `dto` package
     * within the `common` module or a `customer` specific module. For the purpose of this
     * single file generation, it's included as a static nested class.
     */
    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class CustomerPayload {
        // Example fields. These should reflect the core attributes of a customer in the CDP
        // that are typically updated or are crucial for downstream processing (e.g., offer eligibility, deduplication).

        /**
         * The full name of the customer.
         */
        private String customerName;

        /**
         * The primary mobile number of the customer.
         */
        private String mobileNumber;

        /**
         * The primary email ID of the customer.
         */
        private String emailId;

        /**
         * The Permanent Account Number (PAN) of the customer, a key identifier in Indian financial services.
         */
        private String panNumber;

        /**
         * The Aadhaar number of the customer, another key identifier in India.
         */
        private String aadhaarNumber;

        /**
         * The current status of the customer in the CDP (e.g., "Active", "Inactive", "Deduplicated", "Blocked").
         */
        private String customerStatus;

        /**
         * Any additional remarks or notes related to the customer update.
         */
        private String remarks;

        // Add other relevant fields as per the Customer entity definition in CDP
        // e.g., address, dateOfBirth, loanProductEligibility, CIBIL score, etc.
        // private AddressDto address;
        // private LocalDate dateOfBirth;
        // private String cibilScore;
    }
}
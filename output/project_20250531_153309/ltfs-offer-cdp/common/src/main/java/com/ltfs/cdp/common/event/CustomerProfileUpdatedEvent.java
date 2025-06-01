package com.ltfs.cdp.common.event;

import java.io.Serializable;
import java.time.Instant;
import java.util.Objects;
import java.util.UUID;

/**
 * Represents an event indicating that a customer's profile has been updated.
 * This event is designed to be published to a message broker (e.g., Kafka)
 * to notify other services within the LTFS Offer CDP system about changes
 * to customer data.
 *
 * <p>Consumers of this event can react by fetching the latest customer profile
 * from the Customer 360 system or by updating their local caches/views,
 * ensuring a consistent single profile view across the platform.</p>
 *
 * <p>This class is immutable, ensuring that event data remains consistent
 * once created, which is a best practice for event-driven architectures.</p>
 */
public class CustomerProfileUpdatedEvent implements Serializable {

    private static final long serialVersionUID = 1L; // Recommended for Serializable classes

    /**
     * A unique identifier for this specific event instance.
     * This ID helps in tracing the event through the system and can be used
     * for deduplication of events at the consumer side if necessary.
     */
    private final String eventId;

    /**
     * The unique identifier of the customer whose profile was updated.
     * This ID is crucial for identifying the affected customer across the CDP system
     * and for triggering subsequent actions like deduplication or offer finalization.
     */
    private final String customerId;

    /**
     * The timestamp when the customer profile update occurred and this event was generated.
     * Represented as an {@link Instant} for precise, timezone-agnostic timekeeping,
     * which is ideal for distributed systems.
     */
    private final Instant timestamp;

    /**
     * The system or service that initiated the customer profile update.
     * Examples include "Offermart", "Customer360", "DeduplicationService", etc.
     * This provides valuable context for event consumers and for auditing purposes.
     */
    private final String sourceSystem;

    /**
     * Constructs a new CustomerProfileUpdatedEvent with a newly generated event ID
     * and the current timestamp.
     *
     * @param customerId The unique identifier of the customer whose profile was updated.
     *                   Must not be null or empty.
     * @param sourceSystem The system that initiated the customer profile update.
     *                     Must not be null or empty.
     * @throws IllegalArgumentException if {@code customerId} or {@code sourceSystem} is null or empty.
     */
    public CustomerProfileUpdatedEvent(String customerId, String sourceSystem) {
        this(UUID.randomUUID().toString(), customerId, Instant.now(), sourceSystem);
    }

    /**
     * Full constructor for CustomerProfileUpdatedEvent.
     * This constructor allows for explicit control over all event properties,
     * which can be useful for testing or specific scenarios where event ID or timestamp
     * need to be predefined (e.g., replaying events).
     *
     * @param eventId A unique identifier for this event. Must not be null or empty.
     * @param customerId The unique identifier of the customer whose profile was updated.
     *                   Must not be null or empty.
     * @param timestamp The exact time when the event occurred. Must not be null.
     * @param sourceSystem The system that initiated the customer profile update.
     *                     Must not be null or empty.
     * @throws IllegalArgumentException if any required parameter is null or empty.
     */
    public CustomerProfileUpdatedEvent(String eventId, String customerId, Instant timestamp, String sourceSystem) {
        if (eventId == null || eventId.trim().isEmpty()) {
            throw new IllegalArgumentException("Event ID cannot be null or empty.");
        }
        if (customerId == null || customerId.trim().isEmpty()) {
            throw new IllegalArgumentException("Customer ID cannot be null or empty.");
        }
        if (timestamp == null) {
            throw new IllegalArgumentException("Timestamp cannot be null.");
        }
        if (sourceSystem == null || sourceSystem.trim().isEmpty()) {
            throw new IllegalArgumentException("Source system cannot be null or empty.");
        }

        this.eventId = eventId;
        this.customerId = customerId;
        this.timestamp = timestamp;
        this.sourceSystem = sourceSystem;
    }

    /**
     * Returns the unique identifier of this event instance.
     * @return The event ID.
     */
    public String getEventId() {
        return eventId;
    }

    /**
     * Returns the unique identifier of the customer whose profile was updated.
     * @return The customer ID.
     */
    public String getCustomerId() {
        return customerId;
    }

    /**
     * Returns the timestamp when this event occurred.
     * @return The event timestamp as an {@link Instant}.
     */
    public Instant getTimestamp() {
        return timestamp;
    }

    /**
     * Returns the name of the system that initiated the customer profile update.
     * @return The source system name.
     */
    public String getSourceSystem() {
        return sourceSystem;
    }

    /**
     * Compares this event to the specified object. The result is true if and only if
     * the argument is not null and is a CustomerProfileUpdatedEvent object that has
     * the same eventId, customerId, timestamp, and sourceSystem as this object.
     *
     * @param o The object to compare this CustomerProfileUpdatedEvent against.
     * @return true if the given object represents an equivalent CustomerProfileUpdatedEvent, false otherwise.
     */
    @Override
    public boolean equals(Object o) {
        if (this == o) return true;
        if (o == null || getClass() != o.getClass()) return false;
        CustomerProfileUpdatedEvent that = (CustomerProfileUpdatedEvent) o;
        return Objects.equals(eventId, that.eventId) &&
               Objects.equals(customerId, that.customerId) &&
               Objects.equals(timestamp, that.timestamp) &&
               Objects.equals(sourceSystem, that.sourceSystem);
    }

    /**
     * Returns a hash code value for the object. This method is supported for the benefit of
     * hash tables such as those provided by {@link java.util.HashMap}.
     *
     * @return A hash code value for this object.
     */
    @Override
    public int hashCode() {
        return Objects.hash(eventId, customerId, timestamp, sourceSystem);
    }

    /**
     * Returns a string representation of the object.
     * This method is useful for logging and debugging purposes.
     *
     * @return A string representation of this CustomerProfileUpdatedEvent.
     */
    @Override
    public String toString() {
        return "CustomerProfileUpdatedEvent{" +
               "eventId='" + eventId + '\'' +
               ", customerId='" + customerId + '\'' +
               ", timestamp=" + timestamp +
               ", sourceSystem='" + sourceSystem + '\'' +
               '}';
    }
}
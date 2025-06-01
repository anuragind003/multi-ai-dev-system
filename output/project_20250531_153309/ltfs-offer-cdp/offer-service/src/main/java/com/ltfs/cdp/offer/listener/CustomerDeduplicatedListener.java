package com.ltfs.cdp.offer.listener;

import com.ltfs.cdp.offer.dto.CustomerDeduplicationEvent;
import com.ltfs.cdp.offer.service.OfferService;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.amqp.AmqpRejectAndDontRequeueException;
import org.springframework.amqp.rabbit.annotation.RabbitListener;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Component;

/**
 * Listener for customer deduplication events.
 * This component consumes messages from a dedicated queue,
 * processes customer deduplication outcomes, and triggers
 * subsequent actions on associated offers, such as finalization
 * or adjustment.
 */
@Component
public class CustomerDeduplicatedListener {

    private static final Logger logger = LoggerFactory.getLogger(CustomerDeduplicatedListener.class);

    private final OfferService offerService;

    /**
     * Constructs a CustomerDeduplicatedListener with the necessary OfferService.
     * Spring's dependency injection automatically provides the OfferService instance.
     *
     * @param offerService The service responsible for managing and adjusting offers.
     */
    @Autowired
    public CustomerDeduplicatedListener(OfferService offerService) {
        this.offerService = offerService;
    }

    /**
     * Listens for messages on the 'customer.deduplication.events' queue.
     * Each message is expected to be a CustomerDeduplicationEvent object,
     * containing details about the deduplication outcome for a customer.
     *
     * Upon receiving an event, it delegates the processing to the OfferService
     * to handle the impact on related offers.
     *
     * @param event The CustomerDeduplicationEvent object received from the queue.
     *              This object should contain information like original customer ID,
     *              deduplicated customer ID (if applicable), and the deduplication status.
     * @throws AmqpRejectAndDontRequeueException If an unrecoverable error occurs during
     *                                           message processing, the message is rejected
     *                                           and not re-queued, potentially moving it to a DLQ.
     */
    @RabbitListener(queues = "${app.rabbitmq.queues.customer-deduplication-events}")
    public void handleCustomerDeduplicationEvent(CustomerDeduplicationEvent event) {
        logger.info("Received customer deduplication event: {}", event);

        if (event == null) {
            logger.warn("Received null customer deduplication event. Skipping processing.");
            // Reject and don't requeue to prevent infinite loops for malformed messages
            throw new AmqpRejectAndDontRequeueException("Received null event.");
        }

        // Basic validation of essential fields in the event
        if (event.getOriginalCustomerId() == null || event.getOriginalCustomerId().isEmpty()) {
            logger.error("Customer deduplication event missing original customer ID: {}", event);
            throw new AmqpRejectAndDontRequeueException("Event missing original customer ID.");
        }
        if (event.getStatus() == null) {
            logger.error("Customer deduplication event missing status: {}", event);
            throw new AmqpRejectAndDontRequeueException("Event missing deduplication status.");
        }

        try {
            // Delegate the business logic for offer adjustment/finalization to the OfferService.
            // The service will determine the appropriate action based on the deduplication status
            // (e.g., mark offers as duplicate, transfer offers, invalidate offers).
            offerService.handleDeduplicatedCustomer(event);
            logger.info("Successfully processed deduplication event for original customer ID: {}", event.getOriginalCustomerId());

        } catch (Exception e) {
            // Log the error and re-throw as AmqpRejectAndDontRequeueException
            // This ensures that the message is not re-queued indefinitely on transient errors
            // and can be moved to a Dead Letter Queue (DLQ) for further investigation.
            logger.error("Error processing customer deduplication event for original customer ID {}: {}",
                    event.getOriginalCustomerId(), e.getMessage(), e);
            throw new AmqpRejectAndDontRequeueException("Failed to process customer deduplication event: " + e.getMessage(), e);
        }
    }
}

/*
 * DTO for CustomerDeduplicationEvent (example structure - actual DTO should be defined elsewhere)
 *
 * package com.ltfs.cdp.offer.dto;
 *
 * import java.io.Serializable;
 * import java.util.List;
 * import java.util.Objects;
 *
 * public class CustomerDeduplicationEvent implements Serializable {
 *     private String originalCustomerId;
 *     private String dedupedCustomerId; // The ID of the customer it was matched/merged with
 *     private DeduplicationStatus status; // Enum: MATCHED, NO_MATCH, MERGED, REMOVED
 *     private List<String> affectedOfferIds; // Optional: IDs of offers directly impacted
 *     private String correlationId; // For tracing
 *
 *     // Enum for deduplication status
 *     public enum DeduplicationStatus {
 *         MATCHED,      // Original customer matched with an existing deduped customer
 *         NO_MATCH,     // Original customer is unique
 *         MERGED,       // Original customer record was merged into another
 *         REMOVED       // Original customer record was removed (e.g., duplicate top-up)
 *     }
 *
 *     // Getters, Setters, Constructors, equals, hashCode, toString
 *     public CustomerDeduplicationEvent() {}
 *
 *     public CustomerDeduplicationEvent(String originalCustomerId, String dedupedCustomerId, DeduplicationStatus status, List<String> affectedOfferIds, String correlationId) {
 *         this.originalCustomerId = originalCustomerId;
 *         this.dedupedCustomerId = dedupedCustomerId;
 *         this.status = status;
 *         this.affectedOfferIds = affectedOfferIds;
 *         this.correlationId = correlationId;
 *     }
 *
 *     public String getOriginalCustomerId() { return originalCustomerId; }
 *     public void setOriginalCustomerId(String originalCustomerId) { this.originalCustomerId = originalCustomerId; }
 *
 *     public String getDedupedCustomerId() { return dedupedCustomerId; }
 *     public void setDedupedCustomerId(String dedupedCustomerId) { this.dedupedCustomerId = dedupedCustomerId; }
 *
 *     public DeduplicationStatus getStatus() { return status; }
 *     public void setStatus(DeduplicationStatus status) { this.status = status; }
 *
 *     public List<String> getAffectedOfferIds() { return affectedOfferIds; }
 *     public void setAffectedOfferIds(List<String> affectedOfferIds) { this.affectedOfferIds = affectedOfferIds; }
 *
 *     public String getCorrelationId() { return correlationId; }
 *     public void setCorrelationId(String correlationId) { this.correlationId = correlationId; }
 *
 *     @Override
 *     public boolean equals(Object o) {
 *         if (this == o) return true;
 *         if (o == null || getClass() != o.getClass()) return false;
 *         CustomerDeduplicationEvent that = (CustomerDeduplicationEvent) o;
 *         return Objects.equals(originalCustomerId, that.originalCustomerId) &&
 *                Objects.equals(dedupedCustomerId, that.dedupedCustomerId) &&
 *                status == that.status &&
 *                Objects.equals(affectedOfferIds, that.affectedOfferIds) &&
 *                Objects.equals(correlationId, that.correlationId);
 *     }
 *
 *     @Override
 *     public int hashCode() {
 *         return Objects.hash(originalCustomerId, dedupedCustomerId, status, affectedOfferIds, correlationId);
 *     }
 *
 *     @Override
 *     public String toString() {
 *         return "CustomerDeduplicationEvent{" +
 *                "originalCustomerId='" + originalCustomerId + '\'' +
 *                ", dedupedCustomerId='" + dedupedCustomerId + '\'' +
 *                ", status=" + status +
 *                ", affectedOfferIds=" + affectedOfferIds +
 *                ", correlationId='" + correlationId + '\'' +
 *                '}';
 *     }
 * }
 */

/*
 * Interface for OfferService (example structure - actual service should be defined elsewhere)
 *
 * package com.ltfs.cdp.offer.service;
 *
 * import com.ltfs.cdp.offer.dto.CustomerDeduplicationEvent;
 * import org.springframework.stereotype.Service;
 *
 * public interface OfferService {
 *     void handleDeduplicatedCustomer(CustomerDeduplicationEvent event);
 * }
 */

/*
 * Example application.properties or application.yml configuration for RabbitMQ queue:
 *
 * application.properties:
 * app.rabbitmq.queues.customer-deduplication-events=customer.deduplication.events
 *
 * application.yml:
 * app:
 *   rabbitmq:
 *     queues:
 *       customer-deduplication-events: customer.deduplication.events
 */
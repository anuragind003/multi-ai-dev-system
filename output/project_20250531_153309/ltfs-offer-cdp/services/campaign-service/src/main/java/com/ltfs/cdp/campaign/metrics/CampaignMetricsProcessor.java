package com.ltfs.cdp.campaign.metrics;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;
import java.util.Optional;
import java.util.concurrent.ConcurrentHashMap; // For MockRepository
import java.util.Map; // For MockRepository

// --- Start of Mock/Placeholder Classes for direct runnability ---
// In a real project, these classes would reside in their respective packages (e.g., .model, .repository, .events)
// and be proper JPA entities, Spring Data repositories, and DTOs.

/**
 * Placeholder for CampaignMetrics entity.
 * In a real application, this would be a proper JPA @Entity with database mapping
 * (e.g., @Table, @Id, @Column, @Version for optimistic locking).
 * Using Lombok's @Data would simplify getters/setters.
 */
class CampaignMetrics {
    private String campaignId;
    private long offersSentCount;
    private long offersViewedCount;
    private long offersAcceptedCount;
    private long offersRejectedCount;
    private double clickThroughRate;
    private double conversionRate;
    private LocalDateTime lastUpdated;

    public CampaignMetrics(String campaignId) {
        this.campaignId = campaignId;
        this.offersSentCount = 0;
        this.offersViewedCount = 0;
        this.offersAcceptedCount = 0;
        this.offersRejectedCount = 0;
        this.clickThroughRate = 0.0;
        this.conversionRate = 0.0;
        this.lastUpdated = LocalDateTime.now();
    }

    // Getters and Setters
    public String getCampaignId() { return campaignId; }
    public void setCampaignId(String campaignId) { this.campaignId = campaignId; }
    public long getOffersSentCount() { return offersSentCount; }
    public void setOffersSentCount(long offersSentCount) { this.offersSentCount = offersSentCount; }
    public long getOffersViewedCount() { return offersViewedCount; }
    public void setOffersViewedCount(long offersViewedCount) { this.offersViewedCount = offersViewedCount; }
    public long getOffersAcceptedCount() { return offersAcceptedCount; }
    public void setOffersAcceptedCount(long offersAcceptedCount) { this.offersAcceptedCount = offersAcceptedCount; }
    public long getOffersRejectedCount() { return offersRejectedCount; }
    public void setOffersRejectedCount(long offersRejectedCount) { this.offersRejectedCount = offersRejectedCount; }
    public double getClickThroughRate() { return clickThroughRate; }
    public void setClickThroughRate(double clickThroughRate) { this.clickThroughRate = clickThroughRate; }
    public double getConversionRate() { return conversionRate; }
    public void setConversionRate(double conversionRate) { this.conversionRate = conversionRate; }
    public LocalDateTime getLastUpdated() { return lastUpdated; }
    public void setLastUpdated(LocalDateTime lastUpdated) { this.lastUpdated = lastUpdated; }

    /**
     * Recalculates click-through rate and conversion rate based on current counts.
     * Updates the lastUpdated timestamp.
     */
    public void updateRates() {
        if (this.offersSentCount > 0) {
            this.clickThroughRate = (double) this.offersViewedCount / this.offersSentCount * 100.0;
            this.conversionRate = (double) this.offersAcceptedCount / this.offersSentCount * 100.0;
        } else {
            // If no offers sent, rates are 0 to avoid division by zero
            this.clickThroughRate = 0.0;
            this.conversionRate = 0.0;
        }
        this.lastUpdated = LocalDateTime.now();
    }
}

/**
 * Placeholder for CampaignMetricsRepository interface.
 * In a real application, this would extend Spring Data JPA's JpaRepository
 * (e.g., `public interface CampaignMetricsRepository extends JpaRepository<CampaignMetrics, String>`).
 */
interface CampaignMetricsRepository {
    Optional<CampaignMetrics> findById(String campaignId);
    CampaignMetrics save(CampaignMetrics metrics);
}

/**
 * Mock implementation for CampaignMetricsRepository.
 * This is provided to make the CampaignMetricsProcessor directly runnable without a database.
 * In a real application, Spring Data JPA would provide the concrete implementation.
 */
@Service // Mark as a Spring component so it can be injected
class MockCampaignMetricsRepository implements CampaignMetricsRepository {
    // Using ConcurrentHashMap to simulate a thread-safe in-memory store
    private final Map<String, CampaignMetrics> store = new ConcurrentHashMap<>();

    @Override
    public Optional<CampaignMetrics> findById(String campaignId) {
        return Optional.ofNullable(store.get(campaignId));
    }

    @Override
    public CampaignMetrics save(CampaignMetrics metrics) {
        store.put(metrics.getCampaignId(), metrics);
        return metrics;
    }
}

/**
 * Base class for offer-related events.
 * In a real application, this would be in a separate 'events' package (e.g., `com.ltfs.cdp.campaign.events`).
 * DTOs for events might also use Lombok's @Data, @NoArgsConstructor, @AllArgsConstructor.
 */
class OfferEvent {
    private String campaignId;
    private String offerId;
    private String customerId;
    private LocalDateTime timestamp;

    public OfferEvent(String campaignId, String offerId, String customerId, LocalDateTime timestamp) {
        this.campaignId = campaignId;
        this.offerId = offerId;
        this.customerId = customerId;
        this.timestamp = timestamp;
    }

    // Getters
    public String getCampaignId() { return campaignId; }
    public String getOfferId() { return offerId; }
    public String getCustomerId() { return customerId; }
    public LocalDateTime getTimestamp() { return timestamp; }
}

/**
 * Event representing an offer being sent.
 * In a real application, this would be in a separate 'events' package.
 */
class OfferSentEvent extends OfferEvent {
    public OfferSentEvent(String campaignId, String offerId, String customerId, LocalDateTime timestamp) {
        super(campaignId, offerId, customerId, timestamp);
    }
}

/**
 * Event representing an interaction with an offer (viewed, accepted, rejected).
 * In a real application, this would be in a separate 'events' package.
 */
class OfferInteractionEvent extends OfferEvent {
    public enum InteractionType {
        VIEWED, ACCEPTED, REJECTED
    }
    private InteractionType interactionType;

    public OfferInteractionEvent(String campaignId, String offerId, String customerId, LocalDateTime timestamp, InteractionType interactionType) {
        super(campaignId, offerId, customerId, timestamp);
        this.interactionType = interactionType;
    }

    // Getter
    public InteractionType getInteractionType() { return interactionType; }
}
// --- End of Mock/Placeholder Classes ---


/**
 * Service component responsible for processing and aggregating campaign performance metrics.
 * This processor listens to various offer-related events and updates the corresponding
 * campaign metrics in the database.
 *
 * It handles events such as offers being sent, viewed, accepted, or rejected,
 * and calculates key performance indicators like click-through rate and conversion rate.
 *
 * This class is designed to be integrated into a Spring Boot application, typically
 * consuming events from a message broker (e.g., Kafka, RabbitMQ) via `@KafkaListener`
 * or `@RabbitListener`, or being called directly by other services.
 */
@Service
public class CampaignMetricsProcessor {

    private static final Logger log = LoggerFactory.getLogger(CampaignMetricsProcessor.class);

    private final CampaignMetricsRepository campaignMetricsRepository;

    /**
     * Constructs a CampaignMetricsProcessor with the necessary repository dependency.
     * Spring's dependency injection will automatically provide an instance of
     * CampaignMetricsRepository (e.g., the MockCampaignMetricsRepository in this setup,
     * or a Spring Data JPA repository in a full application).
     *
     * @param campaignMetricsRepository The repository for managing campaign metrics data.
     */
    @Autowired
    public CampaignMetricsProcessor(CampaignMetricsRepository campaignMetricsRepository) {
        this.campaignMetricsRepository = campaignMetricsRepository;
    }

    /**
     * Processes an event indicating that an offer has been sent as part of a campaign.
     * This method increments the 'offersSentCount' for the respective campaign.
     *
     * The operation is transactional to ensure atomicity: either the metrics are
     * updated successfully, or the entire operation is rolled back.
     *
     * @param event The OfferSentEvent containing campaign and offer details.
     * @throws RuntimeException if an error occurs during processing, allowing Spring
     *                          to handle transaction rollback.
     */
    @Transactional
    public void processOfferSent(OfferSentEvent event) {
        if (event == null || event.getCampaignId() == null || event.getCampaignId().isEmpty()) {
            log.warn("Received null or invalid OfferSentEvent. Skipping processing.");
            return;
        }

        String campaignId = event.getCampaignId();
        log.info("Processing OfferSentEvent for campaignId: {}", campaignId);

        try {
            // Retrieve existing metrics or create a new entry if none exists for the campaign.
            // Note on concurrency: In a high-concurrency environment, a simple findById then save
            // can lead to "lost updates" if multiple threads read the same old value, increment,
            // and then save. For robust counter increments, consider:
            // 1. Database-level optimistic locking (@Version field in CampaignMetrics entity).
            // 2. Database-level pessimistic locking (@Lock(LockModeType.PESSIMISTIC_WRITE) on repository findById).
            // 3. Custom JPA/SQL update query (e.g., UPDATE campaign_metrics SET offers_sent_count = offers_sent_count + 1 WHERE campaign_id = ?).
            // 4. Using a message queue with guaranteed ordering per campaign ID (e.g., Kafka with partitioned topics).
            CampaignMetrics metrics = campaignMetricsRepository.findById(campaignId)
                    .orElseGet(() -> {
                        log.info("No existing metrics found for campaignId: {}. Creating new entry.", campaignId);
                        return new CampaignMetrics(campaignId);
                    });

            metrics.setOffersSentCount(metrics.getOffersSentCount() + 1);
            metrics.updateRates(); // Recalculate rates (CTR, Conversion Rate) after count update
            campaignMetricsRepository.save(metrics); // Persist the updated metrics
            log.debug("Successfully updated metrics for campaignId: {}. Offers Sent: {}", campaignId, metrics.getOffersSentCount());
        } catch (Exception e) {
            log.error("Error processing OfferSentEvent for campaignId: {}. Error: {}", campaignId, e.getMessage(), e);
            // Re-throw as RuntimeException to trigger transaction rollback if configured
            throw new RuntimeException("Failed to process offer sent event for campaign " + campaignId, e);
        }
    }

    /**
     * Processes an event indicating an interaction with an offer (viewed, accepted, rejected).
     * This method updates the relevant interaction counts and recalculates campaign rates.
     *
     * The operation is transactional to ensure atomicity.
     *
     * @param event The OfferInteractionEvent containing campaign, offer, and interaction type details.
     * @throws RuntimeException if an error occurs during processing.
     */
    @Transactional
    public void processOfferInteraction(OfferInteractionEvent event) {
        if (event == null || event.getCampaignId() == null || event.getCampaignId().isEmpty() || event.getInteractionType() == null) {
            log.warn("Received null or invalid OfferInteractionEvent. Skipping processing.");
            return;
        }

        String campaignId = event.getCampaignId();
        OfferInteractionEvent.InteractionType interactionType = event.getInteractionType();
        log.info("Processing OfferInteractionEvent for campaignId: {} with type: {}", campaignId, interactionType);

        try {
            // Retrieve existing metrics. If no metrics exist, it indicates an issue (e.g., offer sent event was missed),
            // but for robustness, we create a new entry. In a strict system, this might throw an error.
            CampaignMetrics metrics = campaignMetricsRepository.findById(campaignId)
                    .orElseGet(() -> {
                        log.warn("No existing metrics found for campaignId: {}. Cannot update interaction counts without a base. Creating new entry.", campaignId);
                        return new CampaignMetrics(campaignId);
                    });

            // Increment the appropriate counter based on interaction type
            switch (interactionType) {
                case VIEWED:
                    metrics.setOffersViewedCount(metrics.getOffersViewedCount() + 1);
                    break;
                case ACCEPTED:
                    metrics.setOffersAcceptedCount(metrics.getOffersAcceptedCount() + 1);
                    break;
                case REJECTED:
                    metrics.setOffersRejectedCount(metrics.getOffersRejectedCount() + 1);
                    break;
                default:
                    log.warn("Unknown interaction type: {} for campaignId: {}. Skipping update.", interactionType, campaignId);
                    return; // Do not proceed with saving if type is unknown
            }

            metrics.updateRates(); // Recalculate rates after count update
            campaignMetricsRepository.save(metrics); // Persist the updated metrics
            log.debug("Successfully updated metrics for campaignId: {}. Interaction Type: {}. Current counts: Viewed={}, Accepted={}, Rejected={}",
                    campaignId, interactionType, metrics.getOffersViewedCount(), metrics.getOffersAcceptedCount(), metrics.getOffersRejectedCount());

        } catch (Exception e) {
            log.error("Error processing OfferInteractionEvent for campaignId: {} and type {}. Error: {}", campaignId, interactionType, e.getMessage(), e);
            throw new RuntimeException("Failed to process offer interaction event for campaign " + campaignId, e);
        }
    }

    /**
     * Recalculates and updates all campaign metrics for a specific campaign.
     * This method can be used for batch recalculations, data consistency checks,
     * or as part of a scheduled job if real-time updates are not strictly required.
     *
     * In a more complex system, this might involve re-aggregating data from raw event logs
     * or historical offer records to ensure accuracy. For this example, it simply
     * re-runs the rate calculation based on the existing stored counts.
     *
     * @param campaignId The ID of the campaign for which to recalculate metrics.
     * @throws IllegalArgumentException if campaign metrics are not found for the given ID.
     * @throws RuntimeException if an unexpected error occurs during recalculation.
     */
    @Transactional
    public void recalculateMetrics(String campaignId) {
        log.info("Recalculating metrics for campaignId: {}", campaignId);
        try {
            CampaignMetrics metrics = campaignMetricsRepository.findById(campaignId)
                    .orElseThrow(() -> new IllegalArgumentException("Campaign metrics not found for ID: " + campaignId));

            metrics.updateRates(); // Re-calculate rates based on current counts
            campaignMetricsRepository.save(metrics); // Save the updated metrics
            log.info("Successfully recalculated metrics for campaignId: {}", campaignId);
        } catch (IllegalArgumentException e) {
            log.warn("Recalculation skipped for campaignId {}: {}", campaignId, e.getMessage());
            // Do not re-throw for expected "not found" scenarios, just log.
        } catch (Exception e) {
            log.error("Error during recalculation for campaignId: {}. Error: {}", campaignId, e.getMessage(), e);
            throw new RuntimeException("Failed to recalculate metrics for campaign " + campaignId, e);
        }
    }
}
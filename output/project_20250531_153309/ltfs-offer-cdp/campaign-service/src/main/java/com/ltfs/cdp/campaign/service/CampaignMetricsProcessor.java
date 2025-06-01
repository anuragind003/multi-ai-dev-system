package com.ltfs.cdp.campaign.service;

import com.ltfs.cdp.campaign.model.CampaignMetrics;
import com.ltfs.cdp.campaign.repository.CampaignMetricsRepository;
import com.ltfs.cdp.campaign.event.OfferAcceptedEvent;
import com.ltfs.cdp.campaign.event.OfferRejectedEvent;
import com.ltfs.cdp.campaign.event.OfferSentEvent;
import com.ltfs.cdp.campaign.event.OfferViewedEvent;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;
import java.util.Optional;

/**
 * Service class responsible for processing and aggregating campaign performance metrics.
 * It listens to various offer-related events (sent, viewed, accepted, rejected)
 * and updates the corresponding campaign metrics in the database.
 * This class ensures that campaign performance data is kept up-to-date for reporting and analysis.
 *
 * <p>Note: For a highly concurrent environment, consider using database-level optimistic locking
 * or a more robust event processing framework (e.g., Kafka Streams for stateful aggregation)
 * to handle concurrent updates to campaign metrics more efficiently and reliably than simple
 * find-and-save operations within a transaction.</p>
 */
@Service
public class CampaignMetricsProcessor {

    private static final Logger logger = LoggerFactory.getLogger(CampaignMetricsProcessor.class);

    private final CampaignMetricsRepository campaignMetricsRepository;

    /**
     * Constructs a new CampaignMetricsProcessor with the given CampaignMetricsRepository.
     *
     * @param campaignMetricsRepository The repository for managing campaign metrics data.
     */
    @Autowired
    public CampaignMetricsProcessor(CampaignMetricsRepository campaignMetricsRepository) {
        this.campaignMetricsRepository = campaignMetricsRepository;
    }

    /**
     * Processes an {@link OfferSentEvent} to increment the 'offersSent' count for a campaign.
     * This method is typically invoked by an event listener (e.g., Kafka listener, Spring Cloud Stream).
     * It creates a new {@link CampaignMetrics} entry if one does not already exist for the campaign.
     *
     * @param event The OfferSentEvent containing campaign and offer details.
     */
    @Transactional
    public void processOfferSentEvent(OfferSentEvent event) {
        if (event == null || event.getCampaignId() == null || event.getCampaignId().trim().isEmpty()) {
            logger.warn("Received null or invalid OfferSentEvent (campaignId missing/empty). Skipping processing.");
            return;
        }

        String campaignId = event.getCampaignId();
        logger.info("Processing OfferSentEvent for campaignId: {}, offerId: {}", campaignId, event.getOfferId());

        try {
            // Retrieve existing metrics or create a new entry if it doesn't exist
            Optional<CampaignMetrics> existingMetrics = campaignMetricsRepository.findById(campaignId);
            CampaignMetrics metrics = existingMetrics.orElseGet(() -> {
                logger.debug("No existing metrics found for campaignId: {}. Creating new entry.", campaignId);
                // Initialize with zeros for all counts
                return new CampaignMetrics(campaignId, 0, 0, 0, 0, null);
            });

            // Increment the offersSent count
            metrics.setOffersSent(metrics.getOffersSent() + 1);
            metrics.setLastUpdated(LocalDateTime.now());

            // Save the updated metrics. Spring Data JPA's save method handles both insert and update.
            campaignMetricsRepository.save(metrics);
            logger.info("Successfully processed OfferSentEvent. CampaignId: {}, Offers Sent: {}", campaignId, metrics.getOffersSent());

        } catch (Exception e) {
            // Log the error and potentially rethrow a custom exception or publish to a dead-letter queue
            // for further investigation and reprocessing.
            logger.error("Error processing OfferSentEvent for campaignId: {}. Error: {}", campaignId, e.getMessage(), e);
            // Depending on the system's error handling policy, you might throw a custom runtime exception
            // to trigger a rollback or specific error flow.
            throw new RuntimeException("Failed to process OfferSentEvent for campaignId: " + campaignId, e);
        }
    }

    /**
     * Processes an {@link OfferViewedEvent} to increment the 'offersViewed' count for a campaign.
     * This method is typically invoked by an event listener.
     * It assumes that a {@link CampaignMetrics} entry for the campaign already exists (created by OfferSentEvent).
     *
     * @param event The OfferViewedEvent containing campaign and offer details.
     */
    @Transactional
    public void processOfferViewedEvent(OfferViewedEvent event) {
        if (event == null || event.getCampaignId() == null || event.getCampaignId().trim().isEmpty()) {
            logger.warn("Received null or invalid OfferViewedEvent (campaignId missing/empty). Skipping processing.");
            return;
        }

        String campaignId = event.getCampaignId();
        logger.info("Processing OfferViewedEvent for campaignId: {}, offerId: {}", campaignId, event.getOfferId());

        try {
            Optional<CampaignMetrics> existingMetrics = campaignMetricsRepository.findById(campaignId);
            if (existingMetrics.isPresent()) {
                CampaignMetrics metrics = existingMetrics.get();
                metrics.setOffersViewed(metrics.getOffersViewed() + 1);
                metrics.setLastUpdated(LocalDateTime.now());
                campaignMetricsRepository.save(metrics);
                logger.info("Successfully processed OfferViewedEvent. CampaignId: {}, Offers Viewed: {}", campaignId, metrics.getOffersViewed());
            } else {
                // This scenario might occur if events are out of order or OfferSentEvent failed.
                // Depending on business requirements, one might create a new entry here,
                // but typically 'viewed' implies 'sent' happened first.
                logger.warn("Campaign metrics not found for campaignId: {}. Cannot update offers viewed count. " +
                            "This might indicate an out-of-order event or missing OfferSentEvent.", campaignId);
            }
        } catch (Exception e) {
            logger.error("Error processing OfferViewedEvent for campaignId: {}. Error: {}", campaignId, e.getMessage(), e);
            throw new RuntimeException("Failed to process OfferViewedEvent for campaignId: " + campaignId, e);
        }
    }

    /**
     * Processes an {@link OfferAcceptedEvent} to increment the 'offersAccepted' count for a campaign.
     * This method is typically invoked by an event listener.
     * It assumes that a {@link CampaignMetrics} entry for the campaign already exists.
     *
     * @param event The OfferAcceptedEvent containing campaign and offer details.
     */
    @Transactional
    public void processOfferAcceptedEvent(OfferAcceptedEvent event) {
        if (event == null || event.getCampaignId() == null || event.getCampaignId().trim().isEmpty()) {
            logger.warn("Received null or invalid OfferAcceptedEvent (campaignId missing/empty). Skipping processing.");
            return;
        }

        String campaignId = event.getCampaignId();
        logger.info("Processing OfferAcceptedEvent for campaignId: {}, offerId: {}", campaignId, event.getOfferId());

        try {
            Optional<CampaignMetrics> existingMetrics = campaignMetricsRepository.findById(campaignId);
            if (existingMetrics.isPresent()) {
                CampaignMetrics metrics = existingMetrics.get();
                metrics.setOffersAccepted(metrics.getOffersAccepted() + 1);
                metrics.setLastUpdated(LocalDateTime.now());
                campaignMetricsRepository.save(metrics);
                logger.info("Successfully processed OfferAcceptedEvent. CampaignId: {}, Offers Accepted: {}", campaignId, metrics.getOffersAccepted());
            } else {
                logger.warn("Campaign metrics not found for campaignId: {}. Cannot update offers accepted count.", campaignId);
            }
        } catch (Exception e) {
            logger.error("Error processing OfferAcceptedEvent for campaignId: {}. Error: {}", campaignId, e.getMessage(), e);
            throw new RuntimeException("Failed to process OfferAcceptedEvent for campaignId: " + campaignId, e);
        }
    }

    /**
     * Processes an {@link OfferRejectedEvent} to increment the 'offersRejected' count for a campaign.
     * This method is typically invoked by an event listener.
     * It assumes that a {@link CampaignMetrics} entry for the campaign already exists.
     *
     * @param event The OfferRejectedEvent containing campaign and offer details.
     */
    @Transactional
    public void processOfferRejectedEvent(OfferRejectedEvent event) {
        if (event == null || event.getCampaignId() == null || event.getCampaignId().trim().isEmpty()) {
            logger.warn("Received null or invalid OfferRejectedEvent (campaignId missing/empty). Skipping processing.");
            return;
        }

        String campaignId = event.getCampaignId();
        logger.info("Processing OfferRejectedEvent for campaignId: {}, offerId: {}", campaignId, event.getOfferId());

        try {
            Optional<CampaignMetrics> existingMetrics = campaignMetricsRepository.findById(campaignId);
            if (existingMetrics.isPresent()) {
                CampaignMetrics metrics = existingMetrics.get();
                metrics.setOffersRejected(metrics.getOffersRejected() + 1);
                metrics.setLastUpdated(LocalDateTime.now());
                campaignMetricsRepository.save(metrics);
                logger.info("Successfully processed OfferRejectedEvent. CampaignId: {}, Offers Rejected: {}", campaignId, metrics.getOffersRejected());
            } else {
                logger.warn("Campaign metrics not found for campaignId: {}. Cannot update offers rejected count.", campaignId);
            }
        } catch (Exception e) {
            logger.error("Error processing OfferRejectedEvent for campaignId: {}. Error: {}", campaignId, e.getMessage(), e);
            throw new RuntimeException("Failed to process OfferRejectedEvent for campaignId: " + campaignId, e);
        }
    }

    /**
     * Calculates and returns the conversion rate for a given campaign.
     * Conversion rate is defined as (offersAccepted / offersSent) * 100.
     * Returns 0.0 if offersSent is 0 to avoid division by zero, or if no metrics are found.
     *
     * @param campaignId The ID of the campaign.
     * @return The conversion rate as a double, or 0.0 if no offers were sent or metrics not found.
     */
    @Transactional(readOnly = true)
    public double getConversionRate(String campaignId) {
        if (campaignId == null || campaignId.trim().isEmpty()) {
            logger.warn("Attempted to get conversion rate with null or empty campaignId.");
            return 0.0;
        }

        Optional<CampaignMetrics> metricsOptional = campaignMetricsRepository.findById(campaignId);
        if (metricsOptional.isPresent()) {
            CampaignMetrics metrics = metricsOptional.get();
            long offersSent = metrics.getOffersSent();
            long offersAccepted = metrics.getOffersAccepted();

            if (offersSent > 0) {
                // Calculate conversion rate as a percentage
                return (double) offersAccepted / offersSent * 100.0;
            } else {
                logger.debug("No offers sent for campaignId: {}. Conversion rate is 0.", campaignId);
                return 0.0;
            }
        } else {
            logger.info("Campaign metrics not found for campaignId: {}. Returning 0.0 conversion rate.", campaignId);
            return 0.0;
        }
    }
}
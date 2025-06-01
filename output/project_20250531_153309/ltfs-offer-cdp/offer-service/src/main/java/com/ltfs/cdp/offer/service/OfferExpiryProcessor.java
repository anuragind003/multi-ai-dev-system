package com.ltfs.cdp.offer.service;

import com.ltfs.cdp.offer.model.OfferStatus;
import com.ltfs.cdp.offer.repository.OfferRepository;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;

/**
 * OfferExpiryProcessor is a scheduled component responsible for identifying and processing
 * offers that have passed their expiry date.
 * It updates the status of expired offers to 'EXPIRED' in the database.
 * This component is designed to run periodically to maintain the accuracy of offer statuses.
 */
@Component
public class OfferExpiryProcessor {

    private static final Logger log = LoggerFactory.getLogger(OfferExpiryProcessor.class);

    private final OfferRepository offerRepository;

    /**
     * Constructs an OfferExpiryProcessor with the necessary OfferRepository.
     * Spring's dependency injection automatically provides the OfferRepository instance.
     *
     * @param offerRepository The repository for accessing and managing Offer entities.
     */
    @Autowired
    public OfferExpiryProcessor(OfferRepository offerRepository) {
        this.offerRepository = offerRepository;
    }

    /**
     * Scheduled task to process expired offers.
     * This method is configured to run daily at midnight (00:00 AM) by default.
     * The cron expression can be overridden via the 'offer.expiry.processor.cron' property
     * in the application's configuration (e.g., application.properties or application.yml).
     *
     * It performs a batch update to efficiently change the status of all offers that are
     * currently 'ACTIVE' and whose 'expiryDate' is in the past, setting their status to 'EXPIRED'.
     *
     * The @Transactional annotation ensures that the entire database update operation is
     * treated as a single, atomic transaction. If any part of the update fails, the entire
     * transaction will be rolled back, maintaining data consistency.
     */
    @Scheduled(cron = "${offer.expiry.processor.cron:0 0 0 * * ?}") // Default: daily at midnight
    @Transactional // Ensures the database operation is atomic
    public void processExpiredOffers() {
        log.info("Starting Offer Expiry Processor job at {}", LocalDateTime.now());
        long startTime = System.currentTimeMillis();

        try {
            // Perform a batch update to change the status of all expired active offers.
            // This approach is highly efficient for large datasets as it executes a single
            // SQL UPDATE statement, rather than fetching and then updating individual entities.
            // It assumes the OfferRepository has a method like:
            // int updateStatusForExpiredOffers(OfferStatus newStatus, OfferStatus oldStatus, LocalDateTime currentTime);
            int updatedCount = offerRepository.updateStatusForExpiredOffers(
                    OfferStatus.EXPIRED,      // The new status to set
                    OfferStatus.ACTIVE,       // The old status to match (only update active offers)
                    LocalDateTime.now()       // Offers expired before this time
            );

            if (updatedCount > 0) {
                log.info("Successfully processed {} offers. Updated status from ACTIVE to EXPIRED.", updatedCount);
            } else {
                log.info("No active offers found that have expired in this run.");
            }

        } catch (Exception e) {
            // Log the error with full stack trace for debugging purposes.
            // In a production environment, consider integrating with monitoring systems
            // to alert on job failures.
            log.error("Error occurred during Offer Expiry Processor job: {}", e.getMessage(), e);
        } finally {
            long endTime = System.currentTimeMillis();
            log.info("Offer Expiry Processor job finished in {} ms.", (endTime - startTime));
        }
    }
}
package com.ltfs.cdp.offer.expiry;

import com.ltfs.cdp.offer.model.Offer;
import com.ltfs.cdp.offer.service.OfferService;
import com.ltfs.cdp.offer.util.OfferStatus;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;

import java.time.LocalDateTime;
import java.util.List;

/**
 * OfferExpiryProcessor is a scheduled component responsible for identifying and processing
 * offers that have passed their expiry date. It periodically checks the database for
 * active offers whose expiry date is in the past and updates their status to 'EXPIRED'.
 *
 * This component plays a crucial role in maintaining the accuracy of offer availability
 * within the LTFS Offer CDP system, ensuring that only valid offers are presented to customers.
 */
@Component
public class OfferExpiryProcessor {

    private static final Logger logger = LoggerFactory.getLogger(OfferExpiryProcessor.class);

    private final OfferService offerService;

    /**
     * Constructs an OfferExpiryProcessor with the necessary OfferService dependency.
     *
     * @param offerService The service responsible for offer-related business logic and data access.
     */
    @Autowired
    public OfferExpiryProcessor(OfferService offerService) {
        this.offerService = offerService;
    }

    /**
     * This method is scheduled to run periodically to identify and process expired offers.
     * The cron expression is configured via the 'offer.expiry.cron.expression' property
     * in the application's configuration (e.g., application.properties or application.yml).
     *
     * The task performs the following steps:
     * 1. Logs the start of the expiry processing.
     * 2. Retrieves a list of offers that are currently active but have an expiry date
     *    in the past.
     * 3. If expired offers are found, it iterates through them and updates their status
     *    to 'EXPIRED' in the database.
     * 4. Logs the outcome of the processing, including the number of offers updated.
     * 5. Handles any exceptions that may occur during the process to ensure robustness.
     */
    @Scheduled(cron = "${offer.expiry.cron.expression}")
    public void processExpiredOffers() {
        logger.info("Starting scheduled task: Processing expired offers...");
        long startTime = System.currentTimeMillis();

        try {
            // Find offers that are active and whose expiry date is before the current time
            List<Offer> expiredOffers = offerService.findOffersByExpiryDateBeforeAndStatus(
                    LocalDateTime.now(), OfferStatus.ACTIVE);

            if (expiredOffers.isEmpty()) {
                logger.info("No expired offers found to process.");
                return;
            }

            logger.info("Found {} active offers that have expired. Initiating update...", expiredOffers.size());
            int updatedCount = 0;

            for (Offer offer : expiredOffers) {
                try {
                    // Update the offer status to EXPIRED
                    offerService.updateOfferStatus(offer.getOfferId(), OfferStatus.EXPIRED);
                    updatedCount++;
                    logger.debug("Successfully marked offer ID: {} as EXPIRED.", offer.getOfferId());
                } catch (Exception e) {
                    logger.error("Failed to mark offer ID: {} as EXPIRED. Error: {}", offer.getOfferId(), e.getMessage(), e);
                    // Continue processing other offers even if one fails
                }
            }

            long endTime = System.currentTimeMillis();
            logger.info("Finished processing expired offers. Total {} offers processed, {} offers successfully marked as EXPIRED in {} ms.",
                    expiredOffers.size(), updatedCount, (endTime - startTime));

        } catch (Exception e) {
            logger.error("An unexpected error occurred during expired offer processing: {}", e.getMessage(), e);
        }
    }
}
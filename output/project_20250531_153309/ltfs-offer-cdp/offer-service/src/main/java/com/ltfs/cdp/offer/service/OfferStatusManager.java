package com.ltfs.cdp.offer.service;

import com.ltfs.cdp.offer.exception.OfferNotFoundException;
import com.ltfs.cdp.offer.model.Offer;
import com.ltfs.cdp.offer.model.OfferStatus;
import com.ltfs.cdp.offer.repository.OfferRepository;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;
import java.util.List;
import java.util.Optional;

/**
 * Service class responsible for managing the status transitions of offers.
 * This includes expiring offers based on their validity end date and
 * updating the status of individual offers.
 */
@Service
public class OfferStatusManager {

    private static final Logger log = LoggerFactory.getLogger(OfferStatusManager.class);

    private final OfferRepository offerRepository;

    /**
     * Constructs an OfferStatusManager with the necessary repository dependency.
     *
     * @param offerRepository The repository for accessing and managing Offer entities.
     */
    public OfferStatusManager(OfferRepository offerRepository) {
        this.offerRepository = offerRepository;
    }

    /**
     * Updates the status of a specific offer.
     * This method finds an offer by its ID and updates its status to the new provided status.
     *
     * @param offerId   The unique identifier of the offer to update.
     * @param newStatus The new status to set for the offer.
     * @return The updated Offer entity.
     * @throws OfferNotFoundException if no offer is found with the given offerId.
     */
    @Transactional
    public Offer updateOfferStatus(String offerId, OfferStatus newStatus) {
        log.info("Attempting to update status for offerId: {} to newStatus: {}", offerId, newStatus);
        Optional<Offer> offerOptional = offerRepository.findById(offerId);

        if (offerOptional.isEmpty()) {
            log.warn("Offer not found with ID: {}", offerId);
            throw new OfferNotFoundException("Offer not found with ID: " + offerId);
        }

        Offer offer = offerOptional.get();
        OfferStatus currentStatus = offer.getStatus();

        // Prevent updating if the status is already the same
        if (currentStatus == newStatus) {
            log.info("Offer {} already has status {}. No update needed.", offerId, newStatus);
            return offer;
        }

        // Add any specific business rules for status transitions here if needed
        // For example:
        // if (currentStatus == OfferStatus.EXPIRED && newStatus == OfferStatus.ACTIVE) {
        //     throw new IllegalArgumentException("Cannot reactivate an expired offer.");
        // }

        offer.setStatus(newStatus);
        Offer updatedOffer = offerRepository.save(offer);
        log.info("Successfully updated status for offerId: {} from {} to {}", offerId, currentStatus, newStatus);
        return updatedOffer;
    }

    /**
     * Periodically checks for and expires offers whose validity end date has passed.
     * This method is scheduled to run daily at a specific time (e.g., 2 AM).
     * It fetches all 'ACTIVE' offers that have expired and updates their status to 'EXPIRED'.
     * The cron expression "0 0 2 * * ?" means: at 0 seconds, 0 minutes, 2 AM, every day of the month, every month, any day of the week.
     */
    @Scheduled(cron = "${offer.expiration.cron:0 0 2 * * ?}") // Default to 2 AM daily if property not set
    @Transactional
    public void expireOffers() {
        log.info("Starting scheduled task to expire offers at {}", LocalDateTime.now());
        LocalDateTime now = LocalDateTime.now();

        // Find all active offers whose validityEndDate is before the current time
        List<Offer> offersToExpire = offerRepository.findByStatusAndValidityEndDateBefore(OfferStatus.ACTIVE, now);

        if (offersToExpire.isEmpty()) {
            log.info("No active offers found to expire.");
            return;
        }

        log.info("Found {} active offers to expire.", offersToExpire.size());

        for (Offer offer : offersToExpire) {
            try {
                // Update the status to EXPIRED
                offer.setStatus(OfferStatus.EXPIRED);
                offerRepository.save(offer);
                log.debug("Offer with ID {} successfully expired.", offer.getOfferId());
            } catch (Exception e) {
                // Log the error but continue processing other offers
                log.error("Failed to expire offer with ID {}: {}", offer.getOfferId(), e.getMessage(), e);
            }
        }
        log.info("Finished scheduled task to expire offers. Total offers processed: {}", offersToExpire.size());
    }

    // --- Helper/Mock classes for compilation if not available in project context ---
    // These would typically be in their own files and packages.
    // For the purpose of generating a runnable file, they are included here.

    /**
     * Mock Offer entity for demonstration purposes.
     * In a real project, this would be in `com.ltfs.cdp.offer.model.Offer`.
     */
    // @jakarta.persistence.Entity
    // @jakarta.persistence.Table(name = "offers")
    // @lombok.Data // Requires Lombok dependency
    // class Offer {
    //     @jakarta.persistence.Id
    //     private String offerId;
    //     private String customerId;
    //     private String campaignId;
    //     @jakarta.persistence.Enumerated(jakarta.persistence.EnumType.STRING)
    //     private OfferStatus status;
    //     private java.time.LocalDateTime validityStartDate;
    //     private java.time.LocalDateTime validityEndDate;
    //     // Other fields like product details, offer amount, etc.
    // }

    /**
     * Mock OfferStatus enum for demonstration purposes.
     * In a real project, this would be in `com.ltfs.cdp.offer.model.OfferStatus`.
     */
    // enum OfferStatus {
    //     ACTIVE,
    //     EXPIRED,
    //     DEDUPED,
    //     ACCEPTED,
    //     REJECTED,
    //     PENDING,
    //     CANCELLED
    // }

    /**
     * Mock OfferRepository interface for demonstration purposes.
     * In a real project, this would be in `com.ltfs.cdp.offer.repository.OfferRepository`.
     */
    // @org.springframework.stereotype.Repository
    // interface OfferRepository extends org.springframework.data.jpa.repository.JpaRepository<Offer, String> {
    //     java.util.List<Offer> findByStatusAndValidityEndDateBefore(OfferStatus status, java.time.LocalDateTime dateTime);
    // }

    /**
     * Mock OfferNotFoundException for demonstration purposes.
     * In a real project, this would be in `com.ltfs.cdp.offer.exception.OfferNotFoundException`.
     */
    // class OfferNotFoundException extends RuntimeException {
    //     public OfferNotFoundException(String message) {
    //         super(message);
    //     }
    // }
}
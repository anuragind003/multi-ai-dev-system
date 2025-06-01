package com.ltfs.cdp.offer.status;

import com.ltfs.cdp.offer.enums.OfferStatus;
import com.ltfs.cdp.offer.exception.OfferNotFoundException;
import com.ltfs.cdp.offer.model.Offer;
import com.ltfs.cdp.offer.repository.OfferRepository;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDate;
import java.util.List;
import java.util.Optional;

/**
 * Service component responsible for managing and updating the status of offers within the LTFS Offer CDP system.
 * This class provides methods to change an offer's status to ACTIVE, INACTIVE, or EXPIRED,
 * ensuring data consistency and adherence to business rules.
 *
 * <p>Assumptions for this file to be directly runnable within the project context:</p>
 * <ul>
 *     <li>{@code com.ltfs.cdp.offer.model.Offer}: An entity class representing an offer,
 *         with fields like {@code id} (Long), {@code status} (OfferStatus), and {@code offerEndDate} (LocalDate).</li>
 *     <li>{@code com.ltfs.cdp.offer.enums.OfferStatus}: An enum defining possible offer statuses
 *         (e.g., ACTIVE, INACTIVE, EXPIRED, CONSUMED, REJECTED).</li>
 *     <li>{@code com.ltfs.cdp.offer.repository.OfferRepository}: A Spring Data JPA repository interface
 *         extending {@code JpaRepository<Offer, Long>}, with a method like
 *         {@code findByStatusAndOfferEndDateBefore(OfferStatus status, LocalDate date)}.</li>
 *     <li>{@code com.ltfs.cdp.offer.exception.OfferNotFoundException}: A custom runtime exception
 *         to indicate when an offer cannot be found by its ID.</li>
 * </ul>
 */
@Service
public class OfferStatusManager {

    private static final Logger log = LoggerFactory.getLogger(OfferStatusManager.class);

    private final OfferRepository offerRepository;

    /**
     * Constructs an OfferStatusManager with the necessary OfferRepository dependency.
     * Spring's dependency injection automatically provides the OfferRepository instance.
     *
     * @param offerRepository The repository for Offer entities, used for database operations.
     */
    @Autowired
    public OfferStatusManager(OfferRepository offerRepository) {
        this.offerRepository = offerRepository;
    }

    /**
     * Updates the status of a specific offer identified by its ID to the given new status.
     * This is a generic method used by other specific status update methods.
     *
     * @param offerId The unique identifier of the offer to update.
     * @param newStatus The {@link OfferStatus} to set for the offer.
     * @return The updated {@link Offer} entity after the status change.
     * @throws OfferNotFoundException if no offer with the provided {@code offerId} is found in the database.
     */
    @Transactional
    public Offer updateOfferStatus(Long offerId, OfferStatus newStatus) {
        log.info("Attempting to update status for offer ID: {} to {}", offerId, newStatus);

        // Retrieve the offer from the database using its ID.
        // Optional is used to handle cases where the offer might not exist.
        Optional<Offer> offerOptional = offerRepository.findById(offerId);

        // If the offer is not found, log a warning and throw a custom exception.
        if (offerOptional.isEmpty()) {
            log.warn("Offer with ID: {} not found. Cannot update status.", offerId);
            throw new OfferNotFoundException("Offer with ID " + offerId + " not found.");
        }

        Offer offer = offerOptional.get();
        OfferStatus oldStatus = offer.getStatus();

        // Check if the new status is the same as the current status to avoid unnecessary database operations.
        if (oldStatus == newStatus) {
            log.info("Offer ID: {} already has status {}. No update needed.", offerId, newStatus);
            return offer; // Return the existing offer as no change was made.
        }

        // Set the new status and save the updated offer back to the database.
        offer.setStatus(newStatus);
        Offer updatedOffer = offerRepository.save(offer);
        log.info("Successfully updated status for offer ID: {} from {} to {}", offerId, oldStatus, newStatus);
        return updatedOffer;
    }

    /**
     * Sets an offer's status to {@link OfferStatus#INACTIVE}.
     * This method is typically invoked when an offer is consumed by a customer, rejected,
     * or otherwise becomes unavailable for further action.
     *
     * @param offerId The unique identifier of the offer to deactivate.
     * @return The deactivated {@link Offer} entity.
     * @throws OfferNotFoundException if no offer with the given ID is found.
     */
    @Transactional
    public Offer deactivateOffer(Long offerId) {
        log.debug("Request to deactivate offer with ID: {}", offerId);
        return updateOfferStatus(offerId, OfferStatus.INACTIVE);
    }

    /**
     * Sets an offer's status to {@link OfferStatus#ACTIVE}.
     * This method might be used when an offer is newly created and made available,
     * or if an inactive offer needs to be reactivated for some reason.
     *
     * @param offerId The unique identifier of the offer to activate.
     * @return The activated {@link Offer} entity.
     * @throws OfferNotFoundException if no offer with the given ID is found.
     */
    @Transactional
    public Offer activateOffer(Long offerId) {
        log.debug("Request to activate offer with ID: {}", offerId);
        return updateOfferStatus(offerId, OfferStatus.ACTIVE);
    }

    /**
     * Identifies and updates offers whose {@code offerEndDate} has passed to {@link OfferStatus#EXPIRED}.
     * This method is designed to be invoked periodically, typically by a scheduled job,
     * to automatically manage the lifecycle of offers.
     *
     * @return A list of {@link Offer} entities that were identified and attempted to be expired.
     *         The returned offers will reflect their new {@link OfferStatus#EXPIRED} status if the update was successful.
     */
    @Transactional
    public List<Offer> expireOffers() {
        log.info("Starting scheduled job to identify and expire offers.");

        // Find all offers that are currently ACTIVE and whose offerEndDate is before today's date.
        // This query leverages Spring Data JPA's derived query capabilities.
        List<Offer> offersToExpire = offerRepository.findByStatusAndOfferEndDateBefore(OfferStatus.ACTIVE, LocalDate.now());

        if (offersToExpire.isEmpty()) {
            log.info("No active offers found with an end date before today. No offers to expire.");
            return List.of(); // Return an empty, immutable list if no offers need expiring.
        }

        log.info("Found {} active offers to expire as their end date has passed.", offersToExpire.size());

        // Iterate through the identified offers and update their status to EXPIRED.
        for (Offer offer : offersToExpire) {
            try {
                // Set the status to EXPIRED.
                offer.setStatus(OfferStatus.EXPIRED);
                // Save the updated offer to persist the status change.
                offerRepository.save(offer);
                log.debug("Successfully expired offer ID: {}", offer.getId());
            } catch (Exception e) {
                // Log any errors encountered during the update of a specific offer,
                // but continue processing other offers to ensure robustness.
                log.error("Failed to expire offer ID: {}. Error: {}", offer.getId(), e.getMessage(), e);
            }
        }
        log.info("Finished scheduled job for expiring offers. Processed {} offers.", offersToExpire.size());
        // Return the list of offers that were targeted for expiration.
        // These objects in the list will now reflect their updated EXPIRED status.
        return offersToExpire;
    }
}
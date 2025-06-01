package com.ltfs.cdp.offer.event;

import com.ltfs.cdp.offer.event.model.CampaignUpdateEvent;
import com.ltfs.cdp.offer.event.model.CustomerDeduplicationEvent;
import com.ltfs.cdp.offer.service.OfferService;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.context.event.EventListener;
import org.springframework.scheduling.annotation.Async;
import org.springframework.stereotype.Component;

/**
 * Event listener component responsible for reacting to various system events
 * that may impact the validity or status of offers.
 * This includes events related to customer deduplication and campaign updates,
 * ensuring that offer data remains consistent and accurate with the latest
 * customer and campaign information.
 *
 * This component leverages Spring's event handling mechanism and processes
 * events asynchronously to avoid blocking the event publishers.
 */
@Component
public class OfferEventListener {

    private static final Logger log = LoggerFactory.getLogger(OfferEventListener.class);

    private final OfferService offerService;

    /**
     * Constructs an OfferEventListener with the necessary OfferService dependency.
     * Spring will automatically inject the OfferService instance.
     *
     * @param offerService The service responsible for managing offer-related business logic.
     */
    public OfferEventListener(OfferService offerService) {
        this.offerService = offerService;
    }

    /**
     * Listens for {@link CustomerDeduplicationEvent}s.
     * When a customer deduplication occurs, this method processes the event
     * to update or invalidate offers associated with the merged/duplicate customer IDs.
     * This ensures that offers reflect the consolidated customer profile, aligning
     * with the requirement to perform deduplication against the 'live book'
     * and handle specific dedupe rules for 'Top-up loan offers'.
     *
     * The method is annotated with {@code @Async} to ensure that the event processing
     * does not block the thread that published the event, improving system responsiveness.
     *
     * @param event The CustomerDeduplicationEvent containing details of the deduplication,
     *              including the primary customer ID and a list of merged customer IDs.
     */
    @EventListener
    @Async // Process asynchronously to avoid blocking the deduplication service
    public void handleCustomerDeduplicationEvent(CustomerDeduplicationEvent event) {
        log.info("Received CustomerDeduplicationEvent for primary customer ID: {}, merged customer IDs: {}",
                event.getPrimaryCustomerId(), event.getMergedCustomerIds());
        try {
            // Iterate through all customer IDs that were merged into the primary one.
            // Offers associated with these merged IDs might need to be invalidated or re-assigned.
            for (String mergedCustomerId : event.getMergedCustomerIds()) {
                log.debug("Processing offers for merged customer ID: {}", mergedCustomerId);
                // Invalidate offers associated with the merged customer.
                // The specific business logic (e.g., transfer offers, mark as invalid,
                // or re-evaluate eligibility) should be encapsulated within OfferService.
                // For this implementation, we assume offers from merged customers are invalidated.
                offerService.invalidateOffersByCustomerId(mergedCustomerId);
                log.info("Invalidated offers associated with merged customer ID: {}", mergedCustomerId);

                // If the business rule dictates transferring offers from merged to primary:
                // offerService.transferOffers(mergedCustomerId, event.getPrimaryCustomerId());
                // log.info("Transferred offers from {} to {}", mergedCustomerId, event.getPrimaryCustomerId());
            }

            // After deduplication, existing offers for the primary customer might need
            // re-evaluation against the updated 'live book' (Customer 360) or new dedupe rules.
            // This is crucial for ensuring offer validity post-deduplication, especially
            // for rules like "Top-up loan offers must be deduped only within other Top-up offers".
            offerService.revalidateOffersForCustomer(event.getPrimaryCustomerId());
            log.info("Triggered re-validation of offers for primary customer ID: {}", event.getPrimaryCustomerId());

        } catch (Exception e) {
            // Log the error to provide visibility into failed event processing.
            // Depending on the severity, more robust error handling might be needed,
            // such as publishing to a dead-letter queue or implementing retry logic.
            log.error("Error handling CustomerDeduplicationEvent for primary customer ID {}: {}",
                    event.getPrimaryCustomerId(), e.getMessage(), e);
        }
    }

    /**
     * Listens for {@link CampaignUpdateEvent}s.
     * When a campaign's status or details are updated, this method processes the event
     * to re-evaluate or invalidate offers linked to that campaign. This ensures that
     * offers remain consistent with their parent campaign's status and rules.
     *
     * The method is annotated with {@code @Async} to ensure that the event processing
     * does not block the thread that published the event.
     *
     * @param event The CampaignUpdateEvent containing details of the campaign update,
     *              including the campaign ID and its new status.
     */
    @EventListener
    @Async // Process asynchronously to avoid blocking the campaign management service
    public void handleCampaignUpdateEvent(CampaignUpdateEvent event) {
        log.info("Received CampaignUpdateEvent for campaign ID: {}, new status: {}",
                event.getCampaignId(), event.getNewStatus());
        try {
            // Based on the campaign update, offers linked to this campaign might need action.
            // For example, if a campaign is deactivated or cancelled, all its offers might become invalid.
            // If eligibility criteria change, offers might need re-evaluation.
            final String newStatus = event.getNewStatus();

            if ("INACTIVE".equalsIgnoreCase(newStatus) || "CANCELLED".equalsIgnoreCase(newStatus) || "COMPLETED".equalsIgnoreCase(newStatus)) {
                // If the campaign is no longer active, invalidate all associated offers.
                offerService.invalidateOffersByCampaignId(event.getCampaignId());
                log.info("Invalidated all offers for campaign ID {} due to status change to {}",
                        event.getCampaignId(), newStatus);
            } else {
                // For other updates (e.g., criteria change, active status update),
                // offers might need re-evaluation to ensure they still meet the campaign's rules.
                offerService.revalidateOffersByCampaignId(event.getCampaignId());
                log.info("Triggered re-validation of offers for campaign ID {} due to update", event.getCampaignId());
            }

        } catch (Exception e) {
            // Log the error for visibility. Similar to customer deduplication,
            // consider more advanced error handling strategies if critical.
            log.error("Error handling CampaignUpdateEvent for campaign ID {}: {}",
                    event.getCampaignId(), e.getMessage(), e);
        }
    }

    // Additional event listeners can be added here as new event types are introduced
    // that impact offer validity or status. For example, an event for offer finalization
    // or external system updates.
    //
    // Example:
    // @EventListener
    // @Async
    // public void handleOfferFinalizationEvent(OfferFinalizationEvent event) {
    //     log.info("Received OfferFinalizationEvent for offer ID: {}", event.getOfferId());
    //     try {
    //         // Perform any final checks or updates after an offer is finalized.
    //         offerService.finalizeOfferStatus(event.getOfferId());
    //     } catch (Exception e) {
    //         log.error("Error finalizing offer ID {}: {}", event.getOfferId(), e.getMessage(), e);
    //     }
    // }
}
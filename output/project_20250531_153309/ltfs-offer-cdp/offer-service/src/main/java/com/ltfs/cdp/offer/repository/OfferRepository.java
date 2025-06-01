package com.ltfs.cdp.offer.repository;

import com.ltfs.cdp.offer.model.Offer;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.Optional;

/**
 * JPA Repository for the {@link Offer} entity.
 * This interface provides standard CRUD operations and custom query methods
 * for managing offer data in the LTFS Offer CDP system.
 *
 * The system aims to eliminate manual processes, enable faster processing,
 * and improve the management of customer, campaign, and various offer data.
 *
 * @author Code Generation Agent
 * @version 1.0
 * @since 2025-05-31
 */
@Repository
public interface OfferRepository extends JpaRepository<Offer, Long> {

    /**
     * Finds all offers associated with a specific customer ID.
     * This method is crucial for providing a single profile view of the customer
     * by aggregating all offers linked to them.
     *
     * @param customerId The unique identifier of the customer.
     * @return A list of {@link Offer} entities associated with the given customer ID.
     */
    List<Offer> findByCustomerId(String customerId);

    /**
     * Finds all offers associated with a specific campaign ID.
     * This allows for querying offers based on the campaigns they originated from.
     *
     * @param campaignId The unique identifier of the campaign.
     * @return A list of {@link Offer} entities associated with the given campaign ID.
     */
    List<Offer> findByCampaignId(String campaignId);

    /**
     * Finds offers by their current status.
     * This can be used for filtering offers based on their lifecycle stage
     * (e.g., PENDING, APPROVED, REJECTED, DEDUPED, ACTIVE, EXPIRED).
     *
     * @param status The status of the offer (e.g., "ACTIVE", "EXPIRED", "DEDUPED").
     * @return A list of {@link Offer} entities matching the given status.
     */
    List<Offer> findByStatus(String status);

    /**
     * Finds offers by customer ID and offer type.
     * This method is particularly useful for implementing specific deduplication logic,
     * such as ensuring "Top-up loan offers must be deduped only within other Top-up offers".
     *
     * @param customerId The unique identifier of the customer.
     * @param offerType The type of the offer (e.g., "TOP_UP_LOAN", "PRE_APPROVED", "LOYALTY").
     * @return A list of {@link Offer} entities matching the given customer ID and offer type.
     */
    List<Offer> findByCustomerIdAndOfferType(String customerId, String offerType);

    /**
     * Finds an offer by its unique offer code.
     * This is useful for direct lookup of a specific offer using its business identifier.
     *
     * @param offerCode The unique code assigned to the offer.
     * @return An {@link Optional} containing the {@link Offer} if found, or empty otherwise.
     */
    Optional<Offer> findByOfferCode(String offerCode);

    /**
     * Finds offers that are currently active for a given customer.
     * This combines customer identification with offer status to retrieve relevant,
     * currently valid offers.
     *
     * @param customerId The unique identifier of the customer.
     * @param status The status indicating an active offer (e.g., "ACTIVE", "PENDING_APPROVAL").
     * @return A list of active {@link Offer} entities for the given customer.
     */
    List<Offer> findByCustomerIdAndStatus(String customerId, String status);
}
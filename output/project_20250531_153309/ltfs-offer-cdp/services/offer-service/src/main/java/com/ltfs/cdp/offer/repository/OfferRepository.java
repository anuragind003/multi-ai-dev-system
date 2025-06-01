package com.ltfs.cdp.offer.repository;

import com.ltfs.cdp.offer.entity.Offer;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.Optional;

/**
 * Spring Data JPA repository for the {@link Offer} entity.
 * This interface provides standard CRUD operations and custom query methods
 * for managing offer data in the LTFS Offer CDP system.
 */
@Repository
public interface OfferRepository extends JpaRepository<Offer, Long> {

    /**
     * Finds all offers associated with a specific customer ID.
     * This is crucial for providing a single profile view of the customer
     * and for retrieving all offers related to a customer for deduplication
     * and other processing.
     *
     * @param customerId The unique identifier of the customer.
     * @return A list of {@link Offer} entities associated with the given customer ID.
     */
    List<Offer> findByCustomerId(Long customerId);

    /**
     * Finds an offer by its unique offer ID.
     *
     * @param offerId The unique identifier of the offer.
     * @return An {@link Optional} containing the {@link Offer} if found, or empty otherwise.
     */
    Optional<Offer> findByOfferId(String offerId); // Assuming offerId is a String/UUID in the entity

    /**
     * Finds all offers by their current status.
     * This can be used for filtering offers that are 'PENDING', 'APPROVED', 'REJECTED', etc.
     *
     * @param offerStatus The status of the offer (e.g., "PENDING", "ACTIVE", "EXPIRED").
     * @return A list of {@link Offer} entities matching the given status.
     */
    List<Offer> findByOfferStatus(String offerStatus);

    /**
     * Finds offers by customer ID and offer type.
     * This is particularly useful for specific deduplication logic,
     * such as deduping "Top-up loan offers" only within other "Top-up offers".
     *
     * @param customerId The unique identifier of the customer.
     * @param offerType The type of the offer (e.g., "TOP_UP_LOAN", "PRE_APPROVED_LOAN").
     * @return A list of {@link Offer} entities matching both customer ID and offer type.
     */
    List<Offer> findByCustomerIdAndOfferType(Long customerId, String offerType);

    // Additional custom query methods can be added here as per evolving functional requirements.
    // Examples:
    // List<Offer> findByCampaignId(Long campaignId);
    // List<Offer> findByCustomerIdAndOfferStatusIn(Long customerId, List<String> statuses);
}
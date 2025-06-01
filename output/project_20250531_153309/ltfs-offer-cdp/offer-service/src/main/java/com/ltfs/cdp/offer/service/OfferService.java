package com.ltfs.cdp.offer.service;

import com.ltfs.cdp.offer.dto.OfferRequestDTO;
import com.ltfs.cdp.offer.dto.OfferResponseDTO;
import com.ltfs.cdp.offer.dto.OfferUpdateDTO;
import com.ltfs.cdp.offer.enums.OfferStatus;
import com.ltfs.cdp.offer.exception.OfferNotFoundException;
import com.ltfs.cdp.offer.exception.OfferValidationException;
import com.ltfs.cdp.offer.mapper.OfferMapper;
import com.ltfs.cdp.offer.model.Offer;
import com.ltfs.cdp.offer.repository.OfferRepository;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;
import java.util.List;
import java.util.Optional;
import java.util.stream.Collectors;

/**
 * Service class for managing offer data and its lifecycle within the LTFS Offer CDP system.
 * This service handles CRUD operations for offers, applies business logic such as validation
 * and orchestrates deduplication processes.
 */
@Service
@Transactional(readOnly = true) // Default to read-only transactions for methods not explicitly marked @Transactional
public class OfferService {

    private static final Logger log = LoggerFactory.getLogger(OfferService.class);

    private final OfferRepository offerRepository;
    private final OfferMapper offerMapper;
    // Potentially inject a DeduplicationService here if deduplication is a separate component
    // private final DeduplicationService deduplicationService;

    /**
     * Constructs an OfferService with necessary dependencies.
     *
     * @param offerRepository The repository for Offer entities.
     * @param offerMapper The mapper for converting between Offer entities and DTOs.
     */
    public OfferService(OfferRepository offerRepository, OfferMapper offerMapper) {
        this.offerRepository = offerRepository;
        this.offerMapper = offerMapper;
    }

    /**
     * Creates a new offer in the system.
     * This method performs initial validation and triggers deduplication checks
     * before persisting the offer.
     *
     * @param offerRequestDTO The DTO containing data for the new offer.
     * @return The OfferResponseDTO representing the newly created offer.
     * @throws OfferValidationException If the offer data fails validation or a duplicate is detected.
     */
    @Transactional
    public OfferResponseDTO createOffer(OfferRequestDTO offerRequestDTO) {
        log.info("Attempting to create a new offer for customer ID: {}", offerRequestDTO.getCustomerId());

        // 1. Basic column-level validation on data moving from Offermart to CDP System.
        validateOfferRequest(offerRequestDTO);

        // Convert DTO to entity
        Offer offer = offerMapper.toEntity(offerRequestDTO);

        // Set initial status and timestamps
        if (offer.getOfferStatus() == null) {
            offer.setOfferStatus(OfferStatus.PENDING); // Or a suitable initial status like 'NEW' or 'DRAFT'
        }
        offer.setCreatedAt(LocalDateTime.now());
        offer.setUpdatedAt(LocalDateTime.now());

        // 2. Perform deduplication logic.
        // This is a critical step as per functional requirements:
        // - Apply dedupe logic across all Consumer Loan (CL) products.
        // - Perform deduplication against the 'live book' (Customer 360) before offers are finalized.
        // - Top-up loan offers must be deduped only within other Top-up offers.
        // The actual implementation would involve complex logic, potentially
        // calling an external service or a dedicated deduplication component.
        // For the purpose of this service, we assume deduplication logic is applied
        // either before this service is called, or within a dedicated component
        // that this service interacts with. If an offer is determined to be a duplicate
        // and should not be persisted, an exception should be thrown or the offer
        // status should be set accordingly.
        performDeduplicationCheck(offer); // This method would update offer status or throw exception if duplicate

        // If the offer status was changed to a rejected state by deduplication,
        // we might choose not to save it or save it with the rejected status.
        // For this implementation, we save it regardless, allowing tracking of rejected offers.
        Offer savedOffer = offerRepository.save(offer);
        log.info("Offer created successfully with ID: {} and status: {}", savedOffer.getOfferId(), savedOffer.getOfferStatus());

        return offerMapper.toResponseDTO(savedOffer);
    }

    /**
     * Retrieves an offer by its unique identifier.
     *
     * @param offerId The unique ID of the offer.
     * @return The OfferResponseDTO if found.
     * @throws OfferNotFoundException If no offer is found with the given ID.
     */
    public OfferResponseDTO getOfferById(String offerId) {
        log.debug("Fetching offer with ID: {}", offerId);
        Offer offer = offerRepository.findByOfferId(offerId)
                .orElseThrow(() -> {
                    log.warn("Offer not found with ID: {}", offerId);
                    return new OfferNotFoundException("Offer not found with ID: " + offerId);
                });
        return offerMapper.toResponseDTO(offer);
    }

    /**
     * Retrieves all offers available in the system.
     *
     * @return A list of OfferResponseDTOs.
     */
    public List<OfferResponseDTO> getAllOffers() {
        log.debug("Fetching all offers.");
        List<Offer> offers = offerRepository.findAll();
        return offers.stream()
                .map(offerMapper::toResponseDTO)
                .collect(Collectors.toList());
    }

    /**
     * Retrieves all offers associated with a specific customer.
     *
     * @param customerId The unique ID of the customer.
     * @return A list of OfferResponseDTOs for the given customer.
     */
    public List<OfferResponseDTO> getOffersByCustomerId(String customerId) {
        log.debug("Fetching offers for customer ID: {}", customerId);
        List<Offer> offers = offerRepository.findByCustomerId(customerId);
        return offers.stream()
                .map(offerMapper::toResponseDTO)
                .collect(Collectors.toList());
    }

    /**
     * Updates the status of an existing offer.
     *
     * @param offerId The ID of the offer to update.
     * @param newStatus The new status to set for the offer.
     * @return The updated OfferResponseDTO.
     * @throws OfferNotFoundException If no offer is found with the given ID.
     * @throws OfferValidationException If the status transition is invalid (if such rules are implemented).
     */
    @Transactional
    public OfferResponseDTO updateOfferStatus(String offerId, OfferStatus newStatus) {
        log.info("Attempting to update status for offer ID: {} to {}", offerId, newStatus);
        Offer offer = offerRepository.findByOfferId(offerId)
                .orElseThrow(() -> {
                    log.warn("Offer not found for status update with ID: {}", offerId);
                    return new OfferNotFoundException("Offer not found with ID: " + offerId);
                });

        // Implement status transition validation if necessary.
        // Example: if (offer.getOfferStatus() == OfferStatus.ACCEPTED && newStatus == OfferStatus.PENDING) {
        //     throw new OfferValidationException("Cannot change status from ACCEPTED to PENDING.");
        // }
        // Ensure the new status is valid.
        if (newStatus == null) {
            throw new OfferValidationException("New offer status cannot be null.");
        }

        offer.setOfferStatus(newStatus);
        offer.setUpdatedAt(LocalDateTime.now());
        Offer updatedOffer = offerRepository.save(offer);
        log.info("Offer ID: {} status updated to {}", offerId, newStatus);
        return offerMapper.toResponseDTO(updatedOffer);
    }

    /**
     * Updates details of an existing offer.
     *
     * @param offerId The ID of the offer to update.
     * @param offerUpdateDTO The DTO containing updated offer data.
     * @return The updated OfferResponseDTO.
     * @throws OfferNotFoundException If no offer is found with the given ID.
     * @throws OfferValidationException If the update data fails validation (e.g., invalid dates).
     */
    @Transactional
    public OfferResponseDTO updateOffer(String offerId, OfferUpdateDTO offerUpdateDTO) {
        log.info("Attempting to update offer with ID: {}", offerId);
        Offer existingOffer = offerRepository.findByOfferId(offerId)
                .orElseThrow(() -> {
                    log.warn("Offer not found for update with ID: {}", offerId);
                    return new OfferNotFoundException("Offer not found with ID: " + offerId);
                });

        // Apply updates from DTO to entity.
        // Using Optional.ofNullable to only update fields that are present in the DTO.
        Optional.ofNullable(offerUpdateDTO.getCampaignId()).ifPresent(existingOffer::setCampaignId);
        Optional.ofNullable(offerUpdateDTO.getOfferType()).ifPresent(existingOffer::setOfferType);
        Optional.ofNullable(offerUpdateDTO.getOfferAmount()).ifPresent(existingOffer::setOfferAmount);
        Optional.ofNullable(offerUpdateDTO.getValidityStartDate()).ifPresent(existingOffer::setValidityStartDate);
        Optional.ofNullable(offerUpdateDTO.getValidityEndDate()).ifPresent(existingOffer::setValidityEndDate);
        Optional.ofNullable(offerUpdateDTO.getOfferDetails()).ifPresent(existingOffer::setOfferDetails);
        Optional.ofNullable(offerUpdateDTO.getOfferStatus()).ifPresent(existingOffer::setOfferStatus);
        // Add other fields as necessary for update.

        // Re-validate dates if they were updated
        if (existingOffer.getValidityStartDate() != null && existingOffer.getValidityEndDate() != null &&
            existingOffer.getValidityStartDate().isAfter(existingOffer.getValidityEndDate())) {
            throw new OfferValidationException("Updated Validity Start Date cannot be after End Date.");
        }

        existingOffer.setUpdatedAt(LocalDateTime.now());

        Offer updatedOffer = offerRepository.save(existingOffer);
        log.info("Offer ID: {} updated successfully.", offerId);
        return offerMapper.toResponseDTO(updatedOffer);
    }

    /**
     * Deletes an offer from the system.
     *
     * @param offerId The ID of the offer to delete.
     * @throws OfferNotFoundException If no offer is found with the given ID.
     */
    @Transactional
    public void deleteOffer(String offerId) {
        log.info("Attempting to delete offer with ID: {}", offerId);
        // Check if the offer exists before attempting to delete to provide a specific error.
        if (!offerRepository.existsByOfferId(offerId)) {
            log.warn("Offer not found for deletion with ID: {}", offerId);
            throw new OfferNotFoundException("Offer not found with ID: " + offerId);
        }
        // Assuming deleteByOfferId is defined in OfferRepository for direct deletion by ID.
        // Alternatively, find the entity and then delete:
        // Offer offerToDelete = offerRepository.findByOfferId(offerId).orElseThrow(...);
        // offerRepository.delete(offerToDelete);
        offerRepository.deleteByOfferId(offerId);
        log.info("Offer ID: {} deleted successfully.", offerId);
    }

    /**
     * Performs basic column-level validation on the incoming OfferRequestDTO.
     * This method ensures that essential fields are present and conform to basic rules.
     * More complex business validations might be handled elsewhere or within this method.
     *
     * @param requestDTO The DTO to validate.
     * @throws OfferValidationException If any validation rule is violated.
     */
    private void validateOfferRequest(OfferRequestDTO requestDTO) {
        if (requestDTO.getCustomerId() == null || requestDTO.getCustomerId().trim().isEmpty()) {
            throw new OfferValidationException("Customer ID cannot be null or empty.");
        }
        if (requestDTO.getCampaignId() == null || requestDTO.getCampaignId().trim().isEmpty()) {
            throw new OfferValidationException("Campaign ID cannot be null or empty.");
        }
        if (requestDTO.getOfferType() == null || requestDTO.getOfferType().trim().isEmpty()) {
            throw new OfferValidationException("Offer Type cannot be null or empty.");
        }
        if (requestDTO.getOfferAmount() == null || requestDTO.getOfferAmount().doubleValue() <= 0) {
            throw new OfferValidationException("Offer Amount must be positive.");
        }
        if (requestDTO.getValidityStartDate() == null) {
            throw new OfferValidationException("Validity Start Date cannot be null.");
        }
        if (requestDTO.getValidityEndDate() == null) {
            throw new OfferValidationException("Validity End Date cannot be null.");
        }
        if (requestDTO.getValidityStartDate().isAfter(requestDTO.getValidityEndDate())) {
            throw new OfferValidationException("Validity Start Date cannot be after End Date.");
        }
        log.debug("Offer request DTO validated successfully for customer ID: {}", requestDTO.getCustomerId());
    }

    /**
     * Placeholder for complex deduplication logic.
     * As per functional requirements:
     * - Apply dedupe logic across all Consumer Loan (CL) products (Loyalty, Preapproved, E-aggregator etc.).
     * - Perform deduplication against the 'live book' (Customer 360) before offers are finalized.
     * - Top-up loan offers must be deduped only within other Top-up offers, and matches found should be removed.
     *
     * This method would typically interact with a dedicated deduplication service
     * or a complex set of rules. It might update the offer's status (e.g., to REJECTED_DUPLICATE)
     * or throw an exception if the offer should not proceed.
     *
     * @param offer The offer entity to be checked for duplication.
     * @throws OfferValidationException If a duplicate is found and the offer should not be processed
     *                                  (e.g., if the business rule dictates immediate rejection).
     */
    private void performDeduplicationCheck(Offer offer) {
        log.debug("Performing deduplication check for offer ID: {}", offer.getOfferId());

        // Example placeholder logic for deduplication:
        // This section would be highly dependent on the exact deduplication rules and
        // integration with other services (like Customer 360).

        // 1. Check against existing offers for the same customer and product type.
        //    This would involve querying the offerRepository or a dedicated deduplication service.
        //    List<Offer> existingOffers = offerRepository.findByCustomerIdAndOfferTypeAndOfferStatusIn(
        //        offer.getCustomerId(), offer.getOfferType(), List.of(OfferStatus.ACTIVE, OfferStatus.PENDING));
        //    if (!existingOffers.isEmpty()) {
        //        // Apply specific dedupe rules (e.g., "Top-up loan offers deduped only within other Top-up offers")
        //        boolean isActualDuplicate = existingOffers.stream().anyMatch(existing -> {
        //            // Complex comparison logic based on offer details, amount, validity, etc.
        //            // For "Top-up loan offers must be deduped only within other Top-up offers":
        //            // if (offer.getOfferType().equals("TOP_UP_LOAN") && existing.getOfferType().equals("TOP_UP_LOAN")) {
        //            //     return existing.getOfferAmount().equals(offer.getOfferAmount()) && ...; // More specific rules
        //            // }
        //            // For other CL products, broader rules might apply.
        //            return existing.getOfferAmount().equals(offer.getOfferAmount()); // Simplified example
        //        });
        //        if (isActualDuplicate) {
        //            log.warn("Deduplication detected for offer ID: {}. Marking as REJECTED_DUPLICATE.", offer.getOfferId());
        //            offer.setOfferStatus(OfferStatus.REJECTED_DUPLICATE);
        //            // Optionally, throw an exception to prevent persistence if the business rule dictates
        //            // throw new OfferValidationException("Duplicate offer detected for customer: " + offer.getCustomerId());
        //        }
        //    }

        // 2. Check against 'live book' (Customer 360).
        //    This would involve calling a Customer 360 service to check if the customer
        //    already has active loans/products that conflict with this offer.
        //    For example:
        //    boolean conflictsWithLiveBook = customer360Service.checkConflict(offer.getCustomerId(), offer.getOfferType());
        //    if (conflictsWithLiveBook) {
        //        log.warn("Offer ID: {} conflicts with live book. Marking as REJECTED_LIVE_BOOK_CONFLICT.", offer.getOfferId());
        //        offer.setOfferStatus(OfferStatus.REJECTED_LIVE_BOOK_CONFLICT);
        //        // throw new OfferValidationException("Offer conflicts with existing live book products for customer " + offer.getCustomerId());
        //    }

        // If no duplicates or conflicts, the offer status remains as set (e.g., PENDING)
        log.debug("Deduplication check completed for offer ID: {}. Current status: {}", offer.getOfferId(), offer.getOfferStatus());
    }
}
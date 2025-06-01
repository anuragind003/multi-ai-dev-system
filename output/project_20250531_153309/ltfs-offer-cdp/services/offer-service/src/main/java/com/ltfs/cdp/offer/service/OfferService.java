package com.ltfs.cdp.offer.service;

import com.ltfs.cdp.offer.dto.OfferRequestDTO;
import com.ltfs.cdp.offer.dto.OfferResponseDTO;
import com.ltfs.cdp.offer.entity.Offer;
import com.ltfs.cdp.offer.exception.DeduplicationException;
import com.ltfs.cdp.offer.exception.ResourceNotFoundException;
import com.ltfs.cdp.offer.exception.ValidationException;
import com.ltfs.cdp.offer.mapper.OfferMapper;
import com.ltfs.cdp.offer.repository.OfferRepository;
import com.ltfs.cdp.offer.event.OfferCreatedEvent;
import com.ltfs.cdp.offer.event.OfferUpdatedEvent;
import com.ltfs.cdp.offer.service.deduplication.DeduplicationService;

import org.springframework.context.ApplicationEventPublisher;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.time.LocalDateTime;
import java.util.List;
import java.util.stream.Collectors;
import java.math.BigDecimal; // Assuming loanAmount might be BigDecimal

/**
 * Service class for managing Offer-related business logic.
 * This includes creation, retrieval, update, and deletion of offers,
 * along with integrating validation and deduplication processes.
 */
@Service
public class OfferService {

    private static final Logger log = LoggerFactory.getLogger(OfferService.class);

    private final OfferRepository offerRepository;
    private final OfferMapper offerMapper;
    private final DeduplicationService deduplicationService;
    private final ApplicationEventPublisher eventPublisher;

    /**
     * Constructs an OfferService with necessary dependencies.
     *
     * @param offerRepository The repository for Offer entities.
     * @param offerMapper The mapper for converting between Offer entities and DTOs.
     * @param deduplicationService The service responsible for performing deduplication checks.
     * @param eventPublisher The Spring ApplicationEventPublisher for publishing domain events.
     */
    public OfferService(OfferRepository offerRepository,
                        OfferMapper offerMapper,
                        DeduplicationService deduplicationService,
                        ApplicationEventPublisher eventPublisher) {
        this.offerRepository = offerRepository;
        this.offerMapper = offerMapper;
        this.deduplicationService = deduplicationService;
        this.eventPublisher = eventPublisher;
    }

    /**
     * Creates a new offer in the system.
     * This method performs basic column-level validation,
     * deduplication against the 'live book' (Customer 360),
     * and specific deduplication for 'Top-up' loan offers.
     * Upon successful creation, an {@link OfferCreatedEvent} is published.
     *
     * @param offerRequestDTO The data transfer object containing the details of the offer to be created.
     * @return An {@link OfferResponseDTO} representing the newly created offer.
     * @throws ValidationException If the input {@code offerRequestDTO} fails basic validation rules.
     * @throws DeduplicationException If the offer is identified as a duplicate based on business rules.
     */
    @Transactional
    public OfferResponseDTO createOffer(OfferRequestDTO offerRequestDTO) {
        log.info("Attempting to create offer for customer ID: {}", offerRequestDTO.getCustomerId());

        // 1. Perform basic column-level validation on the incoming DTO.
        validateOfferRequest(offerRequestDTO);

        // 2. Perform deduplication against the 'live book' (Customer 360).
        // This ensures that the offer is not a duplicate against existing customer profiles
        // across all Consumer Loan (CL) products (Loyalty, Preapproved, E-aggregator etc.).
        boolean isDuplicateAgainstLiveBook = deduplicationService.isDuplicateAgainstLiveBook(
                offerRequestDTO.getCustomerId(),
                offerRequestDTO.getProductType(),
                offerRequestDTO.getLoanAmount() != null ? offerRequestDTO.getLoanAmount() : BigDecimal.ZERO // Handle null loanAmount gracefully for dedupe check
        );

        if (isDuplicateAgainstLiveBook) {
            log.warn("Offer for customer ID {} is a duplicate against live book. Aborting creation.", offerRequestDTO.getCustomerId());
            throw new DeduplicationException("Offer is a duplicate against existing customer profiles (live book).");
        }

        // 3. Perform specific deduplication for 'Top-up' loan offers.
        // "Top-up loan offers must be deduped only within other Top-up offers, and matches found should be removed."
        // If a match is found, the current offer creation is aborted.
        if ("TOP_UP_LOAN".equalsIgnoreCase(offerRequestDTO.getProductType())) {
            boolean isDuplicateTopUp = deduplicationService.isDuplicateTopUpOffer(
                    offerRequestDTO.getCustomerId(),
                    offerRequestDTO.getProductType(),
                    offerRequestDTO.getLoanAmount() != null ? offerRequestDTO.getLoanAmount() : BigDecimal.ZERO
            );
            if (isDuplicateTopUp) {
                log.warn("Top-up offer for customer ID {} is a duplicate within other Top-up offers. Aborting creation.", offerRequestDTO.getCustomerId());
                throw new DeduplicationException("Top-up offer is a duplicate within other Top-up offers.");
            }
        }

        // Map the DTO to an entity and set initial system-managed fields.
        Offer offer = offerMapper.toEntity(offerRequestDTO);
        offer.setOfferStatus("PENDING_APPROVAL"); // Initial status, might change based on further processing
        offer.setCreatedAt(LocalDateTime.now());
        offer.setUpdatedAt(LocalDateTime.now());

        // Save the new offer to the database.
        Offer savedOffer = offerRepository.save(offer);
        log.info("Offer with ID {} created successfully for customer ID: {}", savedOffer.getOfferId(), savedOffer.getCustomerId());

        // Publish an event to notify other services or components about the new offer.
        // This is crucial for the event-driven architecture, enabling asynchronous processing
        // like final deduplication against Customer 360 after initial save, or campaign updates.
        eventPublisher.publishEvent(new OfferCreatedEvent(this, savedOffer.getOfferId(), savedOffer.getCustomerId(), savedOffer.getProductType()));

        return offerMapper.toDto(savedOffer);
    }

    /**
     * Retrieves a single offer by its unique identifier.
     *
     * @param offerId The unique ID of the offer to retrieve.
     * @return An {@link OfferResponseDTO} representing the found offer.
     * @throws ResourceNotFoundException If no offer exists with the given {@code offerId}.
     */
    public OfferResponseDTO getOfferById(String offerId) {
        log.info("Attempting to retrieve offer with ID: {}", offerId);
        Offer offer = offerRepository.findById(offerId)
                .orElseThrow(() -> {
                    log.warn("Offer with ID {} not found.", offerId);
                    return new ResourceNotFoundException("Offer not found with ID: " + offerId);
                });
        log.info("Successfully retrieved offer with ID: {}", offerId);
        return offerMapper.toDto(offer);
    }

    /**
     * Retrieves a list of all offers available in the system.
     *
     * @return A {@link List} of {@link OfferResponseDTO} representing all offers.
     */
    public List<OfferResponseDTO> getAllOffers() {
        log.info("Attempting to retrieve all offers.");
        List<Offer> offers = offerRepository.findAll();
        log.info("Retrieved {} offers.", offers.size());
        return offers.stream()
                .map(offerMapper::toDto)
                .collect(Collectors.toList());
    }

    /**
     * Updates an existing offer identified by its ID with new details.
     * This method performs basic validation on the update request.
     * Upon successful update, an {@link OfferUpdatedEvent} is published.
     *
     * @param offerId The unique ID of the offer to update.
     * @param offerRequestDTO The data transfer object containing the updated offer details.
     * @return An {@link OfferResponseDTO} representing the updated offer.
     * @throws ResourceNotFoundException If no offer exists with the given {@code offerId}.
     * @throws ValidationException If the input {@code offerRequestDTO} fails basic validation rules.
     */
    @Transactional
    public OfferResponseDTO updateOffer(String offerId, OfferRequestDTO offerRequestDTO) {
        log.info("Attempting to update offer with ID: {}", offerId);

        // 1. Validate the incoming DTO for update.
        validateOfferRequest(offerRequestDTO);

        // 2. Find the existing offer by ID.
        Offer existingOffer = offerRepository.findById(offerId)
                .orElseThrow(() -> {
                    log.warn("Offer with ID {} not found for update.", offerId);
                    return new ResourceNotFoundException("Offer not found with ID: " + offerId);
                });

        // 3. Apply updates from the DTO to the existing entity.
        // Note: Business rules might dictate which fields are updatable.
        // For simplicity, common fields are updated here.
        existingOffer.setCustomerId(offerRequestDTO.getCustomerId());
        existingOffer.setCampaignId(offerRequestDTO.getCampaignId());
        existingOffer.setProductType(offerRequestDTO.getProductType());
        existingOffer.setLoanAmount(offerRequestDTO.getLoanAmount());
        existingOffer.setInterestRate(offerRequestDTO.getInterestRate());
        existingOffer.setTenureMonths(offerRequestDTO.getTenureMonths());
        existingOffer.setOfferStatus(offerRequestDTO.getOfferStatus()); // Allow status to be updated
        existingOffer.setUpdatedAt(LocalDateTime.now()); // Update timestamp

        // 4. Save the updated offer to the database.
        Offer updatedOffer = offerRepository.save(existingOffer);
        log.info("Offer with ID {} updated successfully.", updatedOffer.getOfferId());

        // Publish an event to notify about the offer update.
        eventPublisher.publishEvent(new OfferUpdatedEvent(this, updatedOffer.getOfferId(), updatedOffer.getCustomerId(), updatedOffer.getOfferStatus()));

        return offerMapper.toDto(updatedOffer);
    }

    /**
     * Deletes an offer from the system by its unique identifier.
     *
     * @param offerId The unique ID of the offer to delete.
     * @throws ResourceNotFoundException If no offer exists with the given {@code offerId}.
     */
    @Transactional
    public void deleteOffer(String offerId) {
        log.info("Attempting to delete offer with ID: {}", offerId);
        if (!offerRepository.existsById(offerId)) {
            log.warn("Offer with ID {} not found for deletion.", offerId);
            throw new ResourceNotFoundException("Offer not found with ID: " + offerId);
        }
        offerRepository.deleteById(offerId);
        log.info("Offer with ID {} deleted successfully.", offerId);
        // Optionally, an OfferDeletedEvent could be published here if downstream systems need to react to deletions.
    }

    /**
     * Performs basic column-level validation on the {@link OfferRequestDTO}.
     * This method checks for null or empty required fields and validates numerical constraints.
     * This can be extended with more complex business rules specific to offer data.
     *
     * @param offerRequestDTO The DTO to validate.
     * @throws ValidationException If any required field is missing or invalid.
     */
    private void validateOfferRequest(OfferRequestDTO offerRequestDTO) {
        if (offerRequestDTO.getCustomerId() == null || offerRequestDTO.getCustomerId().trim().isEmpty()) {
            throw new ValidationException("Customer ID cannot be null or empty.");
        }
        if (offerRequestDTO.getCampaignId() == null || offerRequestDTO.getCampaignId().trim().isEmpty()) {
            throw new ValidationException("Campaign ID cannot be null or empty.");
        }
        if (offerRequestDTO.getProductType() == null || offerRequestDTO.getProductType().trim().isEmpty()) {
            throw new ValidationException("Product type cannot be null or empty.");
        }
        if (offerRequestDTO.getLoanAmount() == null || offerRequestDTO.getLoanAmount().compareTo(BigDecimal.ZERO) <= 0) {
            throw new ValidationException("Loan amount must be a positive value.");
        }
        if (offerRequestDTO.getInterestRate() == null || offerRequestDTO.getInterestRate().compareTo(BigDecimal.ZERO) < 0) {
            throw new ValidationException("Interest rate cannot be negative.");
        }
        if (offerRequestDTO.getTenureMonths() == null || offerRequestDTO.getTenureMonths() <= 0) {
            throw new ValidationException("Tenure in months must be a positive integer.");
        }
        if (offerRequestDTO.getOfferStatus() == null || offerRequestDTO.getOfferStatus().trim().isEmpty()) {
            throw new ValidationException("Offer status cannot be null or empty.");
        }
        // Further validation can be added here, e.g., enum validation for productType or offerStatus,
        // format validation for IDs, range checks for amounts/rates.
        log.debug("Offer request DTO validated successfully for customer ID: {}", offerRequestDTO.getCustomerId());
    }
}
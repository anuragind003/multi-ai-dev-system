package com.ltfs.cdp.offer.controller;

import com.ltfs.cdp.offer.dto.OfferRequestDTO;
import com.ltfs.cdp.offer.dto.OfferResponseDTO;
import com.ltfs.cdp.offer.dto.OfferStatusUpdateDTO;
import com.ltfs.cdp.offer.exception.InvalidOfferDataException;
import com.ltfs.cdp.offer.exception.OfferNotFoundException;
import com.ltfs.cdp.offer.service.OfferService;
import jakarta.validation.Valid;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;

/**
 * REST Controller for managing offer-related operations.
 * This controller handles requests for offer creation, status updates, and retrieval.
 * It acts as the entry point for the offer-service microservice, exposing RESTful APIs.
 */
@RestController
@RequestMapping("/api/v1/offers")
public class OfferController {

    private static final Logger log = LoggerFactory.getLogger(OfferController.class);

    private final OfferService offerService;

    /**
     * Constructs an OfferController with the necessary OfferService.
     * Spring's dependency injection automatically provides the OfferService instance.
     *
     * @param offerService The service layer component responsible for offer business logic.
     */
    public OfferController(OfferService offerService) {
        this.offerService = offerService;
    }

    /**
     * Creates a new offer based on the provided offer request data.
     * Performs basic validation on the incoming DTO.
     *
     * @param offerRequestDTO The DTO containing details for the new offer.
     * @return A ResponseEntity containing the created OfferResponseDTO and HTTP status 201 (Created).
     * @throws InvalidOfferDataException if the provided offer data is invalid.
     */
    @PostMapping
    public ResponseEntity<OfferResponseDTO> createOffer(@Valid @RequestBody OfferRequestDTO offerRequestDTO) {
        log.info("Received request to create offer for customer ID: {}", offerRequestDTO.getCustomerId());
        try {
            OfferResponseDTO createdOffer = offerService.createOffer(offerRequestDTO);
            log.info("Offer created successfully with ID: {}", createdOffer.getOfferId());
            return new ResponseEntity<>(createdOffer, HttpStatus.CREATED);
        } catch (InvalidOfferDataException e) {
            log.error("Validation error during offer creation: {}", e.getMessage());
            throw e; // Re-throw to be handled by a global exception handler if configured
        } catch (Exception e) {
            log.error("An unexpected error occurred while creating offer: {}", e.getMessage(), e);
            // For production, consider a more generic error DTO or specific exception handling
            return new ResponseEntity<>(HttpStatus.INTERNAL_SERVER_ERROR);
        }
    }

    /**
     * Retrieves an offer by its unique identifier.
     *
     * @param offerId The unique ID of the offer to retrieve.
     * @return A ResponseEntity containing the OfferResponseDTO if found, and HTTP status 200 (OK).
     * @throws OfferNotFoundException if no offer is found with the given ID.
     */
    @GetMapping("/{offerId}")
    public ResponseEntity<OfferResponseDTO> getOfferById(@PathVariable String offerId) {
        log.info("Received request to get offer by ID: {}", offerId);
        try {
            OfferResponseDTO offer = offerService.getOfferById(offerId);
            log.info("Successfully retrieved offer with ID: {}", offerId);
            return new ResponseEntity<>(offer, HttpStatus.OK);
        } catch (OfferNotFoundException e) {
            log.warn("Offer not found with ID: {}", offerId);
            throw e; // Re-throw to be handled by a global exception handler
        } catch (Exception e) {
            log.error("An unexpected error occurred while fetching offer with ID {}: {}", offerId, e.getMessage(), e);
            return new ResponseEntity<>(HttpStatus.INTERNAL_SERVER_ERROR);
        }
    }

    /**
     * Retrieves a list of offers associated with a specific customer ID.
     * This endpoint supports the single profile view requirement by fetching all offers for a customer.
     *
     * @param customerId The unique ID of the customer.
     * @return A ResponseEntity containing a list of OfferResponseDTOs and HTTP status 200 (OK).
     *         Returns an empty list if no offers are found for the customer.
     */
    @GetMapping("/customer/{customerId}")
    public ResponseEntity<List<OfferResponseDTO>> getOffersByCustomerId(@PathVariable String customerId) {
        log.info("Received request to get offers for customer ID: {}", customerId);
        try {
            List<OfferResponseDTO> offers = offerService.getOffersByCustomerId(customerId);
            if (offers.isEmpty()) {
                log.info("No offers found for customer ID: {}", customerId);
            } else {
                log.info("Found {} offers for customer ID: {}", offers.size(), customerId);
            }
            return new ResponseEntity<>(offers, HttpStatus.OK);
        } catch (Exception e) {
            log.error("An unexpected error occurred while fetching offers for customer ID {}: {}", customerId, e.getMessage(), e);
            return new ResponseEntity<>(HttpStatus.INTERNAL_SERVER_ERROR);
        }
    }

    /**
     * Updates the status of an existing offer.
     * This is crucial for managing the lifecycle of an offer (e.g., PENDING, APPROVED, REJECTED, EXPIRED).
     *
     * @param offerId The unique ID of the offer to update.
     * @param statusUpdateDTO The DTO containing the new status and any relevant details.
     * @return A ResponseEntity containing the updated OfferResponseDTO and HTTP status 200 (OK).
     * @throws OfferNotFoundException if no offer is found with the given ID.
     * @throws InvalidOfferDataException if the provided status update data is invalid.
     */
    @PutMapping("/{offerId}/status")
    public ResponseEntity<OfferResponseDTO> updateOfferStatus(@PathVariable String offerId,
                                                              @Valid @RequestBody OfferStatusUpdateDTO statusUpdateDTO) {
        log.info("Received request to update status for offer ID: {} to status: {}", offerId, statusUpdateDTO.getNewStatus());
        try {
            OfferResponseDTO updatedOffer = offerService.updateOfferStatus(offerId, statusUpdateDTO);
            log.info("Successfully updated status for offer ID: {} to {}", offerId, updatedOffer.getStatus());
            return new ResponseEntity<>(updatedOffer, HttpStatus.OK);
        } catch (OfferNotFoundException e) {
            log.warn("Offer not found for status update with ID: {}", offerId);
            throw e;
        } catch (InvalidOfferDataException e) {
            log.error("Invalid data for status update of offer ID {}: {}", offerId, e.getMessage());
            throw e;
        } catch (Exception e) {
            log.error("An unexpected error occurred while updating status for offer ID {}: {}", offerId, e.getMessage(), e);
            return new ResponseEntity<>(HttpStatus.INTERNAL_SERVER_ERROR);
        }
    }

    /**
     * Global exception handler for OfferNotFoundException.
     * Returns HTTP 404 Not Found when an offer is not found.
     *
     * @param ex The OfferNotFoundException that was thrown.
     * @return A ResponseEntity with an error message and HTTP status 404.
     */
    @ExceptionHandler(OfferNotFoundException.class)
    @ResponseStatus(HttpStatus.NOT_FOUND)
    public ResponseEntity<String> handleOfferNotFoundException(OfferNotFoundException ex) {
        log.error("Offer Not Found: {}", ex.getMessage());
        return new ResponseEntity<>(ex.getMessage(), HttpStatus.NOT_FOUND);
    }

    /**
     * Global exception handler for InvalidOfferDataException.
     * Returns HTTP 400 Bad Request when input data is invalid.
     *
     * @param ex The InvalidOfferDataException that was thrown.
     * @return A ResponseEntity with an error message and HTTP status 400.
     */
    @ExceptionHandler(InvalidOfferDataException.class)
    @ResponseStatus(HttpStatus.BAD_REQUEST)
    public ResponseEntity<String> handleInvalidOfferDataException(InvalidOfferDataException ex) {
        log.error("Invalid Offer Data: {}", ex.getMessage());
        return new ResponseEntity<>(ex.getMessage(), HttpStatus.BAD_REQUEST);
    }

    /**
     * Global exception handler for any other unexpected exceptions.
     * Returns HTTP 500 Internal Server Error.
     *
     * @param ex The Exception that was thrown.
     * @return A ResponseEntity with a generic error message and HTTP status 500.
     */
    @ExceptionHandler(Exception.class)
    @ResponseStatus(HttpStatus.INTERNAL_SERVER_ERROR)
    public ResponseEntity<String> handleGenericException(Exception ex) {
        log.error("An unexpected internal server error occurred: {}", ex.getMessage(), ex);
        return new ResponseEntity<>("An unexpected error occurred. Please try again later.", HttpStatus.INTERNAL_SERVER_ERROR);
    }
}
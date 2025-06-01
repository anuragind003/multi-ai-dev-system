package com.ltfs.cdp.offer.controller;

import com.ltfs.cdp.offer.dto.OfferRequestDTO;
import com.ltfs.cdp.offer.dto.OfferResponseDTO;
import com.ltfs.cdp.offer.exception.OfferNotFoundException;
import com.ltfs.cdp.offer.service.OfferService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.media.Content;
import io.swagger.v3.oas.annotations.media.Schema;
import io.swagger.v3.oas.annotations.responses.ApiResponse;
import io.swagger.v3.oas.annotations.responses.ApiResponses;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.validation.Valid;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;

/**
 * REST API controller for managing offer-related requests within the LTFS Offer CDP system.
 * This controller handles operations such as ingesting new offers, retrieving existing offers,
 * and triggering offer processing/deduplication based on campaign.
 *
 * It interacts with the {@link OfferService} to perform business logic and data operations.
 * All endpoints are prefixed with "/api/v1/offers".
 */
@RestController
@RequestMapping("/api/v1/offers")
@Tag(name = "Offer Management", description = "APIs for managing customer offers in LTFS CDP")
public class OfferController {

    private static final Logger log = LoggerFactory.getLogger(OfferController.class);

    private final OfferService offerService;

    /**
     * Constructs an OfferController with the necessary OfferService dependency.
     * Spring's dependency injection automatically provides the OfferService instance.
     *
     * @param offerService The service layer component for offer-related business logic.
     */
    public OfferController(OfferService offerService) {
        this.offerService = offerService;
    }

    /**
     * Ingests a new offer into the CDP system.
     * This endpoint receives offer data, performs basic validation, and delegates to the service layer
     * for further processing, including persistence and potential initial deduplication checks.
     *
     * @param offerRequestDTO The DTO containing the details of the offer to be created.
     *                        Must be a valid request body as per {@link OfferRequestDTO} constraints.
     * @return A ResponseEntity containing the created offer's response DTO and HTTP status 201 (Created).
     */
    @PostMapping
    @Operation(summary = "Ingest a new offer",
               description = "Receives and processes a new offer from external systems (e.g., Offermart) for CDP. " +
                             "Performs basic validation and initiates the offer lifecycle.",
               tags = {"Offer Management"})
    @ApiResponses(value = {
            @ApiResponse(responseCode = "201", description = "Offer successfully ingested",
                    content = @Content(mediaType = "application/json",
                            schema = @Schema(implementation = OfferResponseDTO.class))),
            @ApiResponse(responseCode = "400", description = "Invalid offer data provided (e.g., missing required fields, validation errors)",
                    content = @Content),
            @ApiResponse(responseCode = "500", description = "Internal server error during offer ingestion",
                    content = @Content)
    })
    public ResponseEntity<OfferResponseDTO> ingestOffer(@Valid @RequestBody OfferRequestDTO offerRequestDTO) {
        log.info("Received request to ingest new offer for customer ID: {}", offerRequestDTO.getCustomerId());
        OfferResponseDTO createdOffer = offerService.createOffer(offerRequestDTO);
        log.info("Offer with ID {} successfully ingested.", createdOffer.getOfferId());
        return new ResponseEntity<>(createdOffer, HttpStatus.CREATED);
    }

    /**
     * Retrieves a list of offers associated with a specific customer ID.
     * This endpoint allows fetching all offers that have been ingested and processed for a given customer.
     *
     * @param customerId The unique identifier of the customer for whom offers are to be retrieved.
     * @return A ResponseEntity containing a list of OfferResponseDTOs and HTTP status 200 (OK).
     *         Returns an empty list if no offers are found for the specified customer.
     */
    @GetMapping("/customer/{customerId}")
    @Operation(summary = "Get offers by customer ID",
               description = "Retrieves all offers associated with a given customer ID. " +
                             "Returns an empty list if no offers are found.",
               tags = {"Offer Management"})
    @ApiResponses(value = {
            @ApiResponse(responseCode = "200", description = "Successfully retrieved offers (list might be empty)",
                    content = @Content(mediaType = "application/json",
                            schema = @Schema(implementation = OfferResponseDTO.class))),
            @ApiResponse(responseCode = "500", description = "Internal server error during offer retrieval",
                    content = @Content)
    })
    public ResponseEntity<List<OfferResponseDTO>> getOffersByCustomerId(@PathVariable String customerId) {
        log.info("Received request to get offers for customer ID: {}", customerId);
        List<OfferResponseDTO> offers = offerService.getOffersByCustomerId(customerId);
        if (offers.isEmpty()) {
            log.warn("No offers found for customer ID: {}", customerId);
            // Returning 200 OK with an empty list is standard for "collection not found"
            // rather than 404 Not Found for the collection itself.
        } else {
            log.info("Found {} offers for customer ID: {}", offers.size(), customerId);
        }
        return new ResponseEntity<>(offers, HttpStatus.OK);
    }

    /**
     * Retrieves a single offer by its unique offer ID.
     * This endpoint provides detailed information for a specific offer.
     *
     * @param offerId The unique identifier of the offer to be retrieved.
     * @return A ResponseEntity containing the OfferResponseDTO and HTTP status 200 (OK).
     * @throws OfferNotFoundException If no offer is found with the given ID. This exception is
     *                                handled by the {@link #handleOfferNotFoundException(OfferNotFoundException)} method.
     */
    @GetMapping("/{offerId}")
    @Operation(summary = "Get offer by ID",
               description = "Retrieves a single offer by its unique identifier.",
               tags = {"Offer Management"})
    @ApiResponses(value = {
            @ApiResponse(responseCode = "200", description = "Successfully retrieved offer",
                    content = @Content(mediaType = "application/json",
                            schema = @Schema(implementation = OfferResponseDTO.class))),
            @ApiResponse(responseCode = "404", description = "Offer not found with the specified ID",
                    content = @Content),
            @ApiResponse(responseCode = "500", description = "Internal server error during offer retrieval",
                    content = @Content)
    })
    public ResponseEntity<OfferResponseDTO> getOfferById(@PathVariable String offerId) {
        log.info("Received request to get offer by ID: {}", offerId);
        // The service layer is expected to throw OfferNotFoundException if the offer is not found.
        OfferResponseDTO offer = offerService.getOfferById(offerId);
        log.info("Successfully retrieved offer with ID: {}", offerId);
        return new ResponseEntity<>(offer, HttpStatus.OK);
    }

    /**
     * Triggers the processing and deduplication of offers for a specific campaign.
     * This endpoint initiates the backend process to apply deduplication logic
     * and finalize offers for a given campaign, as per functional requirements.
     * This operation is typically asynchronous and returns an immediate acceptance status.
     *
     * @param campaignId The unique identifier of the campaign whose offers need processing.
     * @return A ResponseEntity indicating the status of the processing request (e.g., 202 Accepted).
     */
    @PostMapping("/process/campaign/{campaignId}")
    @Operation(summary = "Trigger offer processing for a campaign",
               description = "Initiates the deduplication and finalization process for offers belonging to a specific campaign. " +
                             "This is typically an asynchronous operation.",
               tags = {"Offer Management"})
    @ApiResponses(value = {
            @ApiResponse(responseCode = "202", description = "Offer processing request accepted and initiated",
                    content = @Content),
            @ApiResponse(responseCode = "400", description = "Invalid campaign ID or processing parameters",
                    content = @Content),
            @ApiResponse(responseCode = "500", description = "Internal server error during processing initiation",
                    content = @Content)
    })
    public ResponseEntity<String> triggerCampaignOfferProcessing(@PathVariable String campaignId) {
        log.info("Received request to trigger offer processing for campaign ID: {}", campaignId);
        // In a microservices architecture with event-driven components, this might
        // publish an event to a message queue (e.g., Kafka) for an async consumer
        // to pick up and process. For simplicity, we assume a direct service call.
        offerService.processOffersForCampaign(campaignId);
        log.info("Offer processing for campaign ID: {} initiated successfully.", campaignId);
        return new ResponseEntity<>("Offer processing for campaign " + campaignId + " initiated.", HttpStatus.ACCEPTED);
    }

    /**
     * Exception handler for {@link OfferNotFoundException}.
     * This method catches {@link OfferNotFoundException} thrown by the service layer
     * and translates it into an HTTP 404 Not Found response, providing a user-friendly message.
     *
     * @param ex The OfferNotFoundException that was thrown.
     * @return A ResponseEntity with an error message and HTTP status 404 (Not Found).
     */
    @ExceptionHandler(OfferNotFoundException.class)
    @ResponseStatus(HttpStatus.NOT_FOUND)
    public ResponseEntity<String> handleOfferNotFoundException(OfferNotFoundException ex) {
        log.error("Offer not found: {}", ex.getMessage());
        return new ResponseEntity<>(ex.getMessage(), HttpStatus.NOT_FOUND);
    }

    // Note: For broader error handling (e.g., validation errors like MethodArgumentNotValidException,
    // or generic RuntimeExceptions), a global @RestControllerAdvice class is typically used
    // to centralize exception handling across all controllers.
}
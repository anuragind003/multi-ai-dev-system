package com.ltfs.cdp.campaign.controller;

import com.ltfs.cdp.campaign.model.dto.CampaignRequestDTO;
import com.ltfs.cdp.campaign.model.dto.CampaignResponseDTO;
import com.ltfs.cdp.campaign.service.CampaignService;
import com.ltfs.cdp.campaign.exception.CampaignNotFoundException;
import com.ltfs.cdp.campaign.util.ApiResponse; // Assuming a common utility class for API responses

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import jakarta.validation.Valid; // For request body validation

import java.util.List;

/**
 * REST Controller for managing campaign-related operations in the LTFS Offer CDP system.
 * This controller handles requests for creating, updating, retrieving campaigns,
 * and triggering Moengage file generation.
 *
 * It interacts with the {@link CampaignService} to perform business logic.
 */
@RestController
@RequestMapping("/api/v1/campaigns")
public class CampaignController {

    private static final Logger logger = LoggerFactory.getLogger(CampaignController.class);

    private final CampaignService campaignService;

    /**
     * Constructs a new CampaignController with the given CampaignService.
     * Spring's dependency injection will automatically provide the CampaignService instance.
     *
     * @param campaignService The service layer component for campaign operations.
     */
    @Autowired
    public CampaignController(CampaignService campaignService) {
        this.campaignService = campaignService;
    }

    /**
     * Endpoint to create a new campaign.
     *
     * @param campaignRequestDTO The DTO containing campaign details for creation.
     *                           Must be valid according to its validation annotations.
     * @return ResponseEntity with an {@link ApiResponse} containing the created
     *         {@link CampaignResponseDTO} and HTTP status 201 (Created) on success.
     *         Returns 400 (Bad Request) if input is invalid (e.g., validation errors).
     *         Returns 500 (Internal Server Error) for unexpected server-side errors.
     */
    @PostMapping
    public ResponseEntity<ApiResponse<CampaignResponseDTO>> createCampaign(@Valid @RequestBody CampaignRequestDTO campaignRequestDTO) {
        logger.info("Received request to create campaign: {}", campaignRequestDTO.getCampaignName());
        try {
            CampaignResponseDTO createdCampaign = campaignService.createCampaign(campaignRequestDTO);
            logger.info("Campaign created successfully with ID: {}", createdCampaign.getCampaignId());
            return new ResponseEntity<>(new ApiResponse<>(true, "Campaign created successfully", createdCampaign), HttpStatus.CREATED);
        } catch (IllegalArgumentException e) {
            // Catches validation errors or business rule violations from service layer
            logger.error("Validation/Business rule error during campaign creation: {}", e.getMessage());
            return new ResponseEntity<>(new ApiResponse<>(false, e.getMessage(), null), HttpStatus.BAD_REQUEST);
        } catch (Exception e) {
            // Catches any other unexpected errors
            logger.error("An unexpected error occurred while creating campaign: {}", e.getMessage(), e);
            return new ResponseEntity<>(new ApiResponse<>(false, "Failed to create campaign due to an internal error.", null), HttpStatus.INTERNAL_SERVER_ERROR);
        }
    }

    /**
     * Endpoint to update an existing campaign.
     *
     * @param id The unique identifier of the campaign to update.
     * @param campaignRequestDTO The DTO containing updated campaign details.
     *                           Must be valid according to its validation annotations.
     * @return ResponseEntity with an {@link ApiResponse} containing the updated
     *         {@link CampaignResponseDTO} and HTTP status 200 (OK) on success.
     *         Returns 404 (Not Found) if the campaign with the given ID does not exist.
     *         Returns 400 (Bad Request) if input is invalid or business rules are violated.
     *         Returns 500 (Internal Server Error) for unexpected server-side errors.
     */
    @PutMapping("/{id}")
    public ResponseEntity<ApiResponse<CampaignResponseDTO>> updateCampaign(@PathVariable Long id, @Valid @RequestBody CampaignRequestDTO campaignRequestDTO) {
        logger.info("Received request to update campaign with ID: {}", id);
        try {
            CampaignResponseDTO updatedCampaign = campaignService.updateCampaign(id, campaignRequestDTO);
            logger.info("Campaign with ID {} updated successfully.", id);
            return new ResponseEntity<>(new ApiResponse<>(true, "Campaign updated successfully", updatedCampaign), HttpStatus.OK);
        } catch (CampaignNotFoundException e) {
            // Specific exception for when a campaign is not found
            logger.warn("Campaign not found for update with ID: {}", id);
            return new ResponseEntity<>(new ApiResponse<>(false, e.getMessage(), null), HttpStatus.NOT_FOUND);
        } catch (IllegalArgumentException e) {
            // Catches validation errors or business rule violations from service layer
            logger.error("Validation/Business rule error during campaign update for ID {}: {}", id, e.getMessage());
            return new ResponseEntity<>(new ApiResponse<>(false, e.getMessage(), null), HttpStatus.BAD_REQUEST);
        } catch (Exception e) {
            // Catches any other unexpected errors
            logger.error("An unexpected error occurred while updating campaign with ID {}: {}", id, e.getMessage(), e);
            return new ResponseEntity<>(new ApiResponse<>(false, "Failed to update campaign due to an internal error.", null), HttpStatus.INTERNAL_SERVER_ERROR);
        }
    }

    /**
     * Endpoint to retrieve a campaign by its unique identifier.
     *
     * @param id The unique identifier of the campaign to retrieve.
     * @return ResponseEntity with an {@link ApiResponse} containing the
     *         {@link CampaignResponseDTO} and HTTP status 200 (OK) on success.
     *         Returns 404 (Not Found) if the campaign with the given ID does not exist.
     *         Returns 500 (Internal Server Error) for unexpected server-side errors.
     */
    @GetMapping("/{id}")
    public ResponseEntity<ApiResponse<CampaignResponseDTO>> getCampaignById(@PathVariable Long id) {
        logger.info("Received request to get campaign by ID: {}", id);
        try {
            CampaignResponseDTO campaign = campaignService.getCampaignById(id);
            logger.info("Successfully retrieved campaign with ID: {}", id);
            return new ResponseEntity<>(new ApiResponse<>(true, "Campaign retrieved successfully", campaign), HttpStatus.OK);
        } catch (CampaignNotFoundException e) {
            // Specific exception for when a campaign is not found
            logger.warn("Campaign not found for ID: {}", id);
            return new ResponseEntity<>(new ApiResponse<>(false, e.getMessage(), null), HttpStatus.NOT_FOUND);
        } catch (Exception e) {
            // Catches any other unexpected errors
            logger.error("An unexpected error occurred while retrieving campaign with ID {}: {}", id, e.getMessage(), e);
            return new ResponseEntity<>(new ApiResponse<>(false, "Failed to retrieve campaign due to an internal error.", null), HttpStatus.INTERNAL_SERVER_ERROR);
        }
    }

    /**
     * Endpoint to retrieve all campaigns.
     *
     * @return ResponseEntity with an {@link ApiResponse} containing a list of
     *         {@link CampaignResponseDTO}s and HTTP status 200 (OK) on success.
     *         Returns 500 (Internal Server Error) for unexpected server-side errors.
     */
    @GetMapping
    public ResponseEntity<ApiResponse<List<CampaignResponseDTO>>> getAllCampaigns() {
        logger.info("Received request to get all campaigns.");
        try {
            List<CampaignResponseDTO> campaigns = campaignService.getAllCampaigns();
            logger.info("Successfully retrieved {} campaigns.", campaigns.size());
            return new ResponseEntity<>(new ApiResponse<>(true, "Campaigns retrieved successfully", campaigns), HttpStatus.OK);
        } catch (Exception e) {
            // Catches any unexpected errors
            logger.error("An unexpected error occurred while retrieving all campaigns: {}", e.getMessage(), e);
            return new ResponseEntity<>(new ApiResponse<>(false, "Failed to retrieve campaigns due to an internal error.", null), HttpStatus.INTERNAL_SERVER_ERROR);
        }
    }

    /**
     * Endpoint to trigger the generation of a Moengage file for a specific campaign.
     * This operation is typically asynchronous or long-running. For simplicity,
     * this endpoint returns 200 OK upon successful initiation of the file generation process.
     * In a real-world scenario, a 202 Accepted status might be more appropriate if the
     * file generation is queued for background processing.
     *
     * @param campaignId The unique identifier of the campaign for which to generate the Moengage file.
     * @return ResponseEntity with an {@link ApiResponse} indicating the status of the operation
     *         and HTTP status 200 (OK) on successful initiation.
     *         Returns 404 (Not Found) if the campaign does not exist.
     *         Returns 500 (Internal Server Error) for unexpected server-side errors.
     */
    @PostMapping("/generate-moengage-file/{campaignId}")
    public ResponseEntity<ApiResponse<String>> generateMoengageFile(@PathVariable Long campaignId) {
        logger.info("Received request to generate Moengage file for campaign ID: {}", campaignId);
        try {
            campaignService.generateMoengageFile(campaignId);
            logger.info("Moengage file generation initiated successfully for campaign ID: {}", campaignId);
            return new ResponseEntity<>(new ApiResponse<>(true, "Moengage file generation initiated successfully.", "File generation process started."), HttpStatus.OK);
        } catch (CampaignNotFoundException e) {
            // Specific exception for when a campaign is not found
            logger.warn("Campaign not found for Moengage file generation with ID: {}", campaignId);
            return new ResponseEntity<>(new ApiResponse<>(false, e.getMessage(), null), HttpStatus.NOT_FOUND);
        } catch (Exception e) {
            // Catches any other unexpected errors
            logger.error("An unexpected error occurred while generating Moengage file for campaign ID {}: {}", campaignId, e.getMessage(), e);
            return new ResponseEntity<>(new ApiResponse<>(false, "Failed to generate Moengage file due to an internal error.", null), HttpStatus.INTERNAL_SERVER_ERROR);
        }
    }
}
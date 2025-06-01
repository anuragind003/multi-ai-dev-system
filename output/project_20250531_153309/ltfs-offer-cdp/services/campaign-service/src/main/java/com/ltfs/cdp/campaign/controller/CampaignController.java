package com.ltfs.cdp.campaign.controller;

import com.ltfs.cdp.campaign.dto.CampaignDTO;
import com.ltfs.cdp.campaign.service.CampaignService;
import com.ltfs.cdp.campaign.exception.ResourceNotFoundException;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import javax.validation.Valid;
import java.util.List;

/**
 * REST API controller for managing campaign data within the LTFS Offer CDP system.
 * This controller provides endpoints for creating, retrieving, updating, and deleting campaign information.
 * It interacts with the {@link CampaignService} to perform business logic and data operations.
 *
 * <p>The base path for all campaign-related endpoints is {@code /api/campaigns}.</p>
 */
@RestController
@RequestMapping("/api/campaigns")
public class CampaignController {

    private final CampaignService campaignService;

    /**
     * Constructs a new CampaignController with the given CampaignService.
     * Spring's {@code @Autowired} annotation handles dependency injection,
     * providing the necessary service instance.
     *
     * @param campaignService The service layer component responsible for campaign business logic.
     */
    @Autowired
    public CampaignController(CampaignService campaignService) {
        this.campaignService = campaignService;
    }

    /**
     * Creates a new campaign in the system.
     *
     * <p>This endpoint accepts a {@link CampaignDTO} in the request body, validates it,
     * and then delegates to the {@link CampaignService} to persist the campaign data.</p>
     *
     * @param campaignDTO The {@link CampaignDTO} object containing the details of the campaign to be created.
     *                    The {@code @Valid} annotation ensures that the incoming DTO adheres to defined validation rules
     *                    (e.g., {@code @NotNull}, {@code @Size} on DTO fields).
     * @return A {@link ResponseEntity} containing the created {@link CampaignDTO} and HTTP status 201 (Created) on success.
     *         Returns HTTP status 500 (Internal Server Error) if an unexpected error occurs during creation.
     */
    @PostMapping
    public ResponseEntity<CampaignDTO> createCampaign(@Valid @RequestBody CampaignDTO campaignDTO) {
        try {
            CampaignDTO createdCampaign = campaignService.createCampaign(campaignDTO);
            return new ResponseEntity<>(createdCampaign, HttpStatus.CREATED);
        } catch (Exception e) {
            // In a production environment, a dedicated logging framework (e.g., SLF4J with Logback)
            // would be used here to log the exception details for debugging and monitoring.
            // Example: logger.error("Error creating campaign: {}", e.getMessage(), e);
            return new ResponseEntity<>(HttpStatus.INTERNAL_SERVER_ERROR);
        }
    }

    /**
     * Retrieves a campaign by its unique identifier.
     *
     * <p>This endpoint fetches a single campaign based on the provided ID from the path variable.</p>
     *
     * @param id The unique ID of the campaign to retrieve.
     * @return A {@link ResponseEntity} containing the {@link CampaignDTO} if found and HTTP status 200 (OK).
     *         Returns HTTP status 404 (Not Found) if no campaign exists with the given ID.
     *         Returns HTTP status 500 (Internal Server Error) if an unexpected error occurs during retrieval.
     */
    @GetMapping("/{id}")
    public ResponseEntity<CampaignDTO> getCampaignById(@PathVariable Long id) {
        try {
            CampaignDTO campaignDTO = campaignService.getCampaignById(id);
            return new ResponseEntity<>(campaignDTO, HttpStatus.OK);
        } catch (ResourceNotFoundException e) {
            // This specific exception indicates that the requested resource was not found.
            // It maps directly to an HTTP 404 Not Found status.
            return new ResponseEntity<>(HttpStatus.NOT_FOUND);
        } catch (Exception e) {
            // Log the exception for unexpected errors.
            return new ResponseEntity<>(HttpStatus.INTERNAL_SERVER_ERROR);
        }
    }

    /**
     * Retrieves all campaigns available in the system.
     *
     * <p>This endpoint returns a list of all campaigns without any specific filtering or pagination.</p>
     *
     * @return A {@link ResponseEntity} containing a list of all {@link CampaignDTO}s and HTTP status 200 (OK).
     *         Returns HTTP status 500 (Internal Server Error) if an unexpected error occurs during retrieval.
     */
    @GetMapping
    public ResponseEntity<List<CampaignDTO>> getAllCampaigns() {
        try {
            List<CampaignDTO> campaigns = campaignService.getAllCampaigns();
            return new ResponseEntity<>(campaigns, HttpStatus.OK);
        } catch (Exception e) {
            // Log the exception for unexpected errors.
            return new ResponseEntity<>(HttpStatus.INTERNAL_SERVER_ERROR);
        }
    }

    /**
     * Updates an existing campaign identified by its ID.
     *
     * <p>This endpoint accepts an ID from the path and a {@link CampaignDTO} in the request body.
     * It updates the campaign corresponding to the given ID with the new details provided in the DTO.</p>
     *
     * @param id The unique ID of the campaign to update.
     * @param campaignDTO The {@link CampaignDTO} object containing the updated details.
     *                    The {@code @Valid} annotation ensures that the incoming DTO adheres to defined validation rules.
     * @return A {@link ResponseEntity} containing the updated {@link CampaignDTO} and HTTP status 200 (OK) on success.
     *         Returns HTTP status 404 (Not Found) if the campaign does not exist.
     *         Returns HTTP status 500 (Internal Server Error) if an unexpected error occurs during the update.
     */
    @PutMapping("/{id}")
    public ResponseEntity<CampaignDTO> updateCampaign(@PathVariable Long id, @Valid @RequestBody CampaignDTO campaignDTO) {
        try {
            CampaignDTO updatedCampaign = campaignService.updateCampaign(id, campaignDTO);
            return new ResponseEntity<>(updatedCampaign, HttpStatus.OK);
        } catch (ResourceNotFoundException e) {
            // This specific exception indicates that the requested resource to update was not found.
            return new ResponseEntity<>(HttpStatus.NOT_FOUND);
        } catch (Exception e) {
            // Log the exception for unexpected errors.
            return new ResponseEntity<>(HttpStatus.INTERNAL_SERVER_ERROR);
        }
    }

    /**
     * Deletes a campaign identified by its ID.
     *
     * <p>This endpoint removes a campaign from the system based on the provided ID.</p>
     *
     * @param id The unique ID of the campaign to delete.
     * @return A {@link ResponseEntity} with HTTP status 204 (No Content) on successful deletion.
     *         Returns HTTP status 404 (Not Found) if the campaign does not exist.
     *         Returns HTTP status 500 (Internal Server Error) if an unexpected error occurs during deletion.
     */
    @DeleteMapping("/{id}")
    public ResponseEntity<Void> deleteCampaign(@PathVariable Long id) {
        try {
            campaignService.deleteCampaign(id);
            return new ResponseEntity<>(HttpStatus.NO_CONTENT); // 204 No Content indicates successful processing with no content to return.
        } catch (ResourceNotFoundException e) {
            // This specific exception indicates that the requested resource to delete was not found.
            return new ResponseEntity<>(HttpStatus.NOT_FOUND);
        } catch (Exception e) {
            // Log the exception for unexpected errors.
            return new ResponseEntity<>(HttpStatus.INTERNAL_SERVER_ERROR);
        }
    }
}
package com.ltfs.cdp.campaign.service;

import com.ltfs.cdp.campaign.dto.CampaignDTO;
import com.ltfs.cdp.campaign.exception.ResourceNotFoundException;
import com.ltfs.cdp.campaign.mapper.CampaignMapper;
import com.ltfs.cdp.campaign.model.Campaign;
import com.ltfs.cdp.campaign.repository.CampaignRepository;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;
import java.util.List;
import java.util.Optional;
import java.util.stream.Collectors;

/**
 * Service class for managing campaign-related operations.
 * This service handles business logic for creating, retrieving, updating, and deleting campaigns,
 * as well as managing campaign metrics. It interacts with the CampaignRepository for data persistence
 * and uses CampaignMapper for DTO-entity conversions.
 */
@Service
public class CampaignService {

    private static final Logger logger = LoggerFactory.getLogger(CampaignService.class);

    private final CampaignRepository campaignRepository;
    private final CampaignMapper campaignMapper;

    /**
     * Constructs a new CampaignService with the given repository and mapper.
     * Spring's dependency injection automatically provides these beans.
     *
     * @param campaignRepository The repository for Campaign entities.
     * @param campaignMapper     The mapper for converting between Campaign entities and DTOs.
     */
    @Autowired
    public CampaignService(CampaignRepository campaignRepository, CampaignMapper campaignMapper) {
        this.campaignRepository = campaignRepository;
        this.campaignMapper = campaignMapper;
    }

    /**
     * Creates a new campaign in the system.
     * Performs basic validation on the input DTO and sets creation/update timestamps.
     *
     * @param campaignDTO The DTO containing the details of the campaign to be created.
     * @return The DTO of the newly created campaign, including its generated ID.
     * @throws IllegalArgumentException if the campaignDTO is null or contains invalid data (e.g., empty name or type).
     */
    @Transactional
    public CampaignDTO createCampaign(CampaignDTO campaignDTO) {
        if (campaignDTO == null) {
            logger.error("Attempted to create campaign with null DTO.");
            throw new IllegalArgumentException("Campaign DTO cannot be null.");
        }
        // Basic validation for critical fields
        if (campaignDTO.getCampaignName() == null || campaignDTO.getCampaignName().trim().isEmpty()) {
            logger.error("Campaign name is null or empty for new campaign creation.");
            throw new IllegalArgumentException("Campaign name cannot be empty.");
        }
        if (campaignDTO.getCampaignType() == null || campaignDTO.getCampaignType().trim().isEmpty()) {
            logger.error("Campaign type is null or empty for new campaign creation.");
            throw new IllegalArgumentException("Campaign type cannot be empty.");
        }

        logger.info("Attempting to create new campaign: {}", campaignDTO.getCampaignName());
        Campaign campaign = campaignMapper.toEntity(campaignDTO);
        
        // Set creation and update timestamps
        campaign.setCreatedAt(LocalDateTime.now());
        campaign.setUpdatedAt(LocalDateTime.now());
        
        // Set initial status if not provided, e.g., "DRAFT"
        if (campaign.getStatus() == null || campaign.getStatus().trim().isEmpty()) {
            campaign.setStatus("DRAFT");
        }

        Campaign savedCampaign = campaignRepository.save(campaign);
        logger.info("Campaign created successfully with ID: {}", savedCampaign.getCampaignId());
        return campaignMapper.toDto(savedCampaign);
    }

    /**
     * Retrieves a campaign by its unique identifier.
     *
     * @param campaignId The ID of the campaign to retrieve.
     * @return The DTO of the found campaign.
     * @throws ResourceNotFoundException if no campaign is found with the given ID.
     */
    @Transactional(readOnly = true)
    public CampaignDTO getCampaignById(Long campaignId) {
        logger.debug("Attempting to retrieve campaign with ID: {}", campaignId);
        return campaignRepository.findById(campaignId)
                .map(campaignMapper::toDto)
                .orElseThrow(() -> {
                    logger.warn("Campaign not found with ID: {}", campaignId);
                    return new ResourceNotFoundException("Campaign not found with ID: " + campaignId);
                });
    }

    /**
     * Retrieves all campaigns, supporting pagination and sorting.
     *
     * @param pageable Pagination information (page number, size, sort order).
     *                 If null, all campaigns will be returned without pagination (though typically a Pageable is always provided).
     * @return A {@link Page} of {@link CampaignDTO} objects, representing a paginated list of campaigns.
     */
    @Transactional(readOnly = true)
    public Page<CampaignDTO> getAllCampaigns(Pageable pageable) {
        logger.debug("Retrieving all campaigns with pageable: {}", pageable);
        Page<Campaign> campaignsPage = campaignRepository.findAll(pageable);
        // Map the Page of Campaign entities to a Page of CampaignDTOs
        return campaignsPage.map(campaignMapper::toDto);
    }

    /**
     * Updates an existing campaign identified by its ID.
     * The method retrieves the existing campaign, updates its fields based on the provided DTO,
     * and then saves the changes.
     *
     * @param campaignId   The ID of the campaign to update.
     * @param campaignDTO The DTO containing the updated campaign details.
     * @return The DTO of the updated campaign.
     * @throws ResourceNotFoundException if no campaign is found with the given ID.
     * @throws IllegalArgumentException if the campaignDTO is null or contains invalid data (e.g., empty name or type).
     */
    @Transactional
    public CampaignDTO updateCampaign(Long campaignId, CampaignDTO campaignDTO) {
        if (campaignDTO == null) {
            logger.error("Attempted to update campaign ID {} with null DTO.", campaignId);
            throw new IllegalArgumentException("Campaign DTO cannot be null for update.");
        }
        // Basic validation for critical fields
        if (campaignDTO.getCampaignName() == null || campaignDTO.getCampaignName().trim().isEmpty()) {
            logger.error("Campaign name is null or empty for campaign ID {}.", campaignId);
            throw new IllegalArgumentException("Campaign name cannot be empty.");
        }
        if (campaignDTO.getCampaignType() == null || campaignDTO.getCampaignType().trim().isEmpty()) {
            logger.error("Campaign type is null or empty for campaign ID {}.", campaignId);
            throw new IllegalArgumentException("Campaign type cannot be empty.");
        }

        logger.info("Attempting to update campaign with ID: {}", campaignId);
        return campaignRepository.findById(campaignId)
                .map(existingCampaign -> {
                    // Use MapStruct mapper to update fields from DTO to existing entity
                    // This handles null values in DTO by ignoring them if configured in mapper
                    campaignMapper.updateEntityFromDto(campaignDTO, existingCampaign);
                    existingCampaign.setUpdatedAt(LocalDateTime.now()); // Update timestamp

                    Campaign updatedCampaign = campaignRepository.save(existingCampaign);
                    logger.info("Campaign with ID {} updated successfully.", campaignId);
                    return campaignMapper.toDto(updatedCampaign);
                })
                .orElseThrow(() -> {
                    logger.warn("Campaign not found for update with ID: {}", campaignId);
                    return new ResourceNotFoundException("Campaign not found with ID: " + campaignId);
                });
    }

    /**
     * Deletes a campaign by its unique identifier.
     *
     * @param campaignId The ID of the campaign to delete.
     * @throws ResourceNotFoundException if no campaign is found with the given ID.
     */
    @Transactional
    public void deleteCampaign(Long campaignId) {
        logger.info("Attempting to delete campaign with ID: {}", campaignId);
        if (!campaignRepository.existsById(campaignId)) {
            logger.warn("Campaign not found for deletion with ID: {}", campaignId);
            throw new ResourceNotFoundException("Campaign not found with ID: " + campaignId);
        }
        campaignRepository.deleteById(campaignId);
        logger.info("Campaign with ID {} deleted successfully.", campaignId);
    }

    /**
     * Updates the status of a specific campaign.
     * This method can be used to change a campaign's state (e.g., from DRAFT to ACTIVE, or ACTIVE to COMPLETED).
     *
     * @param campaignId The ID of the campaign whose status is to be updated.
     * @param newStatus  The new status string to set for the campaign.
     * @return The DTO of the updated campaign.
     * @throws ResourceNotFoundException if no campaign is found with the given ID.
     * @throws IllegalArgumentException if the newStatus is null or empty.
     */
    @Transactional
    public CampaignDTO updateCampaignStatus(Long campaignId, String newStatus) {
        if (newStatus == null || newStatus.trim().isEmpty()) {
            logger.error("Attempted to update campaign status for ID {} with null or empty status.", campaignId);
            throw new IllegalArgumentException("New status cannot be null or empty.");
        }

        logger.info("Updating status for campaign ID {} to: {}", campaignId, newStatus);
        return campaignRepository.findById(campaignId)
                .map(existingCampaign -> {
                    existingCampaign.setStatus(newStatus);
                    existingCampaign.setUpdatedAt(LocalDateTime.now()); // Update timestamp
                    Campaign updatedCampaign = campaignRepository.save(existingCampaign);
                    logger.info("Campaign ID {} status updated to {}.", campaignId, newStatus);
                    return campaignMapper.toDto(updatedCampaign);
                })
                .orElseThrow(() -> {
                    logger.warn("Campaign not found for status update with ID: {}", campaignId);
                    return new ResourceNotFoundException("Campaign not found with ID: " + campaignId);
                });
    }

    /**
     * Retrieves key metrics for a specific campaign.
     * In a real-world scenario, this method would involve more complex logic,
     * potentially aggregating data from other services (e.g., offer service for offer distribution,
     * customer service for engagement data) or performing complex database queries
     * to calculate performance indicators like conversion rates, reach, etc.
     * For this implementation, it simply returns the campaign's DTO, assuming
     * any basic metrics might be part of the campaign's own data or that a more
     * detailed metrics object would be fetched/constructed separately.
     *
     * @param campaignId The ID of the campaign for which to retrieve metrics.
     * @return The DTO of the campaign, which might contain basic metric-related fields.
     * @throws ResourceNotFoundException if no campaign is found with the given ID.
     */
    @Transactional(readOnly = true)
    public CampaignDTO getCampaignMetrics(Long campaignId) {
        logger.info("Retrieving metrics for campaign ID: {}", campaignId);
        // Placeholder for actual metrics logic.
        // For now, we return the campaign DTO itself.
        return campaignRepository.findById(campaignId)
                .map(campaignMapper::toDto)
                .orElseThrow(() -> {
                    logger.warn("Campaign not found for metrics retrieval with ID: {}", campaignId);
                    return new ResourceNotFoundException("Campaign not found with ID: " + campaignId);
                });
    }
}
package com.ltfs.cdp.campaign.service;

import com.ltfs.cdp.campaign.exception.ResourceNotFoundException;
import com.ltfs.cdp.campaign.model.Campaign;
import com.ltfs.cdp.campaign.model.CampaignStatus;
import com.ltfs.cdp.campaign.repository.CampaignRepository;
import com.ltfs.cdp.campaign.dto.CampaignRequestDTO;
import com.ltfs.cdp.campaign.dto.CampaignResponseDTO;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;
import java.util.List;
import java.util.Optional;
import java.util.stream.Collectors;

/**
 * Service class for managing Campaign-related business logic within the LTFS Offer CDP system.
 * This service handles CRUD operations for campaigns and applies business rules
 * related to campaign lifecycle and data integrity, ensuring consistency and
 * adherence to functional requirements like uniqueness of campaign codes.
 */
@Service
public class CampaignService {

    private static final Logger logger = LoggerFactory.getLogger(CampaignService.class);

    private final CampaignRepository campaignRepository;

    /**
     * Constructor injection for CampaignRepository.
     * Spring's @Autowired annotation ensures that an instance of CampaignRepository
     * is provided by the Spring IoC container.
     *
     * @param campaignRepository The repository for Campaign entities, enabling database interactions.
     */
    @Autowired
    public CampaignService(CampaignRepository campaignRepository) {
        this.campaignRepository = campaignRepository;
    }

    /**
     * Creates a new campaign based on the provided CampaignRequestDTO.
     * Ensures that no two campaigns share the same campaign code to maintain data integrity.
     * The initial status of a newly created campaign is set to DRAFT.
     *
     * @param requestDTO The Data Transfer Object containing the details for the new campaign.
     * @return A CampaignResponseDTO representing the newly created campaign, including its generated ID and timestamps.
     * @throws IllegalArgumentException if a campaign with the same campaign code already exists.
     */
    @Transactional
    public CampaignResponseDTO createCampaign(CampaignRequestDTO requestDTO) {
        logger.info("Attempting to create a new campaign with code: {}", requestDTO.getCampaignCode());

        // Validate uniqueness of campaign code before persisting
        if (campaignRepository.findByCampaignCode(requestDTO.getCampaignCode()).isPresent()) {
            logger.warn("Campaign creation failed: A campaign with code '{}' already exists.", requestDTO.getCampaignCode());
            throw new IllegalArgumentException("Campaign with code '" + requestDTO.getCampaignCode() + "' already exists.");
        }

        Campaign campaign = new Campaign();
        campaign.setCampaignName(requestDTO.getCampaignName());
        campaign.setCampaignCode(requestDTO.getCampaignCode());
        campaign.setDescription(requestDTO.getDescription());
        campaign.setStartDate(requestDTO.getStartDate());
        campaign.setEndDate(requestDTO.getEndDate());
        campaign.setStatus(CampaignStatus.DRAFT); // Default status for new campaigns
        campaign.setCreatedAt(LocalDateTime.now());
        campaign.setUpdatedAt(LocalDateTime.now());

        Campaign savedCampaign = campaignRepository.save(campaign);
        logger.info("Successfully created campaign with ID: {}", savedCampaign.getId());
        return convertToDto(savedCampaign);
    }

    /**
     * Retrieves a campaign by its unique identifier.
     * This operation is read-only and does not modify the database state.
     *
     * @param id The unique ID of the campaign to retrieve.
     * @return A CampaignResponseDTO representing the found campaign.
     * @throws ResourceNotFoundException if no campaign is found with the given ID.
     */
    @Transactional(readOnly = true)
    public CampaignResponseDTO getCampaignById(Long id) {
        logger.debug("Attempting to retrieve campaign with ID: {}", id);
        Campaign campaign = campaignRepository.findById(id)
                .orElseThrow(() -> {
                    logger.warn("Campaign not found with ID: {}", id);
                    return new ResourceNotFoundException("Campaign not found with ID: " + id);
                });
        logger.debug("Successfully retrieved campaign with ID: {}", id);
        return convertToDto(campaign);
    }

    /**
     * Retrieves all campaigns stored in the system.
     * This operation is read-only and does not modify the database state.
     *
     * @return A list of CampaignResponseDTOs, each representing a campaign.
     */
    @Transactional(readOnly = true)
    public List<CampaignResponseDTO> getAllCampaigns() {
        logger.debug("Attempting to retrieve all campaigns.");
        List<Campaign> campaigns = campaignRepository.findAll();
        logger.debug("Retrieved {} campaigns.", campaigns.size());
        return campaigns.stream()
                .map(this::convertToDto)
                .collect(Collectors.toList());
    }

    /**
     * Updates an existing campaign identified by its ID with the details provided in the DTO.
     * Ensures that if the campaign code is changed, it does not conflict with another existing campaign's code.
     *
     * @param id The ID of the campaign to update.
     * @param requestDTO The DTO containing the updated campaign details.
     * @return A CampaignResponseDTO representing the updated campaign.
     * @throws ResourceNotFoundException if no campaign is found with the given ID.
     * @throws IllegalArgumentException if the updated campaign code conflicts with another existing campaign.
     */
    @Transactional
    public CampaignResponseDTO updateCampaign(Long id, CampaignRequestDTO requestDTO) {
        logger.info("Attempting to update campaign with ID: {}", id);

        Campaign existingCampaign = campaignRepository.findById(id)
                .orElseThrow(() -> {
                    logger.warn("Campaign update failed: Campaign not found with ID: {}", id);
                    return new ResourceNotFoundException("Campaign not found with ID: " + id);
                });

        // Check if the new campaign code conflicts with another campaign (excluding itself)
        if (!existingCampaign.getCampaignCode().equals(requestDTO.getCampaignCode())) {
            Optional<Campaign> campaignWithSameCode = campaignRepository.findByCampaignCode(requestDTO.getCampaignCode());
            if (campaignWithSameCode.isPresent() && !campaignWithSameCode.get().getId().equals(id)) {
                logger.warn("Campaign update failed: Another campaign with code '{}' already exists.", requestDTO.getCampaignCode());
                throw new IllegalArgumentException("Another campaign with code '" + requestDTO.getCampaignCode() + "' already exists.");
            }
        }

        existingCampaign.setCampaignName(requestDTO.getCampaignName());
        existingCampaign.setCampaignCode(requestDTO.getCampaignCode());
        existingCampaign.setDescription(requestDTO.getDescription());
        existingCampaign.setStartDate(requestDTO.getStartDate());
        existingCampaign.setEndDate(requestDTO.getEndDate());
        // Allow status update if provided in DTO, otherwise keep existing status.
        // More complex status transitions can be handled by updateCampaignStatus method.
        if (requestDTO.getStatus() != null) {
            existingCampaign.setStatus(requestDTO.getStatus());
        }
        existingCampaign.setUpdatedAt(LocalDateTime.now());

        Campaign updatedCampaign = campaignRepository.save(existingCampaign);
        logger.info("Successfully updated campaign with ID: {}", updatedCampaign.getId());
        return convertToDto(updatedCampaign);
    }

    /**
     * Deletes a campaign by its unique identifier.
     *
     * @param id The ID of the campaign to delete.
     * @throws ResourceNotFoundException if no campaign is found with the given ID.
     */
    @Transactional
    public void deleteCampaign(Long id) {
        logger.info("Attempting to delete campaign with ID: {}", id);
        if (!campaignRepository.existsById(id)) {
            logger.warn("Campaign deletion failed: Campaign not found with ID: {}", id);
            throw new ResourceNotFoundException("Campaign not found with ID: " + id);
        }
        campaignRepository.deleteById(id);
        logger.info("Successfully deleted campaign with ID: {}", id);
    }

    /**
     * Updates the status of a specific campaign.
     * This method provides a dedicated way to manage campaign lifecycle states (e.g., DRAFT, ACTIVE, COMPLETED).
     * Includes basic validation for status transitions.
     *
     * @param id The ID of the campaign whose status is to be updated.
     * @param newStatus The new status to set for the campaign.
     * @return A CampaignResponseDTO representing the campaign with its updated status.
     * @throws ResourceNotFoundException if no campaign is found with the given ID.
     * @throws IllegalArgumentException if the requested status transition is invalid (e.g., trying to activate an already completed campaign).
     */
    @Transactional
    public CampaignResponseDTO updateCampaignStatus(Long id, CampaignStatus newStatus) {
        logger.info("Attempting to update status for campaign ID {} to {}", id, newStatus);
        Campaign existingCampaign = campaignRepository.findById(id)
                .orElseThrow(() -> {
                    logger.warn("Campaign status update failed: Campaign not found with ID: {}", id);
                    return new ResourceNotFoundException("Campaign not found with ID: " + id);
                });

        // Basic status transition validation. This can be expanded into a more robust
        // state machine pattern if campaign lifecycle rules become complex.
        if (existingCampaign.getStatus() == CampaignStatus.COMPLETED && newStatus != CampaignStatus.ARCHIVED) {
            logger.warn("Invalid status transition for campaign ID {}: Cannot change from COMPLETED to {}", id, newStatus);
            throw new IllegalArgumentException("Cannot change status of a COMPLETED campaign to anything other than ARCHIVED.");
        }
        // Example: Prevent activating a campaign if its start date is in the future
        // if (newStatus == CampaignStatus.ACTIVE && existingCampaign.getStartDate().isAfter(LocalDate.now())) {
        //     throw new IllegalArgumentException("Cannot activate a campaign whose start date is in the future.");
        // }

        existingCampaign.setStatus(newStatus);
        existingCampaign.setUpdatedAt(LocalDateTime.now());

        Campaign updatedCampaign = campaignRepository.save(existingCampaign);
        logger.info("Successfully updated status for campaign ID {} to {}", updatedCampaign.getId(), newStatus);
        return convertToDto(updatedCampaign);
    }

    /**
     * Converts a Campaign entity object to a CampaignResponseDTO object.
     * This helper method encapsulates the mapping logic, ensuring that only
     * necessary and appropriate data is exposed through the API.
     *
     * @param campaign The Campaign entity to convert.
     * @return The corresponding CampaignResponseDTO.
     */
    private CampaignResponseDTO convertToDto(Campaign campaign) {
        return new CampaignResponseDTO(
                campaign.getId(),
                campaign.getCampaignName(),
                campaign.getCampaignCode(),
                campaign.getDescription(),
                campaign.getStartDate(),
                campaign.getEndDate(),
                campaign.getStatus(),
                campaign.getCreatedAt(),
                campaign.getUpdatedAt()
        );
    }
}
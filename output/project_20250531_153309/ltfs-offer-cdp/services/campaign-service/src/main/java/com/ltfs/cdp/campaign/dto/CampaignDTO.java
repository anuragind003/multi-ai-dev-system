package com.ltfs.cdp.campaign.dto;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.LocalDateTime;
import java.util.UUID;

/**
 * Data Transfer Object (DTO) for Campaign entities.
 * This class is used to transfer campaign-related data between different layers
 * of the application, such as from the controller to the service, or between microservices.
 * It encapsulates the essential attributes of a campaign, facilitating data exchange
 * without exposing internal entity details.
 */
@Data // Lombok annotation to automatically generate getters, setters, toString(), equals(), and hashCode() methods.
@NoArgsConstructor // Lombok annotation to generate a no-argument constructor.
@AllArgsConstructor // Lombok annotation to generate a constructor with all fields as arguments.
@Builder // Lombok annotation to provide a builder pattern for object creation, enhancing readability and flexibility.
public class CampaignDTO {

    /**
     * Unique identifier for the campaign.
     * Using UUID (Universally Unique Identifier) ensures global uniqueness,
     * which is beneficial in distributed microservices architectures.
     */
    private UUID campaignId;

    /**
     * The name of the campaign.
     * This is a human-readable identifier for the campaign.
     * Example: "Diwali Loan Offer 2025", "Summer Personal Loan Campaign"
     */
    private String campaignName;

    /**
     * A detailed description of the campaign.
     * Provides more context about the campaign's objectives or specifics.
     */
    private String campaignDescription;

    /**
     * The type of product associated with this campaign.
     * This field is critical for applying specific deduplication logic
     * as per functional requirements (e.g., "Consumer Loan", "Top-up Loan",
     * "Loyalty", "Preapproved", "E-aggregator").
     */
    private String productType;

    /**
     * The start date and time of the campaign.
     * Uses {@link java.time.LocalDateTime} for precise date and time representation.
     */
    private LocalDateTime startDate;

    /**
     * The end date and time of the campaign.
     * Uses {@link java.time.LocalDateTime} for precise date and time representation.
     */
    private LocalDateTime endDate;

    /**
     * The current status of the campaign.
     * Examples: "ACTIVE", "INACTIVE", "PLANNED", "COMPLETED", "CANCELLED".
     * This can be used to control campaign visibility and eligibility.
     */
    private String status;

    /**
     * The identifier of the user or system that created this campaign record.
     */
    private String createdBy;

    /**
     * The timestamp when this campaign record was created.
     * Automatically recorded upon initial creation.
     */
    private LocalDateTime createdAt;

    /**
     * The identifier of the user or system that last updated this campaign record.
     */
    private String updatedBy;

    /**
     * The timestamp when this campaign record was last updated.
     * Automatically updated upon any modification to the record.
     */
    private LocalDateTime updatedAt;
}
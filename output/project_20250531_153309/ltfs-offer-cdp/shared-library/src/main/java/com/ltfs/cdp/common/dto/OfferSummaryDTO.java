package com.ltfs.cdp.common.dto;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.LocalDate;
import java.time.LocalDateTime;
import java.util.UUID;

/**
 * Data Transfer Object (DTO) for a summary view of an offer.
 * This DTO is designed to provide essential offer information for lists,
 * dashboards, or cross-service queries, minimizing data transfer overhead.
 * It encapsulates key attributes relevant to an offer's identity, status,
 * and its association with customers and campaigns, with a focus on
 * deduplication status as per project requirements.
 */
@Data // Lombok annotation to generate getters, setters, equals, hashCode, and toString methods
@NoArgsConstructor // Lombok annotation to generate a no-argument constructor
@AllArgsConstructor // Lombok annotation to generate a constructor with all fields
public class OfferSummaryDTO {

    /**
     * Unique identifier for the offer instance.
     * This ID uniquely identifies a specific offer generated for a customer
     * within the CDP system. Using UUID ensures global uniqueness across distributed services.
     */
    private UUID offerId;

    /**
     * A business-friendly code or identifier for the offer type.
     * E.g., "PL_PREAPP_2024_Q3", "HL_TOPUP_AUG". This code typically represents
     * the offer template or product type.
     */
    private String offerCode;

    /**
     * A descriptive name for the offer, providing a human-readable title.
     * E.g., "Pre-Approved Personal Loan Offer", "Home Loan Top-up Scheme".
     */
    private String offerName;

    /**
     * The current status of the offer within the CDP lifecycle.
     * Examples: "ACTIVE", "EXPIRED", "PENDING_DEDUP", "DEDUPED_OUT", "FINALIZED", "REJECTED".
     * This status reflects the offer's overall state.
     */
    private String offerStatus;

    /**
     * The unique identifier of the customer to whom this offer is targeted.
     * This is crucial for providing a single profile view and for linking offers
     * to specific customer records, especially during deduplication.
     */
    private UUID customerId;

    /**
     * The unique identifier of the campaign from which this offer originated.
     * This links the offer back to its marketing or business initiative.
     */
    private UUID campaignId;

    /**
     * The type of consumer loan product associated with this offer.
     * Examples: "LOYALTY", "PREAPPROVED", "E_AGGREGATOR", "TOP_UP".
     * This helps categorize offers and apply product-specific logic, like top-up deduplication.
     */
    private String productType;

    /**
     * The date from which the offer is valid.
     * Represents the start of the offer's availability period.
     */
    private LocalDate validFrom;

    /**
     * The date until which the offer is valid.
     * Represents the end of the offer's availability period.
     */
    private LocalDate validTo;

    /**
     * The status indicating the outcome of the deduplication process for this specific offer.
     * This field is critical given the project's strong emphasis on deduplication logic.
     * Examples: "ELIGIBLE_FOR_DEDUP", "DEDUPED_REMOVED", "DEDUPED_KEPT", "NOT_APPLICABLE".
     * "DEDUPED_REMOVED" implies the offer was matched and excluded.
     * "DEDUPED_KEPT" implies the offer was selected as the final one after deduplication.
     */
    private String deduplicationStatus;

    /**
     * Timestamp indicating when this offer summary record was last updated in the system.
     * Useful for auditing, tracking changes, and understanding data freshness.
     */
    private LocalDateTime lastUpdatedDate;
}
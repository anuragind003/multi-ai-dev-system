package com.ltfs.cdp.bre.model;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.math.BigDecimal;
import java.time.LocalDateTime;

/**
 * AttributionFact is a data model representing a fact object used by the Business Rule Engine (BRE)
 * for evaluating attribution and deduplication rules within the LTFS Offer CDP system.
 * It encapsulates key information about a customer, an offer, and associated loan details
 * that are relevant for determining offer eligibility, finalization, and deduplication status.
 *
 * This object serves as the input 'fact' for Drools or other rule engine implementations,
 * allowing rules to be written against its properties to implement complex business logic
 * related to customer profiling, offer management, and deduplication across various
 * consumer loan products.
 */
@Data // Generates getters, setters, toString, equals, and hashCode methods
@NoArgsConstructor // Generates a no-argument constructor
@AllArgsConstructor // Generates a constructor with all fields
@Builder // Provides a builder pattern for object creation, enhancing readability and flexibility
public class AttributionFact {

    /**
     * Unique identifier for the customer.
     * This ID is central to the single customer profile view in the CDP system.
     */
    private String customerId;

    /**
     * Permanent Account Number (PAN) of the customer.
     * A critical identifier used for deduplication logic across various consumer loan products.
     */
    private String pan;

    /**
     * Mobile number of the customer.
     * Used as a key identifier for deduplication and customer profiling, especially for matching.
     */
    private String mobileNumber;

    /**
     * Email ID of the customer.
     * Another key identifier for deduplication and customer profiling.
     */
    private String emailId;

    /**
     * Unique identifier for the offer.
     * Represents a specific offer generated for a customer, which is subject to attribution rules.
     */
    private String offerId;

    /**
     * Identifier for the campaign under which the offer was generated.
     * Helps in grouping and tracking offers by campaign, potentially influencing attribution.
     */
    private String campaignId;

    /**
     * The type of product associated with the offer (e.g., "Loyalty", "Preapproved", "E-aggregator", "Top-up").
     * This field is crucial for applying product-specific deduplication rules,
     * particularly for "Top-up" loans which have unique deduplication requirements.
     */
    private String productType;

    /**
     * The current status of the offer (e.g., "GENERATED", "DEDUPED", "FINALIZED", "REJECTED").
     * Rules can be applied based on the offer's lifecycle status to determine subsequent actions.
     */
    private String offerStatus;

    /**
     * The monetary amount of the offer.
     * Can be used in rules for offer prioritization or eligibility based on value.
     */
    private BigDecimal offerAmount;

    /**
     * The loan account number if the offer is linked to an existing loan.
     * Relevant for top-up offers or offers related to existing loan customers,
     * providing context from the 'live book' (Customer 360).
     */
    private String loanAccountNumber;

    /**
     * The status of the linked loan account (e.g., "ACTIVE", "CLOSED", "OVERDUE").
     * Provides additional context for rules related to existing loan relationships and customer eligibility.
     */
    private String loanStatus;

    /**
     * Timestamp when the offer was initially generated.
     * Useful for time-based rules, offer expiry, or auditing purposes.
     */
    private LocalDateTime offerGenerationTimestamp;

    /**
     * Timestamp when the deduplication process was last performed for this offer.
     * Can be null if deduplication hasn't occurred or is not applicable yet.
     * Indicates when the offer's deduplication status was last assessed.
     */
    private LocalDateTime deduplicationTimestamp;

    /**
     * A boolean flag indicating whether this offer is specifically a "Top-up" loan offer.
     * This is critical for applying the specific deduplication rule:
     * "Top-up loan offers must be deduped only within other Top-up offers, and matches found should be removed."
     * This flag simplifies rule writing for this specific requirement.
     */
    private boolean isTopUpOffer;
}
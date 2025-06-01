package com.ltfs.cdp.common.dto;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.math.BigDecimal;
import java.time.LocalDate;

/**
 * DTO (Data Transfer Object) for encapsulating basic offer details.
 * This class serves as a common structure for transferring offer-related information
 * across different layers and microservices within the LTFS Offer CDP system.
 * It includes core attributes defining an offer, such as its identifier, name,
 * type, associated product, monetary value, and validity period.
 *
 * <p>Utilizes Lombok annotations for automatic generation of boilerplate code
 * like getters, setters, constructors, equals(), hashCode(), and toString() methods,
 * promoting cleaner and more concise code.</p>
 */
@Data // Generates getters, setters, toString, equals, and hashCode methods
@NoArgsConstructor // Generates a no-argument constructor
@AllArgsConstructor // Generates a constructor with all fields as arguments
@Builder // Provides a builder pattern for fluent object creation
public class OfferDetailsDTO {

    /**
     * Unique identifier for the offer.
     * This ID helps in tracking and referencing specific offers within the system.
     * Example: "OFFER12345"
     */
    private String offerId;

    /**
     * The name or title of the offer.
     * Provides a human-readable label for the offer.
     * Example: "Pre-approved Personal Loan Offer"
     */
    private String offerName;

    /**
     * A detailed description of the offer.
     * Provides more context and specifics about what the offer entails,
     * such as interest rates, tenure, or special conditions.
     */
    private String offerDescription;

    /**
     * The type of the offer, e.g., "Loyalty", "Preapproved", "E-aggregator", "Top-up".
     * Helps categorize offers based on their origination or purpose, crucial for
     * deduplication logic as per functional requirements (e.g., Top-up offers deduped only within Top-up offers).
     */
    private String offerType;

    /**
     * The product category to which this offer applies, e.g., "Consumer Loan".
     * Ensures offers are correctly associated with relevant financial products.
     */
    private String productType;

    /**
     * The monetary value or limit associated with the offer.
     * Uses {@link BigDecimal} for precise financial calculations to avoid floating-point inaccuracies.
     * Example: 100000.00
     */
    private BigDecimal offerAmount;

    /**
     * The start date from which the offer is valid.
     * Uses {@link LocalDate} to represent the date without time-of-day information,
     * suitable for validity periods where time is not a critical factor.
     * Example: 2024-01-01
     */
    private LocalDate validFrom;

    /**
     * The end date until which the offer is valid.
     * Uses {@link LocalDate} to represent the date without time-of-day information.
     * Example: 2024-12-31
     */
    private LocalDate validTo;

    /**
     * The current status of the offer, e.g., "Active", "Expired", "Pending", "Finalized".
     * Reflects the lifecycle stage of the offer within the CDP system.
     */
    private String offerStatus;

    /**
     * Identifier of the campaign to which this offer belongs.
     * Links the offer to a specific marketing or business campaign, enabling campaign-level
     * tracking and analysis.
     */
    private String campaignId;
}
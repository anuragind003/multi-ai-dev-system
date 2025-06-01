package com.ltfs.cdp.bre.model;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.math.BigDecimal;

/**
 * EligibilityFact is a Plain Old Java Object (POJO) that serves as a fact object
 * for the Business Rule Engine (BRE) within the LTFS Offer CDP system.
 * It encapsulates all relevant data points required by the eligibility rules
 * to determine whether a specific customer is eligible for a particular offer.
 *
 * This fact object is populated with customer, offer, and campaign-related data
 * from various sources, including the Customer 360 system and Offermart.
 *
 * The fields are designed to support rules related to:
 * - Customer demographics and financial standing.
 * - Existing relationships with LTFS (e.g., loyalty, existing loans).
 * - Offer-specific attributes (e.g., product type, amount).
 * - Deduplication status against the 'live book' (Customer 360) and other offers.
 */
@Data
@NoArgsConstructor
@AllArgsConstructor
public class EligibilityFact {

    /**
     * Unique identifier for the customer being evaluated.
     */
    private String customerId;

    /**
     * Unique identifier for the offer being evaluated for eligibility.
     */
    private String offerId;

    /**
     * Unique identifier for the campaign associated with the offer.
     */
    private String campaignId;

    /**
     * The type of product the offer pertains to (e.g., "LOYALTY", "PRE_APPROVED", "TOP_UP", "E_AGGREGATOR").
     * This is crucial for product-specific eligibility and deduplication logic.
     */
    private String productType;

    /**
     * The proposed amount of the offer. Used in rules that depend on offer value.
     */
    private BigDecimal offerAmount;

    /**
     * The proposed tenure of the offer in months. Used in rules that depend on offer duration.
     */
    private Integer offerTenureMonths;

    /**
     * The proposed interest rate for the offer.
     */
    private BigDecimal offerInterestRate;

    /**
     * The customer's age in years.
     */
    private Integer customerAge;

    /**
     * The customer's annual income.
     */
    private BigDecimal customerIncome;

    /**
     * The customer's CIBIL (credit) score. A higher score generally indicates better creditworthiness.
     */
    private Integer cibilScore;

    /**
     * The number of active loans the customer currently has with LTFS.
     */
    private Integer existingLoanCount;

    /**
     * Indicates whether a profile for this customer exists in the Customer 360 'live book'.
     * Essential for deduplication logic against the master customer data.
     */
    private Boolean isCustomer360ProfileExists;

    /**
     * Indicates if the customer is identified as a pre-approved customer.
     */
    private Boolean isPreApprovedCustomer;

    /**
     * Indicates if the customer is identified as a loyalty customer.
     */
    private Boolean isLoyaltyCustomer;

    /**
     * Indicates if the offer being evaluated is a Top-up loan offer.
     * This flag is particularly important for specific deduplication rules
     * where top-up offers are deduped only within other top-up offers.
     */
    private Boolean isTopUpOffer;

    /**
     * Indicates whether the current offer has been identified as a duplicate
     * based on the deduplication logic.
     */
    private Boolean isOfferDeduplicated;

    /**
     * Provides the reason for deduplication if {@code isOfferDeduplicated} is true.
     * Examples: "Duplicate Customer ID", "Existing Top-up Offer Found", "Customer in Live Book".
     */
    private String deduplicationReason;

    /**
     * The customer's residence type (e.g., "OWNED", "RENTED", "PARENTAL").
     */
    private String customerResidenceType;

    /**
     * The customer's employment type (e.g., "SALARIED", "SELF_EMPLOYED", "BUSINESS_OWNER").
     */
    private String customerEmploymentType;
}
package com.ltfs.cdp.bre.model;

import java.math.BigDecimal;
import java.util.ArrayList;
import java.util.List;
import java.util.Objects;

/**
 * Represents a 'Fact' or data input asserted into the Drools rule engine
 * for processing within the LTFS Offer CDP system.
 * This class encapsulates an incoming offer record, including customer details,
 * offer specifics, and fields to track validation and deduplication outcomes
 * as rules are applied.
 *
 * Facts are the primary data elements that Drools rules operate on.
 * Rules can read fact attributes, modify them, or insert new facts into the working memory.
 */
public class Fact {

    /**
     * A unique identifier for this specific fact instance within the rule engine session.
     * This ID helps in tracking the lifecycle of a fact through the rule execution.
     */
    private String factId;

    /**
     * The system from which this offer record originated (e.g., "Offermart").
     * Used for source-specific validation or deduplication rules.
     */
    private String sourceSystem;

    /**
     * The original record ID from the source system. This is the unique identifier
     * of the record as it was received from the external system.
     */
    private String incomingRecordId;

    /**
     * The customer ID associated with the incoming record, if available from the source.
     */
    private String customerId;

    /**
     * Customer's Permanent Account Number (PAN) for identification and deduplication.
     * Crucial for cross-product deduplication and matching against Customer 360.
     */
    private String panNumber;

    /**
     * Customer's mobile number for identification and deduplication.
     */
    private String mobileNumber;

    /**
     * Customer's email ID for identification and deduplication.
     */
    private String emailId;

    /**
     * The type of loan product (e.g., "Loyalty", "Preapproved", "E-aggregator", "Top-up").
     * Used for product-specific rules, especially for deduplication logic.
     */
    private String productType;

    /**
     * The unique identifier for the offer itself.
     */
    private String offerId;

    /**
     * The proposed loan amount for the offer. Used in offer eligibility rules.
     */
    private BigDecimal loanAmount;

    /**
     * The proposed loan tenure in months. Used in offer eligibility rules.
     */
    private Integer tenureMonths;

    /**
     * The unique identifier for the campaign associated with this offer.
     * Can be used for campaign-specific rules or reporting.
     */
    private String campaignId;

    /**
     * Flag indicating if the initial column-level data validation has passed.
     * True if all required fields are present and in correct format, false otherwise.
     * This flag is typically set by early-stage validation rules.
     */
    private boolean isValidated;

    /**
     * A list of error messages if data validation fails.
     * Rules can add specific error messages to this list, providing detailed feedback.
     */
    private List<String> validationErrors;

    /**
     * The current deduplication status of the fact.
     * Possible values could be "PENDING", "NEW" (no match found), "MATCHED" (match found),
     * "REMOVED" (e.g., top-up offer removed due to a match).
     * Rules will update this status based on deduplication logic.
     */
    private String deduplicationStatus;

    /**
     * The ID of the matched entity (e.g., Customer 360 ID or another offer ID)
     * if a deduplication match is found. This helps link the incoming fact to an existing record.
     */
    private String dedupeMatchId;

    /**
     * A reason or explanation for the deduplication outcome (e.g., "Matched with Customer 360 by PAN",
     * "Top-up offer removed due to existing Top-up offer").
     */
    private String dedupeReason;

    /**
     * Final flag indicating if the offer is eligible for finalization after all rules
     * (validation, deduplication, and other business rules) have been applied.
     * This is the ultimate outcome of the rule engine processing for this fact.
     */
    private boolean isEligibleForFinalization;

    /**
     * Default constructor. Initializes mutable collections and default states.
     */
    public Fact() {
        this.validationErrors = new ArrayList<>();
        this.isValidated = false; // Default state: not yet validated
        this.isEligibleForFinalization = false; // Default state: not yet eligible
        this.deduplicationStatus = "PENDING"; // Default state: deduplication pending
    }

    /**
     * All-args constructor for convenient fact creation with initial data.
     *
     * @param factId A unique identifier for this fact instance.
     * @param sourceSystem The system from which this offer record originated.
     * @param incomingRecordId The original record ID from the source system.
     * @param customerId The customer ID associated with the incoming record.
     * @param panNumber Customer's PAN.
     * @param mobileNumber Customer's mobile number.
     * @param emailId Customer's email ID.
     * @param productType The type of loan product.
     * @param offerId The unique identifier for the offer.
     * @param loanAmount The proposed loan amount.
     * @param tenureMonths The proposed loan tenure in months.
     * @param campaignId The unique identifier for the campaign.
     */
    public Fact(String factId, String sourceSystem, String incomingRecordId, String customerId,
                String panNumber, String mobileNumber, String emailId, String productType,
                String offerId, BigDecimal loanAmount, Integer tenureMonths, String campaignId) {
        this(); // Call default constructor to initialize validationErrors and default flags
        this.factId = factId;
        this.sourceSystem = sourceSystem;
        this.incomingRecordId = incomingRecordId;
        this.customerId = customerId;
        this.panNumber = panNumber;
        this.mobileNumber = mobileNumber;
        this.emailId = emailId;
        this.productType = productType;
        this.offerId = offerId;
        this.loanAmount = loanAmount;
        this.tenureMonths = tenureMonths;
        this.campaignId = campaignId;
    }

    // --- Getters and Setters ---

    public String getFactId() {
        return factId;
    }

    public void setFactId(String factId) {
        this.factId = factId;
    }

    public String getSourceSystem() {
        return sourceSystem;
    }

    public void setSourceSystem(String sourceSystem) {
        this.sourceSystem = sourceSystem;
    }

    public String getIncomingRecordId() {
        return incomingRecordId;
    }

    public void setIncomingRecordId(String incomingRecordId) {
        this.incomingRecordId = incomingRecordId;
    }

    public String getCustomerId() {
        return customerId;
    }

    public void setCustomerId(String customerId) {
        this.customerId = customerId;
    }

    public String getPanNumber() {
        return panNumber;
    }

    public void setPanNumber(String panNumber) {
        this.panNumber = panNumber;
    }

    public String getMobileNumber() {
        return mobileNumber;
    }

    public void setMobileNumber(String mobileNumber) {
        this.mobileNumber = mobileNumber;
    }

    public String getEmailId() {
        return emailId;
    }

    public void setEmailId(String emailId) {
        this.emailId = emailId;
    }

    public String getProductType() {
        return productType;
    }

    public void setProductType(String productType) {
        this.productType = productType;
    }

    public String getOfferId() {
        return offerId;
    }

    public void setOfferId(String offerId) {
        this.offerId = offerId;
    }

    public BigDecimal getLoanAmount() {
        return loanAmount;
    }

    public void setLoanAmount(BigDecimal loanAmount) {
        this.loanAmount = loanAmount;
    }

    public Integer getTenureMonths() {
        return tenureMonths;
    }

    public void setTenureMonths(Integer tenureMonths) {
        this.tenureMonths = tenureMonths;
    }

    public String getCampaignId() {
        return campaignId;
    }

    public void setCampaignId(String campaignId) {
        this.campaignId = campaignId;
    }

    public boolean isValidated() {
        return isValidated;
    }

    public void setValidated(boolean validated) {
        isValidated = validated;
    }

    public List<String> getValidationErrors() {
        return validationErrors;
    }

    public void setValidationErrors(List<String> validationErrors) {
        this.validationErrors = validationErrors;
    }

    /**
     * Adds a single validation error message to the list.
     * This method ensures the list is initialized before adding an error.
     * @param error The error message to add.
     */
    public void addValidationError(String error) {
        if (this.validationErrors == null) {
            this.validationErrors = new ArrayList<>();
        }
        this.validationErrors.add(error);
    }

    public String getDeduplicationStatus() {
        return deduplicationStatus;
    }

    public void setDeduplicationStatus(String deduplicationStatus) {
        this.deduplicationStatus = deduplicationStatus;
    }

    public String getDedupeMatchId() {
        return dedupeMatchId;
    }

    public void setDedupeMatchId(String dedupeMatchId) {
        this.dedupeMatchId = dedupeMatchId;
    }

    public String getDedupeReason() {
        return dedupeReason;
    }

    public void setDedupeReason(String dedupeReason) {
        this.dedupeReason = dedupeReason;
    }

    public boolean isEligibleForFinalization() {
        return isEligibleForFinalization;
    }

    public void setEligibleForFinalization(boolean eligibleForFinalization) {
        isEligibleForFinalization = eligibleForFinalization;
    }

    /**
     * Overrides the equals method to define equality based on the unique factId.
     * This is crucial for Drools working memory, where facts are identified by their equality.
     * If factId is guaranteed to be unique for each asserted Fact object, this provides
     * a stable identity within the rule engine.
     *
     * @param o The object to compare with.
     * @return True if the objects are equal, false otherwise.
     */
    @Override
    public boolean equals(Object o) {
        if (this == o) return true;
        if (o == null || getClass() != o.getClass()) return false;
        Fact fact = (Fact) o;
        // Equality is based on the unique factId.
        // If factId is null, then equality falls back to comparing incomingRecordId and sourceSystem
        // to identify the same logical business record.
        if (factId != null) {
            return Objects.equals(factId, fact.factId);
        } else {
            return Objects.equals(incomingRecordId, fact.incomingRecordId) &&
                   Objects.equals(sourceSystem, fact.sourceSystem);
        }
    }

    /**
     * Overrides the hashCode method, consistent with the equals method.
     * Generates a hash code based on factId, or a combination of incomingRecordId and sourceSystem
     * if factId is not set.
     *
     * @return The hash code for this Fact object.
     */
    @Override
    public int hashCode() {
        if (factId != null) {
            return Objects.hash(factId);
        } else {
            return Objects.hash(incomingRecordId, sourceSystem);
        }
    }

    /**
     * Provides a string representation of the Fact object, useful for logging and debugging.
     * Sensitive fields like PAN, mobile, and email are masked for security purposes.
     *
     * @return A string representation of the Fact.
     */
    @Override
    public String toString() {
        return "Fact{" +
               "factId='" + factId + '\'' +
               ", sourceSystem='" + sourceSystem + '\'' +
               ", incomingRecordId='" + incomingRecordId + '\'' +
               ", customerId='" + customerId + '\'' +
               ", panNumber='" + (panNumber != null ? panNumber.replaceAll("(?<=.{2}).(?=.{2})", "*") : null) + '\'' + // Mask PAN
               ", mobileNumber='" + (mobileNumber != null ? mobileNumber.replaceAll("(?<=.{3}).(?=.{3})", "*") : null) + '\'' + // Mask mobile
               ", emailId='" + (emailId != null ? emailId.replaceAll("(?<=.{2}).(?=.*@)", "*") : null) + '\'' + // Mask email
               ", productType='" + productType + '\'' +
               ", offerId='" + offerId + '\'' +
               ", loanAmount=" + loanAmount +
               ", tenureMonths=" + tenureMonths +
               ", campaignId='" + campaignId + '\'' +
               ", isValidated=" + isValidated +
               ", validationErrors=" + validationErrors +
               ", deduplicationStatus='" + deduplicationStatus + '\'' +
               ", dedupeMatchId='" + dedupeMatchId + '\'' +
               ", dedupeReason='" + dedupeReason + '\'' +
               ", isEligibleForFinalization=" + isEligibleForFinalization +
               '}';
    }
}
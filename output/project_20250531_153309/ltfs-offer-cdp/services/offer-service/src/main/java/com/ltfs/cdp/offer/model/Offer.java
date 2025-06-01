package com.ltfs.cdp.offer.model;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.PrePersist;
import jakarta.persistence.PreUpdate;
import jakarta.persistence.Table;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.math.BigDecimal;
import java.time.LocalDate;
import java.time.LocalDateTime;

/**
 * JPA entity class representing an offer in the LTFS Offer CDP system.
 * This entity stores details about various types of offers, including
 * consumer loan products, their status, and deduplication information.
 */
@Entity
@Table(name = "offers")
@Data
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class Offer {

    /**
     * Unique identifier for the offer.
     * Generated automatically by the database.
     */
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    /**
     * A unique code identifying the offer.
     * This might be an external code from Offermart or an internal system code.
     */
    @Column(name = "offer_code", nullable = false, unique = true, length = 50)
    private String offerCode;

    /**
     * The name of the offer.
     */
    @Column(name = "offer_name", nullable = false, length = 100)
    private String offerName;

    /**
     * A brief description of the offer.
     */
    @Column(name = "offer_description", length = 500)
    private String offerDescription;

    /**
     * The type of the offer (e.g., LOYALTY, PREAPPROVED, E_AGGREGATOR, TOP_UP).
     * This is crucial for applying specific deduplication logic.
     */
    @Column(name = "offer_type", nullable = false, length = 50)
    private String offerType;

    /**
     * The type of product associated with the offer (e.g., CONSUMER_LOAN).
     */
    @Column(name = "product_type", nullable = false, length = 50)
    private String productType;

    /**
     * The unique identifier of the customer to whom the offer is extended.
     * This links the offer to the customer profile in the CDP system.
     */
    @Column(name = "customer_id", nullable = false, length = 100)
    private String customerId;

    /**
     * The unique identifier of the campaign under which this offer was generated.
     */
    @Column(name = "campaign_id", nullable = false, length = 100)
    private String campaignId;

    /**
     * The proposed loan amount for the offer.
     */
    @Column(name = "loan_amount", precision = 19, scale = 2)
    private BigDecimal loanAmount;

    /**
     * The proposed interest rate for the offer.
     */
    @Column(name = "interest_rate", precision = 5, scale = 2)
    private BigDecimal interestRate;

    /**
     * The proposed loan tenure in months.
     */
    @Column(name = "tenure_months")
    private Integer tenureMonths;

    /**
     * The date from which the offer is valid.
     */
    @Column(name = "start_date")
    private LocalDate startDate;

    /**
     * The date until which the offer is valid.
     */
    @Column(name = "end_date")
    private LocalDate endDate;

    /**
     * The current status of the offer (e.g., PENDING, ACTIVE, FINALIZED, REJECTED, EXPIRED).
     */
    @Column(name = "offer_status", nullable = false, length = 50)
    private String offerStatus;

    /**
     * The deduplication status of the offer (e.g., PENDING_DEDUP, DEDUPED, REMOVED_BY_DEDUP, NOT_APPLICABLE).
     * This field tracks the outcome of the deduplication process.
     */
    @Column(name = "deduplication_status", nullable = false, length = 50)
    private String deduplicationStatus;

    /**
     * The reason for the deduplication status, especially if the offer was removed.
     * (e.g., "MATCHED_WITH_EXISTING_OFFER", "MATCHED_WITH_LIVE_BOOK_CUSTOMER").
     */
    @Column(name = "deduplication_reason", length = 255)
    private String deduplicationReason;

    /**
     * Timestamp when the offer record was created.
     * Automatically set on persistence.
     */
    @Column(name = "created_at", nullable = false, updatable = false)
    private LocalDateTime createdAt;

    /**
     * Timestamp when the offer record was last updated.
     * Automatically updated on each modification.
     */
    @Column(name = "updated_at", nullable = false)
    private LocalDateTime updatedAt;

    /**
     * Callback method executed before the entity is persisted (inserted) into the database.
     * Sets the `createdAt` and `updatedAt` timestamps.
     */
    @PrePersist
    protected void onCreate() {
        this.createdAt = LocalDateTime.now();
        this.updatedAt = LocalDateTime.now();
    }

    /**
     * Callback method executed before the entity is updated in the database.
     * Updates the `updatedAt` timestamp.
     */
    @PreUpdate
    protected void onUpdate() {
        this.updatedAt = LocalDateTime.now();
    }
}
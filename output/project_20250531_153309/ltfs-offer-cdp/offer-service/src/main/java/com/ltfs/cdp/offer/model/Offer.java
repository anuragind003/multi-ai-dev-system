package com.ltfs.cdp.offer.model;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.EntityListeners;
import jakarta.persistence.EnumType;
import jakarta.persistence.Enumerated;
import jakarta.persistence.Id;
import jakarta.persistence.PrePersist;
import jakarta.persistence.Table;
import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;
import org.springframework.data.annotation.CreatedDate;
import org.springframework.data.annotation.LastModifiedDate;
import org.springframework.data.jpa.domain.support.AuditingEntityListener;

import java.math.BigDecimal;
import java.time.Instant;
import java.time.LocalDate;
import java.util.UUID;

/**
 * Represents an Offer entity in the LTFS Offer CDP system.
 * This entity stores detailed information about a customer offer,
 * including its status, financial details, and deduplication status.
 * It is mapped to the 'offers' table in the database.
 */
@Entity
@Table(name = "offers")
@Data // Lombok annotation to generate getters, setters, toString, equals, and hashCode
@NoArgsConstructor // Lombok annotation to generate a no-argument constructor
@AllArgsConstructor // Lombok annotation to generate an all-argument constructor
@EntityListeners(AuditingEntityListener.class) // Enable JPA auditing for created/updated dates
public class Offer {

    /**
     * Unique identifier for the offer.
     * Generated as a UUID before persistence if not already set.
     */
    @Id
    @Column(name = "id", updatable = false, nullable = false)
    private UUID id;

    /**
     * A business-friendly reference number for the offer, often used for external communication.
     * Must be unique across all offers.
     */
    @Column(name = "offer_reference_number", unique = true, nullable = false)
    private String offerReferenceNumber;

    /**
     * Identifier of the customer to whom this offer is made.
     * This links to the Customer entity (assuming Customer ID is also a UUID).
     */
    @Column(name = "customer_id", nullable = false)
    private UUID customerId;

    /**
     * Identifier of the campaign under which this offer was generated.
     * This links to the Campaign entity (assuming Campaign ID is also a UUID).
     */
    @Column(name = "campaign_id", nullable = false)
    private UUID campaignId;

    /**
     * Type of product offered (e.g., "Consumer Loan", "Top-up Loan", "Personal Loan").
     * This field is crucial for applying product-specific deduplication logic.
     */
    @Column(name = "product_type", nullable = false)
    private String productType;

    /**
     * The principal loan amount offered.
     * Stored with precision and scale suitable for currency.
     */
    @Column(name = "loan_amount", precision = 19, scale = 2, nullable = false)
    private BigDecimal loanAmount;

    /**
     * The interest rate applicable to the offer.
     * Stored with precision and scale for percentage values.
     */
    @Column(name = "interest_rate", precision = 5, scale = 2)
    private BigDecimal interestRate;

    /**
     * The tenure of the loan in months.
     */
    @Column(name = "tenure_months")
    private Integer tenureMonths;

    /**
     * Current status of the offer (e.g., PENDING, ACTIVE, EXPIRED, DEDUPED).
     * Stored as a String in the database for readability and flexibility.
     */
    @Enumerated(EnumType.STRING)
    @Column(name = "offer_status", nullable = false)
    private OfferStatus offerStatus;

    /**
     * The date from which the offer is valid.
     */
    @Column(name = "offer_start_date", nullable = false)
    private LocalDate offerStartDate;

    /**
     * The date until which the offer is valid.
     */
    @Column(name = "offer_end_date", nullable = false)
    private LocalDate offerEndDate;

    /**
     * The system from which the offer originated (e.g., "OFFERMART", "E-AGGREGATOR").
     * Useful for tracking data lineage.
     */
    @Column(name = "source_system", nullable = false)
    private String sourceSystem;

    /**
     * Status indicating if the offer has undergone deduplication and its outcome.
     * Stored as a String in the database.
     */
    @Enumerated(EnumType.STRING)
    @Column(name = "deduplication_status", nullable = false)
    private DeduplicationStatus deduplicationStatus;

    /**
     * Reason for deduplication, if applicable (e.g., "MATCHED_WITH_LIVE_BOOK", "MATCHED_WITH_TOPUP_OFFER").
     * This field provides context when an offer is marked as DEDUPED_SECONDARY.
     * Null if not deduped or if it's the primary offer after deduplication.
     */
    @Column(name = "deduplication_reason")
    private String deduplicationReason;

    /**
     * If this offer was deduped and marked as DEDUPED_SECONDARY, this field stores the ID of the primary offer
     * it was deduped against. Null if this is the primary offer or not deduped.
     */
    @Column(name = "original_offer_id")
    private UUID originalOfferId;

    /**
     * Timestamp when the offer record was created.
     * Automatically managed by JPA auditing (`@CreatedDate`).
     * Stored as an Instant to preserve full timestamp with timezone.
     */
    @CreatedDate
    @Column(name = "created_at", nullable = false, updatable = false)
    private Instant createdAt;

    /**
     * Timestamp when the offer record was last updated.
     * Automatically managed by JPA auditing (`@LastModifiedDate`).
     * Stored as an Instant.
     */
    @LastModifiedDate
    @Column(name = "updated_at", nullable = false)
    private Instant updatedAt;

    /**
     * User or system that created the offer record.
     * This field can be populated manually or via Spring Data JPA's `@CreatedBy` (requires AuditorAware setup).
     */
    @Column(name = "created_by", updatable = false)
    private String createdBy;

    /**
     * User or system that last updated the offer record.
     * This field can be populated manually or via Spring Data JPA's `@LastModifiedBy` (requires AuditorAware setup).
     */
    @Column(name = "updated_by")
    private String updatedBy;

    /**
     * Enum representing the possible statuses of an offer throughout its lifecycle.
     */
    public enum OfferStatus {
        PENDING,    // Offer is created but not yet fully processed or finalized
        ACTIVE,     // Offer is live and available to the customer for acceptance
        EXPIRED,    // Offer validity period has passed, and it's no longer active
        REJECTED,   // Offer was explicitly rejected by the customer or system
        DEDUPED,    // Offer was identified as a duplicate and marked as inactive/removed from consideration
        CANCELLED   // Offer was cancelled by the system or business logic before expiry/acceptance
    }

    /**
     * Enum representing the deduplication status of an offer.
     * This helps in managing and tracking duplicate offers within the system.
     */
    public enum DeduplicationStatus {
        NOT_DEDUPED,        // Offer has not undergone deduplication or is considered unique
        DEDUPED_PRIMARY,    // This offer is the primary one chosen after deduplication; other duplicates point to it
        DEDUPED_SECONDARY   // This offer was identified as a duplicate and is marked for removal or inactivation,
                            // pointing to the DEDUPED_PRIMARY offer
    }

    /**
     * Lifecycle callback method invoked before the entity is persisted (inserted) into the database.
     * This method ensures that the UUID `id` is generated if not already set,
     * and initializes default values for `deduplicationStatus` and `offerStatus`.
     */
    @PrePersist
    protected void onCreate() {
        if (this.id == null) {
            this.id = UUID.randomUUID(); // Generate a new UUID if ID is not set
        }
        if (this.deduplicationStatus == null) {
            this.deduplicationStatus = DeduplicationStatus.NOT_DEDUPED; // Default deduplication status
        }
        if (this.offerStatus == null) {
            this.offerStatus = OfferStatus.PENDING; // Default offer status
        }
    }
}
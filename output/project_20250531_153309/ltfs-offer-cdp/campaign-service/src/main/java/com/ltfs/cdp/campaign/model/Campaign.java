package com.ltfs.cdp.campaign.model;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.LocalDate;
import java.time.LocalDateTime;

/**
 * Entity representing a Campaign in the LTFS Offer CDP system.
 * This entity stores comprehensive details about various marketing campaigns,
 * including their type, status, and duration. It serves as a core data model
 * for managing offers and applying specific deduplication logic based on campaign attributes.
 *
 * <p>Utilizes Lombok for boilerplate code (getters, setters, constructors, builder)
 * and JPA annotations for object-relational mapping to a PostgreSQL database.</p>
 */
@Entity
@Table(name = "campaigns") // Maps this entity to the 'campaigns' table in the database
@Data // Lombok annotation: Generates getters, setters, toString, equals, and hashCode methods
@NoArgsConstructor // Lombok annotation: Generates a no-argument constructor
@AllArgsConstructor // Lombok annotation: Generates a constructor with all fields as arguments
@Builder // Lombok annotation: Provides a builder pattern for object creation
public class Campaign {

    /**
     * Unique identifier for the campaign.
     * This serves as the primary key for the 'campaigns' table.
     * Generated automatically by the database using identity strategy (auto-increment).
     */
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY) // Specifies auto-increment for PostgreSQL
    @Column(name = "id")
    private Long id;

    /**
     * A unique business code for the campaign.
     * This field ensures that each campaign has a distinct identifier,
     * often used for external system integration or business logic.
     * It is mandatory and unique across all campaigns.
     */
    @Column(name = "campaign_code", unique = true, nullable = false, length = 50)
    private String campaignCode;

    /**
     * The human-readable name of the campaign.
     * This field is mandatory.
     */
    @Column(name = "campaign_name", nullable = false, length = 255)
    private String campaignName;

    /**
     * A detailed description of the campaign.
     * Stored as TEXT to accommodate potentially long descriptions.
     */
    @Column(name = "description", columnDefinition = "TEXT")
    private String description;

    /**
     * The start date of the campaign.
     * Represents the date from which the campaign becomes active.
     * This field is mandatory.
     */
    @Column(name = "start_date", nullable = false)
    private LocalDate startDate;

    /**
     * The end date of the campaign.
     * Represents the date until which the campaign remains active.
     * This field is mandatory.
     */
    @Column(name = "end_date", nullable = false)
    private LocalDate endDate;

    /**
     * The type of the campaign (e.g., "LOYALTY", "PREAPPROVED", "E_AGGREGATOR", "TOP_UP").
     * This field is crucial for applying specific deduplication rules as per functional requirements,
     * such as "Top-up loan offers must be deduped only within other Top-up offers".
     * This field is mandatory.
     */
    @Column(name = "campaign_type", nullable = false, length = 50)
    private String campaignType;

    /**
     * The current status of the campaign (e.g., "ACTIVE", "INACTIVE", "DRAFT", "COMPLETED").
     * This field helps manage the lifecycle of a campaign.
     * This field is mandatory.
     */
    @Column(name = "status", nullable = false, length = 20)
    private String status;

    /**
     * The identifier of the user or system that created this campaign record.
     * This field is mandatory for auditing purposes.
     */
    @Column(name = "created_by", nullable = false, length = 100)
    private String createdBy;

    /**
     * The timestamp when this campaign record was created.
     * This field is mandatory for auditing purposes.
     */
    @Column(name = "created_at", nullable = false)
    private LocalDateTime createdAt;

    /**
     * The identifier of the user or system that last modified this campaign record.
     * This field is optional, as a record might not have been modified after creation.
     */
    @Column(name = "last_modified_by", length = 100)
    private String lastModifiedBy;

    /**
     * The timestamp when this campaign record was last modified.
     * This field is optional, as a record might not have been modified after creation.
     */
    @Column(name = "last_modified_at")
    private LocalDateTime lastModifiedAt;

    // Note on Auditing:
    // For automatic population of 'createdBy', 'createdAt', 'lastModifiedBy', and 'lastModifiedAt',
    // Spring Data JPA provides annotations like @CreatedBy, @CreatedDate, @LastModifiedBy, @LastModifiedDate.
    // These typically require enabling JPA Auditing via @EnableJpaAuditing on a configuration class
    // and using @EntityListeners(AuditingEntityListener.class) on the entity or a base entity.
    // For this standalone entity file, these fields are defined as regular columns,
    // assuming their population is handled either manually or by a broader auditing setup
    // within the Spring Boot application.
}
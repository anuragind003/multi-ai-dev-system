package com.ltfs.cdp.campaign.model;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.LocalDate;
import java.time.LocalDateTime;

/**
 * JPA entity class representing a campaign.
 * This entity stores details about various marketing campaigns within the LTFS Offer CDP system.
 * It supports tracking campaign attributes such as name, description, type, duration, and status.
 * This class is mapped to the 'campaigns' table in the database.
 */
@Entity
@Table(name = "campaigns") // Specifies the table name in the database
@Data // Lombok annotation to generate getters, setters, toString, equals, and hashCode methods
@NoArgsConstructor // Lombok annotation to generate a no-argument constructor
@AllArgsConstructor // Lombok annotation to generate an all-argument constructor
public class Campaign {

    /**
     * Unique identifier for the campaign.
     * This is the primary key of the campaigns table and is auto-generated.
     */
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY) // Configures the primary key to be auto-incremented by the database
    @Column(name = "campaign_id") // Maps this field to the 'campaign_id' column
    private Long id;

    /**
     * The name of the campaign.
     * This field is mandatory, unique, and has a maximum length of 255 characters.
     */
    @Column(name = "campaign_name", nullable = false, unique = true, length = 255)
    private String campaignName;

    /**
     * A detailed description of the campaign.
     * This field is optional and has a maximum length of 1000 characters.
     */
    @Column(name = "campaign_description", length = 1000)
    private String campaignDescription;

    /**
     * The type of the campaign (e.g., LOYALTY, PREAPPROVED, E_AGGREGATOR, TOP_UP).
     * This field is crucial for applying specific deduplication logic as per functional requirements.
     * It is mandatory and has a maximum length of 50 characters.
     */
    @Column(name = "campaign_type", nullable = false, length = 50)
    private String campaignType;

    /**
     * The start date of the campaign.
     * This field is mandatory.
     */
    @Column(name = "start_date", nullable = false)
    private LocalDate startDate;

    /**
     * The end date of the campaign.
     * This field is mandatory.
     */
    @Column(name = "end_date", nullable = false)
    private LocalDate endDate;

    /**
     * The current status of the campaign (e.g., ACTIVE, INACTIVE, DRAFT, COMPLETED).
     * This field is mandatory and has a maximum length of 20 characters.
     */
    @Column(name = "status", nullable = false, length = 20)
    private String status;

    /**
     * The user who created this campaign record.
     * This field is typically populated automatically by an auditing mechanism (e.g., Spring Data JPA Auditing).
     */
    @Column(name = "created_by", length = 100)
    private String createdBy;

    /**
     * The timestamp when this campaign record was created.
     * This field is typically populated automatically by an auditing mechanism.
     */
    @Column(name = "created_date")
    private LocalDateTime createdDate;

    /**
     * The user who last updated this campaign record.
     * This field is typically populated automatically by an auditing mechanism.
     */
    @Column(name = "updated_by", length = 100)
    private String updatedBy;

    /**
     * The timestamp when this campaign record was last updated.
     * This field is typically populated automatically by an auditing mechanism.
     */
    @Column(name = "updated_date")
    private LocalDateTime updatedDate;

    // Note on Auditing:
    // For 'createdBy', 'createdDate', 'updatedBy', and 'updatedDate' fields to be automatically populated,
    // Spring Data JPA Auditing needs to be configured in the application.
    // This typically involves:
    // 1. Enabling JPA Auditing with @EnableJpaAuditing in a Spring Boot configuration class.
    // 2. Optionally, implementing AuditorAware<String> to provide the current user.
    // 3. Adding @EntityListeners(AuditingEntityListener.class) to the entity class,
    //    or using @CreatedBy, @CreatedDate, @LastModifiedBy, @LastModifiedDate annotations
    //    from org.springframework.data.annotation package on the respective fields.
    //    For this standalone entity file, we just define the fields, assuming the auditing setup
    //    is handled at the application level.
}
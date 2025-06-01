package com.ltfs.cdp.customer.model;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;
import org.hibernate.annotations.GenericGenerator;

import javax.persistence.*;
import java.time.Instant;
import java.util.UUID;

/**
 * Entity representing a specific attribute of a customer within the LTFS Offer CDP system.
 * This class maps to the 'customer_attributes' table in the PostgreSQL database.
 * It stores various customer-related data points such as PAN, Aadhaar, Email, Phone, etc.,
 * along with metadata like the source system and last update timestamp.
 * This entity is crucial for building a single, comprehensive customer profile and
 * facilitating deduplication efforts across different data sources, aligning with the
 * project's goal of providing a single profile view of the customer.
 */
@Entity
@Table(name = "customer_attributes")
@Data // Lombok: Generates getters, setters, toString, equals, and hashCode methods automatically.
@NoArgsConstructor // Lombok: Generates a no-argument constructor, required by JPA.
@AllArgsConstructor // Lombok: Generates a constructor with all fields, useful for testing and data initialization.
public class CustomerAttribute {

    /**
     * Unique identifier for the customer attribute entry.
     * This is the primary key of the 'customer_attributes' table.
     * Generated as a UUID (Universally Unique Identifier) to ensure global uniqueness,
     * which is beneficial in distributed microservices architectures and avoids
     * potential ID conflicts when merging data from different sources.
     */
    @Id
    @GeneratedValue(generator = "UUID")
    @GenericGenerator(name = "UUID", strategy = "org.hibernate.id.UUIDGenerator")
    @Column(name = "id", updatable = false, nullable = false)
    private UUID id;

    /**
     * The unique identifier of the customer to whom this attribute belongs.
     * This field establishes a logical link to the main Customer entity.
     * It is a non-nullable UUID, ensuring every attribute is associated with a customer.
     * This is critical for aggregating all attributes to form a single customer profile.
     */
    @Column(name = "customer_id", nullable = false)
    private UUID customerId;

    /**
     * The name or type of the customer attribute (e.g., "PAN", "AADHAAR", "EMAIL", "PHONE_NUMBER").
     * This field categorizes the data stored in the 'attributeValue' column and is essential
     * for identifying and processing specific customer data points during validation and deduplication.
     * Max length is 100 characters to accommodate descriptive attribute names.
     */
    @Column(name = "attribute_name", nullable = false, length = 100)
    private String attributeName;

    /**
     * The actual value of the customer attribute.
     * This could be a PAN number, Aadhaar number, email address, phone number, etc.
     * This is the core data point for deduplication logic.
     * Max length is 255 characters to accommodate various data types and lengths.
     */
    @Column(name = "attribute_value", nullable = false, length = 255)
    private String attributeValue;

    /**
     * The system from which this attribute data was originally sourced.
     * Examples include "Offermart", "Customer360", "E-aggregator".
     * This information is vital for data lineage, conflict resolution during deduplication
     * (e.g., prioritizing data from 'Customer360' as the 'live book'),
     * and understanding data quality. Max length is 50 characters.
     */
    @Column(name = "source_system", nullable = false, length = 50)
    private String sourceSystem;

    /**
     * Timestamp indicating when this attribute record was last updated or created.
     * This field is automatically managed by JPA lifecycle callbacks (`@PrePersist`, `@PreUpdate`)
     * to ensure it always reflects the last modification time.
     * It is crucial for tracking data freshness, auditing purposes, and potentially for
     * resolving conflicts during deduplication (e.g., using the most recent attribute).
     */
    @Column(name = "last_updated_date", nullable = false)
    private Instant lastUpdatedDate;

    /**
     * A boolean flag indicating whether this attribute is currently active or valid.
     * This allows for soft deletion or inactivation of outdated, incorrect, or superseded
     * attributes without physically removing them from the database, preserving historical data.
     * This is useful for maintaining data integrity while still allowing for data evolution.
     */
    @Column(name = "is_active", nullable = false)
    private Boolean isActive;

    /**
     * JPA lifecycle callback method executed before a new entity is persisted (inserted) into the database.
     * It sets the 'lastUpdatedDate' to the current UTC timestamp, ensuring creation time is recorded.
     */
    @PrePersist
    protected void onCreate() {
        this.lastUpdatedDate = Instant.now();
    }

    /**
     * JPA lifecycle callback method executed before an existing entity is updated in the database.
     * It updates the 'lastUpdatedDate' to the current UTC timestamp, ensuring modification time is recorded.
     */
    @PreUpdate
    protected void onUpdate() {
        this.lastUpdatedDate = Instant.now();
    }
}
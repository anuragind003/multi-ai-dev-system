package com.ltfs.cdp.customer.model;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.FetchType;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.JoinColumn;
import jakarta.persistence.ManyToOne;
import jakarta.persistence.Table;
import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.LocalDateTime;

/**
 * Entity for storing dynamic customer attributes.
 * This table holds various additional, flexible attributes associated with a customer,
 * allowing for extensibility without altering the main Customer entity schema.
 * It supports storing key-value pairs where the value can be of different data types,
 * managed by the 'dataType' field.
 */
@Entity
@Table(name = "customer_attribute")
@Data // Generates getters, setters, toString, equals, and hashCode methods
@NoArgsConstructor // Generates a no-argument constructor
@AllArgsConstructor // Generates a constructor with all fields as arguments
public class CustomerAttribute {

    /**
     * Unique identifier for the customer attribute.
     * This serves as the primary key for the customer_attribute table.
     */
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY) // Auto-increments ID for new entities
    private Long id;

    /**
     * The customer to whom this attribute belongs.
     * This establishes a Many-to-One relationship with the Customer entity.
     * FetchType.LAZY is used to prevent eager loading of the Customer object,
     * improving performance by loading it only when explicitly accessed.
     * The 'customer_id' column in the 'customer_attribute' table will serve as the foreign key.
     * Assumes a 'Customer' entity exists in the same package or a related model package.
     */
    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "customer_id", nullable = false) // Maps the foreign key column
    private Customer customer;

    /**
     * The name of the dynamic attribute (e.g., "Occupation", "IncomeRange", "PreferredContactMethod").
     * This column is indexed for efficient lookup and querying of specific attributes.
     * It is a mandatory field.
     */
    @Column(name = "attribute_name", nullable = false, length = 100)
    private String attributeName;

    /**
     * The value of the dynamic attribute, stored as a String.
     * This allows for flexibility in storing various data types (e.g., numbers, dates, booleans)
     * which can be converted by the application layer based on the 'dataType' field.
     * Using 'columnDefinition = "TEXT"' allows for potentially longer attribute values.
     */
    @Column(name = "attribute_value", columnDefinition = "TEXT")
    private String attributeValue;

    /**
     * The original data type of the attribute value (e.g., "STRING", "INTEGER", "BOOLEAN", "DATE", "DECIMAL").
     * This metadata is crucial for proper type conversion and validation when retrieving
     * and processing the 'attributeValue'. It is a mandatory field.
     */
    @Column(name = "data_type", nullable = false, length = 50)
    private String dataType;

    /**
     * Timestamp indicating when this attribute record was last updated or created.
     * This helps in tracking data freshness and for auditing purposes. It is a mandatory field.
     */
    @Column(name = "last_updated_date", nullable = false)
    private LocalDateTime lastUpdatedDate;

    /**
     * The source system from which this attribute data originated (e.g., "Offermart", "Customer360", "E-aggregator").
     * This is vital for data lineage, understanding data provenance, and for implementing
     * conflict resolution strategies during data deduplication processes. It is a mandatory field.
     */
    @Column(name = "source_system", nullable = false, length = 100)
    private String sourceSystem;
}
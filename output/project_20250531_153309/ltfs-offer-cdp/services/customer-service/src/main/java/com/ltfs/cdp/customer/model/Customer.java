package com.ltfs.cdp.customer.model;

import jakarta.persistence.*;
import jakarta.validation.constraints.*;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;
import org.hibernate.annotations.GenericGenerator;
import org.springframework.data.annotation.CreatedBy;
import org.springframework.data.annotation.CreatedDate;
import org.springframework.data.annotation.LastModifiedBy;
import org.springframework.data.annotation.LastModifiedDate;
import org.springframework.data.jpa.domain.support.AuditingEntityListener;

import java.io.Serializable;
import java.time.Instant;
import java.time.LocalDate;
import java.util.UUID;

/**
 * JPA entity class representing a Customer in the LTFS Offer CDP system.
 * This entity maps to the 'customer' table in the PostgreSQL database.
 * It holds core customer profile information, crucial for deduplication
 * and providing a single customer view across various loan products.
 *
 * <p>Utilizes Lombok for boilerplate code (getters, setters, constructors, builder)
 * and Spring Data JPA Auditing for automatic population of creation and modification timestamps/users.</p>
 */
@Entity
@Table(name = "customer", uniqueConstraints = {
        @UniqueConstraint(columnNames = {"pan"}),
        @UniqueConstraint(columnNames = {"aadhaar"}),
        @UniqueConstraint(columnNames = {"mobile_number"}),
        @UniqueConstraint(columnNames = {"email_id"}),
        @UniqueConstraint(columnNames = {"customer_identifier"}) // Business unique ID
})
@Data // Lombok: Generates getters, setters, toString, equals, and hashCode
@NoArgsConstructor // Lombok: Generates a no-argument constructor
@AllArgsConstructor // Lombok: Generates a constructor with all fields
@Builder // Lombok: Provides a builder pattern for object creation
@EntityListeners(AuditingEntityListener.class) // Enables JPA auditing for created/modified dates/users
public class Customer implements Serializable {

    private static final long serialVersionUID = 1L;

    /**
     * Unique identifier for the customer entity.
     * Generated as a UUID by the database using Hibernate's UUIDGenerator.
     */
    @Id
    @GeneratedValue(generator = "UUID")
    @GenericGenerator(
            name = "UUID",
            strategy = "org.hibernate.id.UUIDGenerator"
    )
    @Column(name = "id", updatable = false, nullable = false)
    private UUID id;

    /**
     * Business-specific customer identifier, often used in legacy systems or external integrations.
     * This field is mandatory and must be unique across all customer records.
     */
    @Column(name = "customer_identifier", nullable = false, length = 50)
    @NotBlank(message = "Customer identifier cannot be blank")
    @Size(max = 50, message = "Customer identifier cannot exceed 50 characters")
    private String customerIdentifier;

    /**
     * First name of the customer.
     */
    @Column(name = "first_name", length = 100)
    @Size(max = 100, message = "First name cannot exceed 100 characters")
    private String firstName;

    /**
     * Middle name of the customer.
     */
    @Column(name = "middle_name", length = 100)
    @Size(max = 100, message = "Middle name cannot exceed 100 characters")
    private String middleName;

    /**
     * Last name of the customer.
     */
    @Column(name = "last_name", length = 100)
    @Size(max = 100, message = "Last name cannot exceed 100 characters")
    private String lastName;

    /**
     * Date of birth of the customer.
     */
    @Column(name = "date_of_birth")
    private LocalDate dateOfBirth;

    /**
     * Gender of the customer (e.g., "MALE", "FEMALE", "OTHER").
     */
    @Column(name = "gender", length = 10)
    @Size(max = 10, message = "Gender cannot exceed 10 characters")
    private String gender;

    /**
     * Permanent Account Number (PAN) of the customer.
     * This field is unique and crucial for identification and deduplication.
     * Includes pattern validation for standard Indian PAN format (5 letters, 4 digits, 1 letter).
     */
    @Column(name = "pan", unique = true, length = 10)
    @Pattern(regexp = "[A-Z]{5}[0-9]{4}[A-Z]{1}", message = "Invalid PAN format")
    @Size(min = 10, max = 10, message = "PAN must be 10 characters long")
    private String pan;

    /**
     * Aadhaar number of the customer.
     * This field is unique and crucial for identification and deduplication.
     * Includes pattern validation for standard 12-digit Aadhaar format.
     */
    @Column(name = "aadhaar", unique = true, length = 12)
    @Pattern(regexp = "^[2-9]{1}[0-9]{11}$", message = "Invalid Aadhaar format")
    @Size(min = 12, max = 12, message = "Aadhaar must be 12 characters long")
    private String aadhaar;

    /**
     * Mobile number of the customer.
     * This field is unique and crucial for identification and deduplication.
     * Includes pattern validation for standard Indian mobile numbers (10 digits, starting with 6-9).
     */
    @Column(name = "mobile_number", unique = true, length = 15)
    @Pattern(regexp = "^[6-9]\\d{9}$", message = "Invalid Indian mobile number format")
    @Size(max = 15, message = "Mobile number cannot exceed 15 characters")
    private String mobileNumber;

    /**
     * Email ID of the customer.
     * This field is unique and crucial for identification and deduplication.
     * Includes basic email format validation.
     */
    @Column(name = "email_id", unique = true, length = 255)
    @Email(message = "Invalid email format")
    @Size(max = 255, message = "Email ID cannot exceed 255 characters")
    private String emailId;

    /**
     * First line of the customer's address.
     */
    @Column(name = "address_line1", length = 255)
    @Size(max = 255, message = "Address line 1 cannot exceed 255 characters")
    private String addressLine1;

    /**
     * Second line of the customer's address.
     */
    @Column(name = "address_line2", length = 255)
    @Size(max = 255, message = "Address line 2 cannot exceed 255 characters")
    private String addressLine2;

    /**
     * City of the customer's address.
     */
    @Column(name = "city", length = 100)
    @Size(max = 100, message = "City cannot exceed 100 characters")
    private String city;

    /**
     * State of the customer's address.
     */
    @Column(name = "state", length = 100)
    @Size(max = 100, message = "State cannot exceed 100 characters")
    private String state;

    /**
     * Pincode/Zip code of the customer's address.
     */
    @Column(name = "pincode", length = 10)
    @Size(max = 10, message = "Pincode cannot exceed 10 characters")
    private String pincode;

    /**
     * Type of customer, indicating the source or category of the loan product.
     * Examples: "LOYALTY", "PREAPPROVED", "E_AGGREGATOR".
     */
    @Column(name = "customer_type", length = 50)
    @Size(max = 50, message = "Customer type cannot exceed 50 characters")
    private String customerType;

    /**
     * Status of deduplication for this customer record.
     * Examples: "PENDING", "DEDUPED", "NOT_DEDUPED", "REMOVED".
     * 'REMOVED' indicates a record that was identified as a duplicate and suppressed.
     */
    @Column(name = "dedupe_status", length = 20)
    @Size(max = 20, message = "Dedupe status cannot exceed 20 characters")
    private String dedupeStatus;

    /**
     * If this record is a duplicate, this field stores the ID of the master customer record
     * it was deduped against. This field will be null if the record is not deduped or is the master record itself.
     */
    @Column(name = "dedupe_reference_id")
    private UUID dedupeReferenceId;

    /**
     * The system from which this customer data originated.
     * Examples: "OFFERMART", "CUSTOMER_360", "CRM". This helps in tracing data lineage.
     */
    @Column(name = "source_system", length = 50)
    @Size(max = 50, message = "Source system cannot exceed 50 characters")
    private String sourceSystem;

    /**
     * Indicates if the customer record is active. Used for soft deletion or status management.
     * Defaults to true (active).
     */
    @Column(name = "is_active", nullable = false)
    private Boolean isActive = true; // Default to active

    /**
     * Timestamp when the record was created. Automatically managed by JPA Auditing.
     * This field is immutable after creation.
     */
    @CreatedDate
    @Column(name = "created_at", nullable = false, updatable = false)
    private Instant createdAt;

    /**
     * Timestamp when the record was last updated. Automatically managed by JPA Auditing.
     */
    @LastModifiedDate
    @Column(name = "updated_at")
    private Instant updatedAt;

    /**
     * User or system that created the record. Automatically managed by JPA Auditing.
     * This field is immutable after creation.
     */
    @CreatedBy
    @Column(name = "created_by", length = 100, updatable = false)
    private String createdBy;

    /**
     * User or system that last updated the record. Automatically managed by JPA Auditing.
     */
    @LastModifiedBy
    @Column(name = "updated_by", length = 100)
    private String updatedBy;
}
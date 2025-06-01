package com.ltfs.cdp.common.dto;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.LocalDate;

/**
 * Data Transfer Object (DTO) representing a simplified customer profile view.
 * This DTO is used across the LTFS Offer CDP system to provide a consistent
 * and deduplicated view of customer information, primarily for consumer loan products.
 * It contains essential fields for customer identification and deduplication purposes,
 * aligning with the project's goal of a single customer profile view.
 */
@Data
@NoArgsConstructor
@AllArgsConstructor
public class CustomerProfileDTO {

    /**
     * Unique identifier for the customer within the CDP system.
     * This ID is typically generated or assigned by the CDP upon ingestion
     * or during the deduplication process.
     */
    private String customerId;

    /**
     * The canonical identifier for the customer from the Customer 360 system (live book).
     * This field is crucial for linking the CDP's customer profile to the enterprise-wide
     * customer master data after successful deduplication.
     */
    private String customer360Id;

    /**
     * The first name of the customer. Used for identification and matching.
     */
    private String firstName;

    /**
     * The last name of the customer. Used for identification and matching.
     */
    private String lastName;

    /**
     * The customer's mobile number. A primary contact point and a key field
     * for deduplication logic.
     */
    private String mobileNumber;

    /**
     * The customer's email ID. Another important contact point and a field
     * often used in deduplication algorithms.
     */
    private String emailId;

    /**
     * The customer's Permanent Account Number (PAN).
     * This is a unique identifier for financial transactions in India and is
     * a critical field for robust deduplication in the financial domain.
     */
    private String panNumber;

    /**
     * The customer's Aadhaar number (Unique Identification Authority of India).
     * A widely used unique identifier in India, highly relevant for
     * accurate customer deduplication.
     */
    private String aadhaarNumber;

    /**
     * The customer's date of birth. Used for identification, age verification,
     * and as a strong criterion in deduplication logic.
     */
    private LocalDate dateOfBirth;

    // Future enhancements might include additional fields like address, gender,
    // or other demographic data if they become relevant for the "simplified"
    // profile view or for more granular deduplication rules.
}
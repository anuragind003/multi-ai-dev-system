package com.ltfs.cdp.common.dto;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.LocalDate;

/**
 * Data Transfer Object (DTO) representing core customer profile information.
 * This DTO is used to exchange simplified customer data between services
 * without exposing the full complexity of the underlying entity.
 * It supports the "single profile view of the customer" requirement by
 * encapsulating key identifying attributes.
 */
@Data
@NoArgsConstructor
@AllArgsConstructor
public class CustomerProfileDTO {

    /**
     * Unique identifier for the customer within the CDP system.
     * This could be an internal system ID or a primary key from a source system.
     */
    private String customerId;

    /**
     * Customer Information File (CIF) number, a unique identifier often used in banking.
     */
    private String cifNumber;

    /**
     * The first name of the customer.
     */
    private String firstName;

    /**
     * The last name of the customer.
     */
    private String lastName;

    /**
     * The primary mobile number of the customer.
     */
    private String mobileNumber;

    /**
     * Permanent Account Number (PAN) of the customer, a unique identification number
     * issued by the Indian Income Tax Department.
     */
    private String panNumber;

    /**
     * Aadhaar number of the customer, a 12-digit unique identification number
     * issued by the Unique Identification Authority of India (UIDAI).
     */
    private String aadhaarNumber;

    /**
     * The date of birth of the customer.
     */
    private LocalDate dateOfBirth;

    /**
     * The primary email address of the customer.
     */
    private String emailId;

    // Lombok annotations (@Data, @NoArgsConstructor, @AllArgsConstructor) automatically
    // generate getters, setters, equals(), hashCode(), and toString() methods,
    // and a no-argument and all-argument constructor, respectively.
    // This reduces boilerplate code and keeps the DTO concise.
}
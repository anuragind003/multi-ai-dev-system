package com.ltfs.cdp.customer.dto;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

import javax.validation.constraints.Email;
import javax.validation.constraints.NotBlank;
import javax.validation.constraints.NotNull;
import javax.validation.constraints.PastOrPresent;
import javax.validation.constraints.Pattern;
import javax.validation.constraints.Size;
import java.time.LocalDate;

/**
 * Data Transfer Object (DTO) for Customer Profile.
 * This DTO is used to transfer consolidated customer profile data
 * between different layers of the application and over the API.
 * It represents a single, deduplicated view of a customer for Consumer Loan Products
 * within the LTFS Offer CDP system.
 */
@Data
@NoArgsConstructor
@AllArgsConstructor
public class CustomerProfileDTO {

    /**
     * Unique identifier for the customer profile in the CDP system.
     * This ID is typically generated after successful deduplication and consolidation
     * of customer data from various sources (e.g., Offermart).
     */
    private String customerId;

    /**
     * The customer's first name.
     * Mandatory field with a maximum length of 100 characters.
     */
    @NotBlank(message = "First name cannot be blank")
    @Size(max = 100, message = "First name cannot exceed 100 characters")
    private String firstName;

    /**
     * The customer's middle name.
     * Optional field with a maximum length of 100 characters.
     */
    @Size(max = 100, message = "Middle name cannot exceed 100 characters")
    private String middleName;

    /**
     * The customer's last name.
     * Mandatory field with a maximum length of 100 characters.
     */
    @NotBlank(message = "Last name cannot be blank")
    @Size(max = 100, message = "Last name cannot exceed 100 characters")
    private String lastName;

    /**
     * The customer's date of birth.
     * Mandatory field, must be a date in the past or present.
     */
    @NotNull(message = "Date of birth cannot be null")
    @PastOrPresent(message = "Date of birth cannot be in the future")
    private LocalDate dateOfBirth;

    /**
     * Permanent Account Number (PAN) of the customer.
     * Mandatory field, validated against a standard Indian PAN format (5 letters, 4 digits, 1 letter).
     */
    @NotBlank(message = "PAN cannot be blank")
    @Pattern(regexp = "[A-Z]{5}[0-9]{4}[A-Z]{1}", message = "Invalid PAN format. Expected: ABCDE1234F")
    private String pan;

    /**
     * Aadhar Number of the customer.
     * Mandatory field, validated against a standard 12-digit Aadhar format (starts with 2-9).
     */
    @NotBlank(message = "Aadhar number cannot be blank")
    @Pattern(regexp = "^[2-9]{1}[0-9]{11}$", message = "Invalid Aadhar number format. Expected: 12 digits starting with 2-9")
    private String aadharNumber;

    /**
     * Primary mobile number of the customer.
     * Mandatory field, validated against a standard 10-digit Indian mobile number format (starts with 6-9).
     */
    @NotBlank(message = "Mobile number cannot be blank")
    @Pattern(regexp = "^[6-9]\\d{9}$", message = "Invalid mobile number format. Expected: 10 digits starting with 6-9")
    private String mobileNumber;

    /**
     * Primary email ID of the customer.
     * Optional field, validated against a standard email format with a maximum length of 255 characters.
     */
    @Email(message = "Invalid email format")
    @Size(max = 255, message = "Email ID cannot exceed 255 characters")
    private String emailId;

    /**
     * Address Line 1 of the customer's residential address.
     * Mandatory field with a maximum length of 255 characters.
     */
    @NotBlank(message = "Address Line 1 cannot be blank")
    @Size(max = 255, message = "Address Line 1 cannot exceed 255 characters")
    private String addressLine1;

    /**
     * Address Line 2 of the customer's residential address.
     * Optional field with a maximum length of 255 characters.
     */
    @Size(max = 255, message = "Address Line 2 cannot exceed 255 characters")
    private String addressLine2;

    /**
     * City of the customer's residential address.
     * Mandatory field with a maximum length of 100 characters.
     */
    @NotBlank(message = "City cannot be blank")
    @Size(max = 100, message = "City cannot exceed 100 characters")
    private String city;

    /**
     * State of the customer's residential address.
     * Mandatory field with a maximum length of 100 characters.
     */
    @NotBlank(message = "State cannot be blank")
    @Size(max = 100, message = "State cannot exceed 100 characters")
    private String state;

    /**
     * Pincode of the customer's residential address.
     * Mandatory field, validated against a standard 6-digit Indian pincode format (starts with 1-9).
     */
    @NotBlank(message = "Pincode cannot be blank")
    @Pattern(regexp = "^[1-9]{1}[0-9]{5}$", message = "Invalid pincode format. Expected: 6 digits starting with 1-9")
    private String pincode;

    /**
     * Identifier from the 'Customer 360' live book system.
     * This field is populated if the customer profile has been successfully deduped
     * and matched against an existing customer in the Customer 360 system.
     */
    private String customer360Id;

    /**
     * A boolean flag indicating whether this customer profile is considered part of the 'live book'.
     * True if a match was found and consolidated with a Customer 360 entry.
     */
    private Boolean isLiveBookCustomer;

    /**
     * The current deduplication status of the customer profile.
     * This can indicate the outcome of the deduplication process, e.g.,
     * "DEDUPED": Successfully deduplicated and consolidated.
     * "PENDING_DEDUP": Awaiting deduplication process.
     * "NOT_DEDUPED": No match found or deduplication not yet performed.
     * "DUPLICATE_REMOVED": Identified as a duplicate and removed/merged.
     */
    private String deduplicationStatus;
}
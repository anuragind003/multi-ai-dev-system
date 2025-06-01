package com.ltfs.cdp.customer.dto;

import jakarta.validation.constraints.Email;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Past;
import jakarta.validation.constraints.Pattern;
import jakarta.validation.constraints.Size;
import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.LocalDate;

/**
 * Data Transfer Object (DTO) for incoming customer data requests.
 * This class encapsulates the necessary fields for creating or updating a customer profile
 * within the LTFS Offer CDP system. It includes basic column-level validation
 * to ensure data integrity at the point of entry.
 *
 * <p>Utilizes Lombok annotations for boilerplate code reduction (getters, setters,
 * constructors, toString, equals, hashCode).</p>
 *
 * <p>Validation constraints are applied using Jakarta Bean Validation (JSR 380) annotations
 * to enforce data quality rules.</p>
 */
@Data
@NoArgsConstructor
@AllArgsConstructor
public class CustomerRequest {

    /**
     * The identifier of the source system from which this customer data originated.
     * This is crucial for tracking data lineage and for specific deduplication rules.
     * Example: "Offermart", "CRM", "LegacySystem".
     */
    @NotBlank(message = "Source system cannot be blank")
    @Size(max = 50, message = "Source system must not exceed 50 characters")
    private String sourceSystem;

    /**
     * The unique identifier of the customer within the originating source system.
     * This helps in mapping and reconciling customer records across different platforms.
     */
    @NotBlank(message = "Source customer ID cannot be blank")
    @Size(max = 100, message = "Source customer ID must not exceed 100 characters")
    private String sourceCustomerId;

    /**
     * The first name of the customer.
     */
    @NotBlank(message = "First name cannot be blank")
    @Size(max = 100, message = "First name must not exceed 100 characters")
    private String firstName;

    /**
     * The middle name of the customer. This field is optional.
     */
    @Size(max = 100, message = "Middle name must not exceed 100 characters")
    private String middleName;

    /**
     * The last name of the customer.
     */
    @NotBlank(message = "Last name cannot be blank")
    @Size(max = 100, message = "Last name must not exceed 100 characters")
    private String lastName;

    /**
     * The date of birth of the customer.
     * Must be a valid date and in the past, as per typical customer data requirements.
     */
    @NotNull(message = "Date of birth cannot be null")
    @Past(message = "Date of birth must be in the past")
    private LocalDate dateOfBirth;

    /**
     * The gender of the customer. Expected values are typically 'M' for Male, 'F' for Female,
     * or 'O' for Other.
     */
    @NotBlank(message = "Gender cannot be blank")
    @Pattern(regexp = "^[MFO]$", message = "Gender must be 'M', 'F', or 'O'")
    private String gender;

    /**
     * The primary mobile number of the customer.
     * Validated to be a 10-digit numeric string, common for Indian mobile numbers.
     */
    @NotBlank(message = "Mobile number cannot be blank")
    @Pattern(regexp = "^[0-9]{10}$", message = "Mobile number must be a 10-digit number")
    private String mobileNumber;

    /**
     * The email ID of the customer. This field is optional.
     * If provided, it must conform to a standard email format.
     */
    @Email(message = "Email ID must be a valid email format")
    @Size(max = 255, message = "Email ID must not exceed 255 characters")
    private String emailId;

    /**
     * The Permanent Account Number (PAN) of the customer. This field is optional.
     * If provided, it must adhere to the standard Indian PAN format (5 letters, 4 digits, 1 letter).
     */
    @Pattern(regexp = "^[A-Z]{5}[0-9]{4}[A-Z]{1}$", message = "PAN number must be in a valid format (e.g., ABCDE1234F)")
    private String panNumber;

    /**
     * The Aadhaar number of the customer. This field is optional.
     * If provided, it must be a 12-digit numeric string.
     */
    @Pattern(regexp = "^[0-9]{12}$", message = "Aadhaar number must be a 12-digit number")
    private String aadhaarNumber;

    /**
     * The first line of the customer's residential or correspondence address.
     */
    @NotBlank(message = "Address Line 1 cannot be blank")
    @Size(max = 255, message = "Address Line 1 must not exceed 255 characters")
    private String addressLine1;

    /**
     * The second line of the customer's address. This field is optional.
     */
    @Size(max = 255, message = "Address Line 2 must not exceed 255 characters")
    private String addressLine2;

    /**
     * The city component of the customer's address.
     */
    @NotBlank(message = "City cannot be blank")
    @Size(max = 100, message = "City must not exceed 100 characters")
    private String city;

    /**
     * The state component of the customer's address.
     */
    @NotBlank(message = "State cannot be blank")
    @Size(max = 100, message = "State must not exceed 100 characters")
    private String state;

    /**
     * The pincode (postal code) of the customer's address.
     * Validated to be a 6-digit numeric string, common for Indian pincodes.
     */
    @NotBlank(message = "Pincode cannot be blank")
    @Pattern(regexp = "^[0-9]{6}$", message = "Pincode must be a 6-digit number")
    private String pincode;

    /**
     * The type of consumer loan product associated with this customer request.
     * This field is critical for applying specific deduplication logic and offer finalization rules.
     * Examples: "Loyalty", "Preapproved", "E-aggregator", "Top-up".
     */
    @NotBlank(message = "Loan product type cannot be blank")
    @Size(max = 50, message = "Loan product type must not exceed 50 characters")
    private String loanProductType;
}
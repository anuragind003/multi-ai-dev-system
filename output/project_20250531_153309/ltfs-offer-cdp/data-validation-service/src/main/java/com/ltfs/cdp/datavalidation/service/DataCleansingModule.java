package com.ltfs.cdp.datavalidation.service;

import org.springframework.stereotype.Service;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.regex.Pattern;

/**
 * Service module responsible for performing basic data cleansing operations on validated customer data.
 * This includes trimming whitespace, standardizing case, and formatting specific data types
 * like phone numbers, email addresses, PAN, and Aadhaar numbers.
 * <p>
 * It operates on a {@link CustomerDataDTO} object, ensuring type safety and a clear data structure.
 * It is assumed that {@code CustomerDataDTO} is defined in the same package or an accessible package
 * and contains fields relevant to customer information (e.g., firstName, mobileNumber, panCard).
 * </p>
 */
@Service
public class DataCleansingModule {

    private static final Logger log = LoggerFactory.getLogger(DataCleansingModule.class);

    // Regex for common non-digit characters (used for phone numbers, Aadhaar)
    private static final Pattern NON_DIGIT_PATTERN = Pattern.compile("[^\\d]");
    // Basic regex for PAN card format (5 letters, 4 digits, 1 letter)
    private static final Pattern PAN_CARD_PATTERN = Pattern.compile("^[A-Z]{5}[0-9]{4}[A-Z]{1}$");
    // Basic regex for Aadhaar number format (12 digits)
    private static final Pattern AADHAAR_NUMBER_PATTERN = Pattern.compile("^\\d{12}$");

    /**
     * Cleanses a given {@link CustomerDataDTO} object by applying various cleansing rules.
     * The cleansing process includes:
     * <ul>
     *     <li>Trimming leading/trailing whitespace from all string fields.</li>
     *     <li>Converting empty strings (after trimming) to {@code null}.</li>
     *     <li>Standardizing names (first, last, middle) and city/state to Title Case.</li>
     *     <li>Standardizing email addresses to lowercase.</li>
     *     <li>Formatting mobile numbers to contain only digits.</li>
     *     <li>Formatting PAN card numbers (uppercase, no spaces, basic validation).</li>
     *     <li>Formatting Aadhaar numbers (digits only, basic validation).</li>
     *     <li>Standardizing gender values to common representations (M, F, O).</li>
     * </ul>
     *
     * @param rawCustomerData The {@link CustomerDataDTO} containing raw customer data that has
     *                        already passed initial validation.
     * @return A new {@link CustomerDataDTO} object containing the cleansed data.
     *         Returns a new, empty {@link CustomerDataDTO} if the input {@code rawCustomerData} is {@code null}.
     */
    public CustomerDataDTO cleanseCustomerData(CustomerDataDTO rawCustomerData) {
        if (rawCustomerData == null) {
            log.warn("Received null CustomerDataDTO for cleansing. Returning a new, empty DTO.");
            return new CustomerDataDTO(); // Return an empty DTO to avoid NullPointerException downstream
        }

        CustomerDataDTO cleansedData = new CustomerDataDTO();

        // Customer ID - typically just trim and ensure not empty
        cleansedData.setCustomerId(emptyToNull(rawCustomerData.getCustomerId()));

        // Names - trim, empty to null, and convert to Title Case
        cleansedData.setFirstName(toTitleCase(rawCustomerData.getFirstName()));
        cleansedData.setLastName(toTitleCase(rawCustomerData.getLastName()));
        cleansedData.setMiddleName(toTitleCase(rawCustomerData.getMiddleName()));

        // Mobile Number - trim, empty to null, and format to digits only
        cleansedData.setMobileNumber(formatMobileNumber(rawCustomerData.getMobileNumber()));

        // Email - trim, empty to null, and convert to lowercase
        cleansedData.setEmail(toLowerCase(rawCustomerData.getEmail()));

        // PAN Card - trim, empty to null, uppercase, remove spaces, and validate
        cleansedData.setPanCard(formatPanCard(rawCustomerData.getPanCard()));

        // Aadhaar Number - trim, empty to null, digits only, and validate
        cleansedData.setAadhaarNumber(formatAadhaarNumber(rawCustomerData.getAadhaarNumber()));

        // Address fields - trim and empty to null, city/state to Title Case
        cleansedData.setAddressLine1(emptyToNull(rawCustomerData.getAddressLine1()));
        cleansedData.setAddressLine2(emptyToNull(rawCustomerData.getAddressLine2()));
        cleansedData.setCity(toTitleCase(rawCustomerData.getCity()));
        cleansedData.setState(toTitleCase(rawCustomerData.getState()));
        cleansedData.setPincode(emptyToNull(rawCustomerData.getPincode())); // Pincode typically just digits, but can be string

        // Date of Birth - just trim and empty to null for now. Actual date parsing/formatting
        // might be handled in a dedicated date utility or mapping layer.
        cleansedData.setDateOfBirth(emptyToNull(rawCustomerData.getDateOfBirth()));

        // Gender - trim, empty to null, and standardize to common representations
        cleansedData.setGender(standardizeGender(rawCustomerData.getGender()));

        log.debug("Customer data cleansing completed for customer ID: {}", cleansedData.getCustomerId());
        return cleansedData;
    }

    /**
     * Cleanses a generic string by trimming leading/trailing whitespace.
     * If the string becomes empty after trimming, it is converted to {@code null}.
     *
     * @param input The string to cleanse.
     * @return The trimmed string, or {@code null} if the input is {@code null} or becomes empty after trimming.
     */
    private String emptyToNull(String input) {
        if (input == null) {
            return null;
        }
        String trimmed = input.trim();
        return trimmed.isEmpty() ? null : trimmed;
    }

    /**
     * Converts a string to Title Case (first letter of each word capitalized, rest lowercase).
     * Handles multiple words separated by spaces and trims the final result.
     *
     * @param input The string to convert.
     * @return The string in Title Case, or {@code null} if input is {@code null} or empty after trimming.
     */
    private String toTitleCase(String input) {
        String cleanedInput = emptyToNull(input);
        if (cleanedInput == null) {
            return null;
        }

        StringBuilder titleCase = new StringBuilder();
        boolean capitalizeNext = true; // Flag to indicate if the next character should be capitalized

        for (char c : cleanedInput.toCharArray()) {
            if (Character.isWhitespace(c)) {
                titleCase.append(c);
                capitalizeNext = true; // Next non-whitespace character should be capitalized
            } else if (capitalizeNext) {
                titleCase.append(Character.toUpperCase(c));
                capitalizeNext = false; // Reset flag until next whitespace
            } else {
                titleCase.append(Character.toLowerCase(c));
            }
        }
        return titleCase.toString().trim(); // Trim final result in case of leading/trailing spaces
    }

    /**
     * Converts a string to lowercase.
     *
     * @param input The string to convert.
     * @return The string in lowercase, or {@code null} if input is {@code null} or empty after trimming.
     */
    private String toLowerCase(String input) {
        String cleanedInput = emptyToNull(input);
        return cleanedInput != null ? cleanedInput.toLowerCase() : null;
    }

    /**
     * Formats a mobile number by removing all non-digit characters.
     *
     * @param mobileNumber The raw mobile number string.
     * @return The formatted mobile number containing only digits, or {@code null} if input is {@code null} or empty.
     */
    private String formatMobileNumber(String mobileNumber) {
        String cleanedInput = emptyToNull(mobileNumber);
        if (cleanedInput == null) {
            return null;
        }
        String digitsOnly = NON_DIGIT_PATTERN.matcher(cleanedInput).replaceAll("");
        return digitsOnly.isEmpty() ? null : digitsOnly;
    }

    /**
     * Formats a PAN card number by converting it to uppercase and removing spaces.
     * Performs a basic regex validation. If validation fails, logs a warning and returns {@code null}.
     *
     * @param panCard The raw PAN card number string.
     * @return The formatted PAN card number, or {@code null} if input is {@code null}, empty, or invalid.
     */
    private String formatPanCard(String panCard) {
        String cleanedInput = emptyToNull(panCard);
        if (cleanedInput == null) {
            return null;
        }
        String formattedPan = cleanedInput.toUpperCase().replaceAll("\\s", "");
        if (PAN_CARD_PATTERN.matcher(formattedPan).matches()) {
            return formattedPan;
        } else {
            log.warn("Invalid PAN card format detected during cleansing: '{}'. Expected format like ABCDE1234F. Returning null.", panCard);
            return null;
        }
    }

    /**
     * Formats an Aadhaar number by removing all non-digit characters.
     * Performs a basic length validation (12 digits). If validation fails, logs a warning and returns {@code null}.
     *
     * @param aadhaarNumber The raw Aadhaar number string.
     * @return The formatted Aadhaar number (12 digits), or {@code null} if input is {@code null}, empty, or invalid.
     */
    private String formatAadhaarNumber(String aadhaarNumber) {
        String cleanedInput = emptyToNull(aadhaarNumber);
        if (cleanedInput == null) {
            return null;
        }
        String formattedAadhaar = NON_DIGIT_PATTERN.matcher(cleanedInput).replaceAll(""); // Remove all non-digits
        if (AADHAAR_NUMBER_PATTERN.matcher(formattedAadhaar).matches()) {
            return formattedAadhaar;
        } else {
            log.warn("Invalid Aadhaar number format or length detected during cleansing: '{}'. Expected 12 digits. Returning null.", aadhaarNumber);
            return null;
        }
    }

    /**
     * Standardizes gender input to common representations (e.g., "M", "F", "O").
     * This method is case-insensitive for input.
     *
     * @param gender The raw gender string.
     * @return Standardized gender string ("M", "F", "O"), or {@code null} if input is {@code null} or cannot be standardized.
     */
    private String standardizeGender(String gender) {
        String cleanedInput = emptyToNull(gender);
        if (cleanedInput == null) {
            return null;
        }
        String upperCaseGender = cleanedInput.toUpperCase();
        switch (upperCaseGender) {
            case "M":
            case "MALE":
                return "M";
            case "F":
            case "FEMALE":
                return "F";
            case "O":
            case "OTHER":
            case "OTHERS": // Common variant
                return "O";
            default:
                log.warn("Unrecognized gender value for cleansing: '{}'. Returning null.", gender);
                return null;
        }
    }
}

// NOTE: The CustomerDataDTO class is assumed to be defined in the same package
// (com.ltfs.cdp.datavalidation.service) or an accessible package.
// For example:
/*
package com.ltfs.cdp.datavalidation.service;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class CustomerDataDTO {
    private String customerId;
    private String firstName;
    private String lastName;
    private String middleName;
    private String mobileNumber;
    private String email;
    private String panCard;
    private String aadhaarNumber;
    private String addressLine1;
    private String addressLine2;
    private String city;
    private String state;
    private String pincode;
    private String dateOfBirth;
    private String gender;
    // Add other relevant fields as per project requirements
}
*/
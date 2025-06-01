package com.ltfs.cdp.datavalidation.service;

import org.springframework.stereotype.Service;
import java.time.LocalDate;
import java.time.format.DateTimeParseException;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.regex.Pattern;

/**
 * Service responsible for applying predefined column-level validation rules to incoming data records.
 * This engine ensures data quality and consistency before data is processed further into the CDP system.
 * It supports various rule types like NOT_NULL, REGEX, MAX_LENGTH, IS_NUMERIC, IS_DATE, etc.
 *
 * In a production environment, the validation rules would typically be loaded dynamically
 * from a configuration service, database, or external file, rather than being hardcoded.
 */
@Service
public class ValidationRulesEngine {

    /**
     * A map to store validation rules, keyed by field name.
     * Each field can have multiple rules associated with it.
     */
    private final Map<String, List<ValidationRule>> validationRules;

    /**
     * Constructor for ValidationRulesEngine.
     * Initializes the validation rules. For this example, rules are hardcoded.
     * In a real application, consider injecting a service that provides these rules
     * from a persistent store or configuration.
     */
    public ValidationRulesEngine() {
        this.validationRules = new HashMap<>();
        initializeDefaultRules();
    }

    /**
     * Initializes a set of default validation rules.
     * These rules are examples and should be replaced with actual business rules
     * loaded dynamically in a production system.
     */
    private void initializeDefaultRules() {
        // Rules for 'customerId': Must not be null/empty, must match a specific alphanumeric pattern (8-15 chars)
        validationRules.computeIfAbsent("customerId", k -> new ArrayList<>()).add(
                new ValidationRule("customerId", RuleType.NOT_NULL, null, "Customer ID cannot be null."));
        validationRules.computeIfAbsent("customerId", k -> new ArrayList<>()).add(
                new ValidationRule("customerId", RuleType.NOT_EMPTY, null, "Customer ID cannot be empty."));
        validationRules.computeIfAbsent("customerId", k -> new ArrayList<>()).add(
                new ValidationRule("customerId", RuleType.REGEX, "^[A-Z0-9]{8,15}$", "Customer ID must be alphanumeric (8-15 characters)."));

        // Rules for 'customerName': Must not be null, max length 100, allows letters, spaces, apostrophes, hyphens
        validationRules.computeIfAbsent("customerName", k -> new ArrayList<>()).add(
                new ValidationRule("customerName", RuleType.NOT_NULL, null, "Customer Name cannot be null."));
        validationRules.computeIfAbsent("customerName", k -> new ArrayList<>()).add(
                new ValidationRule("customerName", RuleType.MAX_LENGTH, "100", "Customer Name cannot exceed 100 characters."));
        validationRules.computeIfAbsent("customerName", k -> new ArrayList<>()).add(
                new ValidationRule("customerName", RuleType.REGEX, "^[a-zA-Z\\s.'-]+$", "Customer Name contains invalid characters."));

        // Rules for 'loanAmount': Must not be null, must be numeric, minimum value 1000
        validationRules.computeIfAbsent("loanAmount", k -> new ArrayList<>()).add(
                new ValidationRule("loanAmount", RuleType.NOT_NULL, null, "Loan Amount cannot be null."));
        validationRules.computeIfAbsent("loanAmount", k -> new ArrayList<>()).add(
                new ValidationRule("loanAmount", RuleType.IS_NUMERIC, null, "Loan Amount must be a numeric value."));
        validationRules.computeIfAbsent("loanAmount", k -> new ArrayList<>()).add(
                new ValidationRule("loanAmount", RuleType.MIN_VALUE, "1000", "Loan Amount must be at least 1000."));

        // Rules for 'offerDate': Must not be null, must be a valid date in YYYY-MM-DD format
        validationRules.computeIfAbsent("offerDate", k -> new ArrayList<>()).add(
                new ValidationRule("offerDate", RuleType.NOT_NULL, null, "Offer Date cannot be null."));
        validationRules.computeIfAbsent("offerDate", k -> new ArrayList<>()).add(
                new ValidationRule("offerDate", RuleType.IS_DATE, "yyyy-MM-dd", "Offer Date must be in YYYY-MM-DD format."));

        // Rules for 'email': Optional (no NOT_NULL), must match email regex, max length 255
        validationRules.computeIfAbsent("email", k -> new ArrayList<>()).add(
                new ValidationRule("email", RuleType.REGEX, "^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,6}$", "Invalid email format."));
        validationRules.computeIfAbsent("email", k -> new ArrayList<>()).add(
                new ValidationRule("email", RuleType.MAX_LENGTH, "255", "Email cannot exceed 255 characters."));

        // Rules for 'mobileNumber': Must not be null, must be a 10-digit Indian mobile number
        validationRules.computeIfAbsent("mobileNumber", k -> new ArrayList<>()).add(
                new ValidationRule("mobileNumber", RuleType.NOT_NULL, null, "Mobile Number cannot be null."));
        validationRules.computeIfAbsent("mobileNumber", k -> new ArrayList<>()).add(
                new ValidationRule("mobileNumber", RuleType.REGEX, "^[6-9]\\d{9}$", "Mobile Number must be a 10-digit Indian mobile number."));
    }

    /**
     * Validates a single data record against the predefined rules.
     *
     * @param record A Map representing a single data record, where keys are column names
     *               and values are the string representations of the data.
     * @return A List of {@link ValidationError} objects, detailing all validation failures.
     *         Returns an empty list if the record is valid.
     */
    public List<ValidationError> validateRecord(Map<String, String> record) {
        List<ValidationError> errors = new ArrayList<>();

        if (record == null) {
            errors.add(new ValidationError("record", "null", "Input record cannot be null."));
            return errors;
        }

        // Iterate through all defined validation rules for each field
        for (Map.Entry<String, List<ValidationRule>> entry : validationRules.entrySet()) {
            String fieldName = entry.getKey();
            List<ValidationRule> rulesForField = entry.getValue();
            String fieldValue = record.get(fieldName); // Get the raw value for the current field

            // Apply each rule for the current field
            for (ValidationRule rule : rulesForField) {
                boolean isValid = true;
                // Trim whitespace for string-based checks, but keep null if original was null
                String actualValue = (fieldValue != null) ? fieldValue.trim() : null;

                switch (rule.getRuleType()) {
                    case NOT_NULL:
                        if (actualValue == null) {
                            isValid = false;
                        }
                        break;
                    case NOT_EMPTY:
                        if (actualValue == null || actualValue.isEmpty()) {
                            isValid = false;
                        }
                        break;
                    case REGEX:
                        // Only apply regex if the value is not null or empty.
                        // If a field is mandatory and needs regex, it should also have NOT_NULL/NOT_EMPTY rules.
                        if (actualValue != null && !actualValue.isEmpty()) {
                            try {
                                isValid = Pattern.matches(rule.getRuleValue(), actualValue);
                            } catch (java.util.regex.PatternSyntaxException e) {
                                // This indicates an issue with the rule definition itself.
                                // In a production system, this should be logged using a proper logger (e.g., SLF4J).
                                System.err.println("ERROR: Invalid regex pattern defined for field '" + fieldName + "': " + rule.getRuleValue() + " - " + e.getMessage());
                                isValid = false; // Treat as invalid if the rule itself is malformed
                            }
                        }
                        break;
                    case MAX_LENGTH:
                        if (actualValue != null) {
                            try {
                                int maxLength = Integer.parseInt(rule.getRuleValue());
                                if (actualValue.length() > maxLength) {
                                    isValid = false;
                                }
                            } catch (NumberFormatException e) {
                                System.err.println("ERROR: Invalid MAX_LENGTH rule value for field '" + fieldName + "': " + rule.getRuleValue() + " - " + e.getMessage());
                                isValid = false;
                            }
                        }
                        break;
                    case MIN_LENGTH:
                        if (actualValue != null) {
                            try {
                                int minLength = Integer.parseInt(rule.getRuleValue());
                                if (actualValue.length() < minLength) {
                                    isValid = false;
                                }
                            } catch (NumberFormatException e) {
                                System.err.println("ERROR: Invalid MIN_LENGTH rule value for field '" + fieldName + "': " + rule.getRuleValue() + " - " + e.getMessage());
                                isValid = false;
                            }
                        }
                        break;
                    case IS_NUMERIC:
                        if (actualValue == null || actualValue.isEmpty()) {
                            isValid = false; // Null or empty is not numeric
                        } else {
                            try {
                                Double.parseDouble(actualValue); // Use Double to handle both integers and decimals
                            } catch (NumberFormatException e) {
                                isValid = false;
                            }
                        }
                        break;
                    case IS_DATE:
                        if (actualValue == null || actualValue.isEmpty()) {
                            isValid = false; // Null or empty is not a date
                        } else {
                            try {
                                // For simplicity, assuming ISO_LOCAL_DATE (yyyy-MM-dd) format.
                                // For custom date formats, use DateTimeFormatter.ofPattern(rule.getRuleValue()).parse(actualValue);
                                LocalDate.parse(actualValue);
                            } catch (DateTimeParseException e) {
                                isValid = false;
                            }
                        }
                        break;
                    case MIN_VALUE:
                        if (actualValue == null || actualValue.isEmpty()) {
                            isValid = false; // Cannot compare null/empty to a min value
                        } else {
                            try {
                                double actualNum = Double.parseDouble(actualValue);
                                double minNum = Double.parseDouble(rule.getRuleValue());
                                if (actualNum < minNum) {
                                    isValid = false;
                                }
                            } catch (NumberFormatException e) {
                                // If the value or rule value is not a number, it cannot satisfy MIN_VALUE
                                isValid = false;
                            }
                        }
                        break;
                    case MAX_VALUE:
                        if (actualValue == null || actualValue.isEmpty()) {
                            isValid = false; // Cannot compare null/empty to a max value
                        } else {
                            try {
                                double actualNum = Double.parseDouble(actualValue);
                                double maxNum = Double.parseDouble(rule.getRuleValue());
                                if (actualNum > maxNum) {
                                    isValid = false;
                                }
                            } catch (NumberFormatException e) {
                                // If the value or rule value is not a number, it cannot satisfy MAX_VALUE
                                isValid = false;
                            }
                        }
                        break;
                    default:
                        // Unknown rule type, log and skip or treat as invalid
                        System.err.println("WARNING: Unknown validation rule type: " + rule.getRuleType() + " for field: " + fieldName);
                        break;
                }

                if (!isValid) {
                    // Add the error and continue to check other rules for the same field or other fields.
                    // This ensures all validation failures for a record are collected.
                    errors.add(new ValidationError(fieldName, fieldValue, rule.getErrorMessage()));
                }
            }
        }

        return errors;
    }

    /**
     * Enum defining the types of validation rules supported by the engine.
     */
    public enum RuleType {
        NOT_NULL,       // Checks if the field value is null.
        NOT_EMPTY,      // Checks if the field value is an empty string (after trimming).
        REGEX,          // Checks if the field value matches a given regular expression.
        MAX_LENGTH,     // Checks if the field value's length exceeds a maximum.
        MIN_LENGTH,     // Checks if the field value's length is less than a minimum.
        IS_NUMERIC,     // Checks if the field value can be parsed as a number (integer or decimal).
        IS_DATE,        // Checks if the field value can be parsed as a date (e.g., YYYY-MM-DD).
        MIN_VALUE,      // For numeric fields, checks if the value is less than a minimum.
        MAX_VALUE       // For numeric fields, checks if the value is greater than a maximum.
    }

    /**
     * Represents a single validation rule configuration.
     * This class is immutable.
     */
    private static class ValidationRule {
        private final String fieldName;
        private final RuleType ruleType;
        private final String ruleValue; // e.g., regex pattern, max length, date format, min/max numeric value
        private final String errorMessage;

        /**
         * Constructs a new ValidationRule.
         *
         * @param fieldName    The name of the field this rule applies to.
         * @param ruleType     The type of validation to perform.
         * @param ruleValue    The value associated with the rule (e.g., regex string, length limit, date format). Can be null for some rule types (e.g., NOT_NULL).
         * @param errorMessage The error message to return if this rule fails.
         */
        public ValidationRule(String fieldName, RuleType ruleType, String ruleValue, String errorMessage) {
            this.fieldName = Objects.requireNonNull(fieldName, "Field name cannot be null for a validation rule.");
            this.ruleType = Objects.requireNonNull(ruleType, "Rule type cannot be null for a validation rule.");
            this.ruleValue = ruleValue; // Can be null
            this.errorMessage = Objects.requireNonNull(errorMessage, "Error message cannot be null for a validation rule.");
        }

        public String getFieldName() {
            return fieldName;
        }

        public RuleType getRuleType() {
            return ruleType;
        }

        public String getRuleValue() {
            return ruleValue;
        }

        public String getErrorMessage() {
            return errorMessage;
        }

        @Override
        public String toString() {
            return "ValidationRule{" +
                   "fieldName='" + fieldName + '\'' +
                   ", ruleType=" + ruleType +
                   ", ruleValue='" + (ruleValue != null ? ruleValue : "N/A") + '\'' +
                   ", errorMessage='" + errorMessage + '\'' +
                   '}';
        }
    }

    /**
     * Represents a single validation error found for a specific field in a record.
     * This class is immutable and provides details about the failed validation.
     */
    public static class ValidationError {
        private final String fieldName;
        private final String invalidValue; // The actual value that caused the validation failure
        private final String errorMessage; // The descriptive error message for the failure

        /**
         * Constructs a new ValidationError.
         *
         * @param fieldName    The name of the field that failed validation.
         * @param invalidValue The value of the field that was deemed invalid. Can be null if the field itself was missing.
         * @param errorMessage A descriptive message explaining why the validation failed.
         */
        public ValidationError(String fieldName, String invalidValue, String errorMessage) {
            this.fieldName = Objects.requireNonNull(fieldName, "Field name cannot be null for a validation error.");
            this.invalidValue = invalidValue; // Can be null
            this.errorMessage = Objects.requireNonNull(errorMessage, "Error message cannot be null for a validation error.");
        }

        public String getFieldName() {
            return fieldName;
        }

        public String getInvalidValue() {
            return invalidValue;
        }

        public String getErrorMessage() {
            return errorMessage;
        }

        @Override
        public String toString() {
            return "ValidationError{" +
                   "fieldName='" + fieldName + '\'' +
                   ", invalidValue='" + (invalidValue != null ? invalidValue : "null") + '\'' +
                   ", errorMessage='" + errorMessage + '\'' +
                   '}';
        }
    }
}
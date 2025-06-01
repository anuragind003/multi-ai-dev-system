package com.ltfs.cdp.validation.rules;

import com.ltfs.cdp.validation.model.ValidationResult; // Assuming ValidationResult class exists in this package

/**
 * Interface defining the contract for individual data validation rules within the LTFS Offer CDP system.
 * Each implementation of this interface will encapsulate a specific validation logic
 * to be applied to incoming data (e.g., from Offermart) before it is processed further
 * or stored in the CDP.
 *
 * <p>This interface supports generic data types, allowing rules to be applied to various
 * data entities such as DTOs representing customer, offer, or campaign data, or even
 * raw data structures like {@code Map<String, Object>} for flexible column-level validation.</p>
 *
 * @param <T> The type of data entity or object to be validated by this rule.
 *            This could be a specific DTO (e.g., {@code CustomerDataDTO}),
 *            or a more generic type like {@code Map<String, Object>} for dynamic data structures.
 */
public interface ValidationRule<T> {

    /**
     * Applies the specific validation logic defined by this rule to the given data entity.
     * Implementations should perform checks and return a {@link ValidationResult}
     * indicating success or failure, along with any detailed error messages.
     *
     * @param data The data entity of type {@code T} to be validated. This object
     *             contains the fields and values that the rule will inspect.
     * @return A {@link ValidationResult} object. If {@code ValidationResult.isValid()}
     *         returns {@code true}, the data passed the validation. If {@code false},
     *         the data failed, and {@code ValidationResult.getErrorMessages()} will
     *         contain a list of reasons for the failure.
     */
    ValidationResult validate(T data);

    /**
     * Returns a unique and descriptive name for this validation rule.
     * This name can be used for logging, reporting, configuration, or
     * identifying specific rules in a collection of rules.
     *
     * @return A {@code String} representing the name of this validation rule.
     *         Example: "CustomerEmailFormatRule", "LoanAmountRangeRule".
     */
    String getRuleName();

    /**
     * Provides a brief, human-readable description of what this validation rule checks.
     * This can be useful for documentation, debugging, or user interfaces.
     *
     * @return A {@code String} describing the purpose and scope of this validation rule.
     *         Example: "Ensures the customer's email address is in a valid format.",
     *         "Checks if the loan amount falls within the acceptable range [1000, 1000000]."
     */
    String getRuleDescription();
}
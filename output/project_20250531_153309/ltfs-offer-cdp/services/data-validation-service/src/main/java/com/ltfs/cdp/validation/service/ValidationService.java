package com.ltfs.cdp.validation.service;

import com.ltfs.cdp.validation.dto.CustomerOfferDataDto;
import com.ltfs.cdp.validation.dto.ValidationResult;
import com.ltfs.cdp.validation.rule.DataValidator;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import java.util.ArrayList;
import java.util.List;
import java.util.Objects;

/**
 * Service orchestrating the data validation process for incoming customer and offer data.
 * This service is responsible for applying a series of column-level validation rules
 * to ensure data quality before it's processed further into the CDP system.
 *
 * It aggregates multiple {@link DataValidator} implementations, allowing for a modular
 * and extensible validation pipeline.
 */
@Service
public class ValidationService {

    private static final Logger logger = LoggerFactory.getLogger(ValidationService.class);

    /**
     * A list of {@link DataValidator} instances that will be applied to the incoming data.
     * These validators are automatically injected by Spring, allowing for dynamic
     * discovery and application of all defined validation rules.
     */
    private final List<DataValidator> dataValidators;

    /**
     * Constructs a ValidationService with a list of injected DataValidator instances.
     * Spring's dependency injection mechanism will automatically find all beans
     * that implement the {@link DataValidator} interface and provide them as a list.
     * This design promotes extensibility, as new validation rules can be added
     * by simply creating new {@link DataValidator} implementations and marking them
     * as Spring components (e.g., with @Component).
     *
     * @param dataValidators A list of all {@link DataValidator} implementations available in the Spring context.
     * @throws NullPointerException if the injected dataValidators list is null (should not happen with Spring).
     */
    @Autowired
    public ValidationService(List<DataValidator> dataValidators) {
        // Ensure that the injected list of validators is not null.
        // Objects.requireNonNull provides a clear error message if this unexpected scenario occurs.
        this.dataValidators = Objects.requireNonNull(dataValidators, "Data validators list cannot be null.");
        logger.info("ValidationService initialized with {} data validators.", dataValidators.size());
        if (dataValidators.isEmpty()) {
            logger.warn("No DataValidator implementations found. Data validation will effectively be skipped.");
        }
    }

    /**
     * Validates the incoming customer and offer data DTO by applying all registered
     * {@link DataValidator} rules.
     *
     * The validation process involves iterating through each validator. If any validator
     * identifies issues, the overall data is marked as invalid, and all collected error
     * messages are returned. This method is designed to be fault-tolerant, meaning an
     * error in one validator will not halt the entire validation process, but rather
     * log the issue and continue with other validators.
     *
     * @param customerOfferDataDto The DTO containing customer and offer data to be validated.
     *                             This DTO is expected to encapsulate all necessary fields
     *                             for column-level validation.
     * @return A {@link ValidationResult} object. This object contains a boolean flag
     *         indicating whether the data is valid (true if no errors were found by any validator)
     *         and a list of error messages if validation failures occurred.
     * @throws IllegalArgumentException if the input {@code customerOfferDataDto} is null,
     *                                  as validation cannot proceed without data.
     */
    public ValidationResult validate(CustomerOfferDataDto customerOfferDataDto) {
        // Pre-check for null input to prevent NullPointerExceptions downstream.
        if (customerOfferDataDto == null) {
            logger.error("Attempted to validate a null CustomerOfferDataDto. This is not allowed.");
            throw new IllegalArgumentException("CustomerOfferDataDto cannot be null for validation.");
        }

        // Log the start of validation, using a unique identifier from the DTO for traceability.
        // Assuming CustomerOfferDataDto has a getUniqueId() method for logging purposes.
        logger.debug("Starting validation for data record with unique ID: {}", customerOfferDataDto.getUniqueId());

        List<String> errors = new ArrayList<>(); // Accumulator for all validation error messages.
        boolean isValid = true; // Flag to track overall validation status.

        // Iterate through each injected DataValidator.
        for (DataValidator validator : dataValidators) {
            try {
                // Execute the validation logic for the current validator.
                List<String> validatorErrors = validator.validate(customerOfferDataDto);

                // If the validator returned errors, add them to the collective list and mark as invalid.
                if (validatorErrors != null && !validatorErrors.isEmpty()) {
                    errors.addAll(validatorErrors);
                    isValid = false; // Mark overall validation as failed.
                    logger.debug("Validator '{}' found {} errors for record ID: {}.",
                                 validator.getClass().getSimpleName(), validatorErrors.size(), customerOfferDataDto.getUniqueId());
                }
            } catch (Exception e) {
                // Robust error handling: If a specific validator throws an unexpected exception,
                // log the error, add a system error message to the results, and mark the data as invalid.
                // This prevents a single faulty validator from crashing the entire validation pipeline.
                logger.error("System error encountered during validation by '{}' for record ID: {}. Error: {}",
                             validator.getClass().getSimpleName(), customerOfferDataDto.getUniqueId(), e.getMessage(), e);
                errors.add("System error during validation by " + validator.getClass().getSimpleName() + ": " + e.getMessage());
                isValid = false; // A system error during validation also means the data is not fully validated.
            }
        }

        // Construct the final ValidationResult based on the accumulated status and errors.
        ValidationResult result = new ValidationResult(isValid, errors);

        // Log the final outcome of the validation process.
        if (isValid) {
            logger.info("Data validation successful for record ID: {}.", customerOfferDataDto.getUniqueId());
        } else {
            logger.warn("Data validation failed for record ID: {}. Total errors found: {}.",
                        customerOfferDataDto.getUniqueId(), errors.size());
        }
        return result;
    }
}
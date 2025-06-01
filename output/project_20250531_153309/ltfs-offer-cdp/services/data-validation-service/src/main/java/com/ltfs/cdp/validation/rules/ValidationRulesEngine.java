package com.ltfs.cdp.validation.rules;

import com.ltfs.cdp.validation.model.OverallValidationResult;
import com.ltfs.cdp.validation.model.ValidationResult;
import com.ltfs.cdp.validation.rule.ValidationRule;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.stream.Collectors;

/**
 * {@code ValidationRulesEngine} is a core component of the data validation service.
 * It is responsible for loading and applying a set of predefined validation rules
 * to incoming data records.
 *
 * This engine orchestrates the execution of individual {@link ValidationRule} instances,
 * aggregates their results, and provides an overall validation status for each data record.
 * It is designed to be extensible, allowing new validation rules to be easily added
 * and automatically picked up by Spring's dependency injection mechanism.
 *
 * The engine expects data records to be provided as a {@code Map<String, Object>},
 * which is suitable for column-level validation on generic data structures
 * (e.g., data rows from Offermart).
 */
@Service
public class ValidationRulesEngine {

    private static final Logger log = LoggerFactory.getLogger(ValidationRulesEngine.class);

    /**
     * A list of all active validation rules injected by Spring.
     * Spring will automatically discover and inject all beans that implement the {@link ValidationRule} interface.
     * This allows for easy addition of new validation logic by simply creating new {@link ValidationRule}
     * implementations and marking them as Spring components.
     */
    private final List<ValidationRule> validationRules;

    /**
     * Constructs a new {@code ValidationRulesEngine} with the given list of validation rules.
     * Spring's dependency injection mechanism will automatically provide all beans
     * that implement the {@link ValidationRule} interface.
     *
     * @param validationRules A list of {@link ValidationRule} instances to be applied by this engine.
     *                        This list is expected to be populated by Spring. If no rules are found,
     *                        an empty list will be used.
     */
    public ValidationRulesEngine(List<ValidationRule> validationRules) {
        // Ensure that the injected list is not null, even if empty, to prevent NullPointerExceptions.
        this.validationRules = Objects.requireNonNullElseGet(validationRules, ArrayList::new);
        log.info("ValidationRulesEngine initialized with {} rules.", this.validationRules.size());
        this.validationRules.forEach(rule -> log.debug("  - Loaded rule: {}", rule.getRuleName()));
    }

    /**
     * Applies all configured validation rules to a single data record.
     * Each rule is executed independently, and their individual results are aggregated
     * into an {@link OverallValidationResult}.
     *
     * If an exception occurs during the execution of a specific rule, it is caught,
     * logged, and reported as a failure for that rule, allowing other rules to proceed
     * without crashing the entire validation process.
     *
     * @param data The data record to validate. This is typically a {@code Map<String, Object>}
     *             representing a row of data from the Offermart system, or a similar generic structure.
     *             It should not be null.
     * @return An {@link OverallValidationResult} containing the aggregated validation status
     *         and a list of individual {@link ValidationResult} for each rule applied.
     *         Returns an overall failure if the input data is null or if any rule fails.
     *         If no rules are configured, the data is considered valid by default.
     */
    public OverallValidationResult applyRules(Map<String, Object> data) {
        if (data == null) {
            log.warn("Attempted to validate a null data record. Returning overall failure.");
            return OverallValidationResult.fail("Input data record cannot be null for validation.");
        }

        List<ValidationResult> individualResults = new ArrayList<>();
        boolean overallSuccess = true;

        // If no validation rules are configured, the data is considered valid by default.
        if (validationRules.isEmpty()) {
            log.warn("No validation rules configured. Data record will be considered valid by default.");
            return OverallValidationResult.success("No validation rules configured.");
        }

        // Iterate through each configured validation rule and apply it to the data record.
        for (ValidationRule rule : validationRules) {
            ValidationResult ruleResult;
            try {
                log.debug("Applying rule '{}' to data record.", rule.getRuleName());
                ruleResult = rule.validate(data); // Execute the validation logic for the current rule.

                if (!ruleResult.isSuccess()) {
                    overallSuccess = false; // If any individual rule fails, the overall validation fails.
                    log.debug("Rule '{}' failed: {}", rule.getRuleName(), ruleResult.getErrorMessages());
                } else {
                    log.debug("Rule '{}' passed.", rule.getRuleName());
                }
            } catch (Exception e) {
                // Catch any unexpected exceptions that might occur during a rule's execution.
                // This prevents a single faulty rule from stopping the entire validation process.
                log.error("An unexpected error occurred while applying rule '{}': {}", rule.getRuleName(), e.getMessage(), e);
                ruleResult = ValidationResult.fail(rule.getRuleName(), "Internal error during rule execution: " + e.getMessage());
                overallSuccess = false; // An internal error in a rule also marks the overall validation as failed.
            }
            individualResults.add(ruleResult); // Add the result of the current rule to the list.
        }

        // Return the aggregated result.
        return new OverallValidationResult(overallSuccess, individualResults);
    }

    /**
     * Applies all configured validation rules to a list of data records in a batch.
     * This method iterates through each record in the provided list and applies the rules
     * using the {@link #applyRules(Map)} method.
     *
     * @param dataRecords A list of data records (each a {@code Map<String, Object>}) to validate.
     *                    Can be an empty list, but not null.
     * @return A {@code Map} where the key is the original data record and the value is its
     *         {@link OverallValidationResult}. This map contains the validation outcome for each
     *         record in the batch.
     *         Returns an empty map if the input list is null or empty.
     */
    public Map<Map<String, Object>, OverallValidationResult> applyRulesBatch(List<Map<String, Object>> dataRecords) {
        if (dataRecords == null || dataRecords.isEmpty()) {
            log.warn("Attempted to validate a null or empty list of data records in batch. Returning empty map.");
            return java.util.Collections.emptyMap();
        }

        log.info("Starting batch validation for {} data records.", dataRecords.size());

        // Use Java Streams to efficiently process the batch.
        // Each record is mapped to its validation result using the applyRules method.
        return dataRecords.stream()
                .collect(Collectors.toMap(
                        record -> record, // The key of the map is the original data record.
                        this::applyRules  // The value is the OverallValidationResult obtained by applying rules to the record.
                ));
    }
}
package com.ltfs.cdp.bre.controller;

import com.ltfs.cdp.bre.dto.RuleExecutionRequest;
import com.ltfs.cdp.bre.dto.RuleExecutionResult;
import com.ltfs.cdp.bre.exception.RuleEngineException;
import com.ltfs.cdp.bre.service.RuleEngineService;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import javax.validation.Valid;

/**
 * REST API controller for managing and triggering the execution of business rules
 * within the LTFS Offer CDP's Business Rule Engine (BRE) service.
 * This controller provides endpoints to initiate rule evaluation based on incoming data.
 */
@RestController
@RequestMapping("/api/v1/rules")
public class RuleController {

    private static final Logger logger = LoggerFactory.getLogger(RuleController.class);

    private final RuleEngineService ruleEngineService;

    /**
     * Constructs a new RuleController with the given RuleEngineService.
     * Spring's dependency injection will automatically provide the RuleEngineService instance.
     *
     * @param ruleEngineService The service responsible for executing business rules.
     */
    @Autowired
    public RuleController(RuleEngineService ruleEngineService) {
        this.ruleEngineService = ruleEngineService;
    }

    /**
     * Endpoint to trigger the execution of business rules.
     * This method accepts a {@link RuleExecutionRequest} containing the data context
     * on which the rules should be evaluated.
     *
     * <p>
     * The request body should be a JSON object conforming to the {@link RuleExecutionRequest} structure,
     * typically including a `requestId` for traceability and a `dataContext` map
     * holding the key-value pairs relevant for rule evaluation (e.g., customer details, offer attributes).
     * </p>
     *
     * <p>
     * Example Request Body:
     * <pre>
     * {
     *   "requestId": "BRE-EXEC-20231027-001",
     *   "ruleSetName": "DEDUPLICATION_RULES", // Optional: to specify a subset of rules
     *   "dataContext": {
     *     "customerId": "CUST12345",
     *     "loanProductType": "Consumer Loan",
     *     "offerAmount": 50000,
     *     "isPreApproved": true,
     *     "existingLoanIds": ["L1001", "L1002"]
     *   }
     * }
     * </pre>
     * </p>
     *
     * @param request The {@link RuleExecutionRequest} containing the data context for rule evaluation.
     *                The request is validated using JSR 303 annotations (e.g., @NotBlank, @NotNull).
     * @return A {@link ResponseEntity} containing a {@link RuleExecutionResult} and an appropriate HTTP status.
     *         - {@code HttpStatus.OK} (200) if rules are executed successfully.
     *         - {@code HttpStatus.BAD_REQUEST} (400) if the input request is invalid.
     *         - {@code HttpStatus.INTERNAL_SERVER_ERROR} (500) if an unexpected error occurs during rule processing.
     */
    @PostMapping("/execute")
    public ResponseEntity<RuleExecutionResult> executeRules(@Valid @RequestBody RuleExecutionRequest request) {
        // Log the incoming request for auditing and debugging purposes.
        // Avoid logging sensitive data directly.
        logger.info("Received request to execute rules. Request ID: {}", request.getRequestId());

        try {
            // Delegate the actual rule execution logic to the RuleEngineService.
            RuleExecutionResult result = ruleEngineService.executeRules(request);

            // Log successful completion and return OK status with the result.
            logger.info("Rule execution completed successfully for Request ID: {}. Status: {}", request.getRequestId(), result.getStatus());
            return new ResponseEntity<>(result, HttpStatus.OK);

        } catch (RuleEngineException e) {
            // Catch specific exceptions from the rule engine service.
            // This indicates a business-level error during rule processing.
            logger.error("Rule engine error during execution for Request ID: {}: {}", request.getRequestId(), e.getMessage(), e);
            // Return an internal server error or a more specific status if applicable,
            // along with a result indicating failure.
            return new ResponseEntity<>(
                new RuleExecutionResult(request.getRequestId(), "FAILED", "Rule engine processing error: " + e.getMessage()),
                HttpStatus.INTERNAL_SERVER_ERROR
            );
        } catch (Exception e) {
            // Catch any other unexpected exceptions that might occur.
            logger.error("An unexpected error occurred during rule execution for Request ID: {}: {}", request.getRequestId(), e.getMessage(), e);
            // Return an internal server error with a generic failure message.
            return new ResponseEntity<>(
                new RuleExecutionResult(request.getRequestId(), "FAILED", "An unexpected error occurred: " + e.getMessage()),
                HttpStatus.INTERNAL_SERVER_ERROR
            );
        }
    }

    // Additional endpoints for managing rules (e.g., retrieving rule definitions,
    // deploying new rules) could be added here if the BRE service is also
    // responsible for rule lifecycle management.
    // For this task, the primary focus is on triggering rule execution.
}
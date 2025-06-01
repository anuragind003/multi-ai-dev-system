package com.ltfs.cdp.bre.controller;

import com.ltfs.cdp.bre.service.RuleExecutionService;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.Map;
import java.util.Objects;

/**
 * REST Controller for executing business rules within the LTFS Offer CDP's Business Rule Engine (BRE) service.
 * This controller exposes an endpoint to trigger the business rule engine
 * with a given set of facts (input data) and receive the processed output.
 * It acts as the entry point for external systems or other microservices
 * to leverage the BRE capabilities for tasks like data validation, deduplication,
 * and offer eligibility determination.
 */
@RestController
@RequestMapping("/api/v1/bre/rules") // Base path for rule execution endpoints, following API versioning best practices.
public class RuleExecutionController {

    private static final Logger logger = LoggerFactory.getLogger(RuleExecutionController.class);

    private final RuleExecutionService ruleExecutionService;

    /**
     * Constructs a new RuleExecutionController with the specified RuleExecutionService.
     * Spring's dependency injection automatically provides the RuleExecutionService instance,
     * ensuring that the controller has access to the core business logic for rule execution.
     *
     * @param ruleExecutionService The service responsible for executing business rules.
     */
    @Autowired
    public RuleExecutionController(RuleExecutionService ruleExecutionService) {
        this.ruleExecutionService = ruleExecutionService;
    }

    /**
     * Executes business rules based on the provided facts.
     *
     * This endpoint accepts a JSON object representing the facts (input data)
     * and passes them to the business rule engine for evaluation. The engine
     * processes these facts according to predefined rules (e.g., for deduplication,
     * validation, or offer eligibility) and returns the modified or derived facts.
     *
     * Example Request Body:
     * {
     *     "customer_id": "CUST123",
     *     "loan_amount": 50000,
     *     "product_type": "Consumer Loan",
     *     "is_preapproved": true
     * }
     *
     * @param facts A {@code Map<String, Object>} representing the input data
     *              (facts) for rule evaluation. This map is expected to be
     *              sent as the request body in JSON format. The generic map
     *              allows for flexible input structures based on the rules being executed.
     * @return A {@code ResponseEntity<Map<String, Object>>} containing the
     *         output or modified facts after rule execution, along with an
     *         appropriate HTTP status code.
     *         - {@code HttpStatus.OK (200)} if rules are executed successfully,
     *           with the processed facts in the response body.
     *         - {@code HttpStatus.BAD_REQUEST (400)} if the input facts are null or empty,
     *           indicating an invalid request payload.
     *         - {@code HttpStatus.INTERNAL_SERVER_ERROR (500)} if an unexpected
     *           error occurs during rule execution within the service layer.
     */
    @PostMapping("/execute")
    public ResponseEntity<Map<String, Object>> executeRules(@RequestBody Map<String, Object> facts) {
        // Log the incoming request for auditing and debugging purposes.
        logger.info("Received request to execute rules. Incoming facts: {}", facts);

        // Validate input facts. A null or empty map of facts might indicate an invalid request.
        // This basic validation prevents unnecessary processing and provides immediate feedback to the client.
        if (Objects.isNull(facts) || facts.isEmpty()) {
            logger.warn("Bad Request: Input facts are null or empty. Cannot proceed with rule execution.");
            // Return a 400 Bad Request status with a descriptive error message.
            return new ResponseEntity<>(Map.of("error", "Input facts cannot be null or empty. Please provide valid data."), HttpStatus.BAD_REQUEST);
        }

        try {
            // Delegate the core rule execution logic to the RuleExecutionService.
            // This separation of concerns keeps the controller lean and focused on HTTP request handling.
            Map<String, Object> resultFacts = ruleExecutionService.executeRules(facts);

            // Log the successful execution and the result facts returned by the service.
            logger.info("Rules executed successfully. Result facts: {}", resultFacts);

            // Return the processed facts with an OK (200) status, indicating successful operation.
            return new ResponseEntity<>(resultFacts, HttpStatus.OK);
        } catch (Exception e) {
            // Catch any unexpected exceptions that might occur during rule execution in the service layer.
            // This ensures that the API gracefully handles errors and provides a consistent error response.
            logger.error("An unexpected error occurred during rule execution for facts: {}. Error: {}", facts, e.getMessage(), e);

            // Return an internal server error (500) response with a generic error message
            // and potentially the exception details for debugging (in a controlled environment).
            return new ResponseEntity<>(Map.of("error", "Failed to execute rules due to an internal server error.", "details", e.getMessage()), HttpStatus.INTERNAL_SERVER_ERROR);
        }
    }
}
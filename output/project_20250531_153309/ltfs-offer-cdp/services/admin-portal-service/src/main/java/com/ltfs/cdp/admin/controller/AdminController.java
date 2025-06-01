package com.ltfs.cdp.admin.controller;

import com.ltfs.cdp.admin.dto.AdminConfigDTO;
import com.ltfs.cdp.admin.exception.AdminOperationException;
import com.ltfs.cdp.admin.service.AdminService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.responses.ApiResponse;
import io.swagger.v3.oas.annotations.responses.ApiResponses;
import io.swagger.v3.oas.annotations.tags.Tag;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

/**
 * REST API controller for admin-specific functionalities within the LTFS Offer CDP system.
 * This controller provides endpoints to manage system operations such as data ingestion,
 * deduplication triggers, and configuration management.
 *
 * It leverages Spring Boot's REST capabilities and integrates with a service layer
 * for business logic execution.
 */
@RestController
@RequestMapping("/api/v1/admin")
@Tag(name = "Admin Portal", description = "APIs for administrative functionalities of the CDP system, including data ingestion, deduplication, and configuration management.")
public class AdminController {

    private static final Logger logger = LoggerFactory.getLogger(AdminController.class);

    private final AdminService adminService;

    /**
     * Constructs an AdminController with the necessary AdminService dependency.
     * Spring's dependency injection will automatically provide the AdminService instance.
     *
     * @param adminService The service responsible for executing admin-related business logic.
     */
    @Autowired
    public AdminController(AdminService adminService) {
        this.adminService = adminService;
    }

    /**
     * Health check endpoint for the admin portal service.
     * This endpoint can be used by monitoring systems to verify the service's operational status.
     *
     * @return A {@link ResponseEntity} with a success message and HTTP status 200 (OK).
     */
    @Operation(summary = "Check health of the Admin Portal Service",
               description = "Returns a simple status to indicate if the service is operational and responsive.")
    @ApiResponse(responseCode = "200", description = "Service is up and running")
    @GetMapping("/health")
    public ResponseEntity<String> healthCheck() {
        logger.info("Admin health check requested.");
        return ResponseEntity.ok("Admin Portal Service is up and running!");
    }

    /**
     * Triggers the data ingestion process from Offermart into the CDP system.
     * This operation is typically asynchronous, initiating a background process to fetch
     * and validate data from external sources.
     *
     * @return A {@link ResponseEntity} indicating the status of the trigger.
     *         Returns 202 (Accepted) if the process is successfully initiated,
     *         or 500 (Internal Server Error) if an error occurs during initiation.
     */
    @Operation(summary = "Trigger data ingestion from Offermart",
               description = "Initiates the process of ingesting customer and offer data from Offermart into the CDP system. This operation is typically asynchronous and involves basic column-level validation.")
    @ApiResponses(value = {
        @ApiResponse(responseCode = "202", description = "Data ingestion process initiated successfully"),
        @ApiResponse(responseCode = "500", description = "Internal server error during initiation of data ingestion")
    })
    @PostMapping("/trigger-ingestion")
    public ResponseEntity<String> triggerDataIngestion() {
        logger.info("Request received to trigger data ingestion from Offermart.");
        try {
            // Delegate the actual business logic to the AdminService.
            // This method is expected to initiate an asynchronous process (e.g., by publishing an event).
            adminService.triggerOffermartDataIngestion();
            return ResponseEntity.accepted().body("Data ingestion process initiated successfully.");
        } catch (AdminOperationException e) {
            // Catch specific business exceptions related to admin operations.
            logger.error("Failed to trigger data ingestion: {}", e.getMessage(), e);
            return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR).body("Failed to trigger data ingestion: " + e.getMessage());
        } catch (Exception e) {
            // Catch any unexpected runtime exceptions.
            logger.error("An unexpected error occurred while triggering data ingestion: {}", e.getMessage(), e);
            return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR).body("An unexpected error occurred: " + e.getMessage());
        }
    }

    /**
     * Triggers the deduplication process across all Consumer Loan products.
     * This operation is crucial for maintaining a single profile view of the customer
     * and involves applying dedupe logic against the 'live book' (Customer 360).
     * It is typically a resource-intensive and potentially long-running asynchronous process.
     *
     * @return A {@link ResponseEntity} indicating the status of the trigger.
     *         Returns 202 (Accepted) if the process is successfully initiated,
     *         or 500 (Internal Server Error) if an error occurs during initiation.
     */
    @Operation(summary = "Trigger deduplication process",
               description = "Initiates the deduplication logic across all Consumer Loan products (Loyalty, Preapproved, E-aggregator etc.) and against the 'live book' (Customer 360). Top-up loan offers are deduped only within other Top-up offers. This operation can be resource-intensive and might run asynchronously.")
    @ApiResponses(value = {
        @ApiResponse(responseCode = "202", description = "Deduplication process initiated successfully"),
        @ApiResponse(responseCode = "500", description = "Internal server error during initiation of deduplication")
    })
    @PostMapping("/trigger-deduplication")
    public ResponseEntity<String> triggerDeduplication() {
        logger.info("Request received to trigger deduplication process.");
        try {
            // Delegate the actual business logic to the AdminService.
            // This method is expected to initiate an asynchronous process.
            adminService.triggerDeduplicationProcess();
            return ResponseEntity.accepted().body("Deduplication process initiated successfully.");
        } catch (AdminOperationException e) {
            logger.error("Failed to trigger deduplication: {}", e.getMessage(), e);
            return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR).body("Failed to trigger deduplication: " + e.getMessage());
        } catch (Exception e) {
            logger.error("An unexpected error occurred while triggering deduplication: {}", e.getMessage(), e);
            return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR).body("An unexpected error occurred: " + e.getMessage());
        }
    }

    /**
     * Retrieves the current administrative configuration settings for the CDP system.
     * This could include parameters like deduplication thresholds, validation rule toggles, etc.
     *
     * @return A {@link ResponseEntity} containing the {@link AdminConfigDTO} with current settings
     *         and HTTP status 200 (OK), or 500 (Internal Server Error) if retrieval fails.
     */
    @Operation(summary = "Get admin configuration",
               description = "Retrieves the current administrative configuration settings for the CDP system, such as deduplication thresholds or validation rule statuses.")
    @ApiResponses(value = {
        @ApiResponse(responseCode = "200", description = "Admin configuration retrieved successfully"),
        @ApiResponse(responseCode = "500", description = "Internal server error while retrieving configuration")
    })
    @GetMapping("/config")
    public ResponseEntity<AdminConfigDTO> getAdminConfiguration() {
        logger.info("Request received to get admin configuration.");
        try {
            AdminConfigDTO config = adminService.getAdminConfiguration();
            return ResponseEntity.ok(config);
        } catch (AdminOperationException e) {
            logger.error("Failed to retrieve admin configuration: {}", e.getMessage(), e);
            return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR).body(null); // Return null body or an error DTO
        } catch (Exception e) {
            logger.error("An unexpected error occurred while retrieving admin configuration: {}", e.getMessage(), e);
            return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR).body(null);
        }
    }

    /**
     * Updates the administrative configuration settings for the CDP system.
     * The new configuration is provided in the request body.
     *
     * @param configDTO The {@link AdminConfigDTO} containing the new configuration settings.
     * @return A {@link ResponseEntity} containing the updated {@link AdminConfigDTO}
     *         and HTTP status 200 (OK), 400 (Bad Request) if input is invalid,
     *         or 500 (Internal Server Error) if the update fails.
     */
    @Operation(summary = "Update admin configuration",
               description = "Updates the administrative configuration settings for the CDP system. Requires a request body with the new configuration parameters.")
    @ApiResponses(value = {
        @ApiResponse(responseCode = "200", description = "Admin configuration updated successfully"),
        @ApiResponse(responseCode = "400", description = "Invalid configuration data provided"),
        @ApiResponse(responseCode = "500", description = "Internal server error during configuration update")
    })
    @PutMapping("/config")
    public ResponseEntity<AdminConfigDTO> updateAdminConfiguration(@RequestBody AdminConfigDTO configDTO) {
        logger.info("Request received to update admin configuration: {}", configDTO);
        try {
            // Basic validation of the incoming DTO. More complex validation should be in the service layer.
            if (configDTO == null) {
                logger.warn("Received null admin configuration DTO.");
                return ResponseEntity.badRequest().body(null);
            }
            // Example of a simple validation rule: dedupe threshold must be within a valid range.
            if (configDTO.getDedupeThreshold() < 0 || configDTO.getDedupeThreshold() > 1) {
                logger.warn("Invalid dedupe threshold provided: {}", configDTO.getDedupeThreshold());
                return ResponseEntity.badRequest().body(null); // Or return a more specific error DTO
            }

            AdminConfigDTO updatedConfig = adminService.updateAdminConfiguration(configDTO);
            return ResponseEntity.ok(updatedConfig);
        } catch (AdminOperationException e) {
            logger.error("Failed to update admin configuration: {}", e.getMessage(), e);
            return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR).body(null);
        } catch (Exception e) {
            logger.error("An unexpected error occurred while updating admin configuration: {}", e.getMessage(), e);
            return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR).body(null);
        }
    }
}
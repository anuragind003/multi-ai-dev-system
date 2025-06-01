package com.ltfs.cdp.reporting.controller;

import com.ltfs.cdp.reporting.dto.ReportGenerationRequest;
import com.ltfs.cdp.reporting.dto.ReportGenerationResponse;
import com.ltfs.cdp.reporting.dto.ReportStatusResponse;
import com.ltfs.cdp.reporting.exception.ReportNotFoundException;
import com.ltfs.cdp.reporting.exception.ReportGenerationException;
import com.ltfs.cdp.reporting.service.ReportService;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.core.io.ByteArrayResource;
import org.springframework.core.io.Resource;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import javax.validation.Valid;

/**
 * REST API controller for handling report generation and retrieval requests.
 * Provides endpoints for initiating report generation, checking report status,
 * and downloading completed reports.
 */
@RestController
@RequestMapping("/api/v1/reports")
public class ReportController {

    private static final Logger logger = LoggerFactory.getLogger(ReportController.class);

    private final ReportService reportService;

    /**
     * Constructs a new ReportController with the given ReportService.
     * Spring's dependency injection automatically provides the ReportService instance.
     *
     * @param reportService The service responsible for report generation logic.
     */
    @Autowired
    public ReportController(ReportService reportService) {
        this.reportService = reportService;
    }

    /**
     * Initiates the generation of a new report based on the provided request.
     * This operation is typically asynchronous, and the response will contain a report ID
     * that can be used to check the status or download the report later.
     *
     * @param request The {@link ReportGenerationRequest} containing details like report type and parameters.
     * @return A {@link ResponseEntity} containing {@link ReportGenerationResponse} with the report ID
     *         and initial status, or an error message.
     */
    @PostMapping("/generate")
    public ResponseEntity<ReportGenerationResponse> generateReport(@Valid @RequestBody ReportGenerationRequest request) {
        logger.info("Received request to generate report: {}", request.getReportType());
        try {
            ReportGenerationResponse response = reportService.initiateReportGeneration(request);
            logger.info("Report generation initiated successfully for report ID: {}", response.getReportId());
            // Return 202 Accepted as report generation is typically an asynchronous process
            return new ResponseEntity<>(response, HttpStatus.ACCEPTED);
        } catch (ReportGenerationException e) {
            logger.error("Error initiating report generation for type {}: {}", request.getReportType(), e.getMessage());
            // Return 400 Bad Request for issues with the request parameters
            return new ResponseEntity<>(new ReportGenerationResponse(null, "FAILED", e.getMessage()), HttpStatus.BAD_REQUEST);
        } catch (Exception e) {
            logger.error("An unexpected error occurred during report generation initiation for type {}: {}", request.getReportType(), e.getMessage(), e);
            // Return 500 Internal Server Error for unexpected issues
            return new ResponseEntity<>(new ReportGenerationResponse(null, "FAILED", "Internal server error during report generation initiation."), HttpStatus.INTERNAL_SERVER_ERROR);
        }
    }

    /**
     * Retrieves the current status of a previously initiated report.
     *
     * @param reportId The unique identifier of the report.
     * @return A {@link ResponseEntity} containing {@link ReportStatusResponse} with the report's
     *         current status (e.g., PENDING, IN_PROGRESS, COMPLETED, FAILED) and potentially a download URL.
     */
    @GetMapping("/{reportId}/status")
    public ResponseEntity<ReportStatusResponse> getReportStatus(@PathVariable String reportId) {
        logger.info("Received request to get status for report ID: {}", reportId);
        try {
            ReportStatusResponse status = reportService.getReportStatus(reportId);
            logger.debug("Status for report ID {} is: {}", reportId, status.getStatus());
            return ResponseEntity.ok(status);
        } catch (ReportNotFoundException e) {
            logger.warn("Report with ID {} not found when checking status: {}", reportId, e.getMessage());
            // Return 404 Not Found if the report ID does not exist
            return new ResponseEntity<>(new ReportStatusResponse(reportId, "NOT_FOUND", null, e.getMessage()), HttpStatus.NOT_FOUND);
        } catch (Exception e) {
            logger.error("An unexpected error occurred while fetching status for report ID {}: {}", reportId, e.getMessage(), e);
            // Return 500 Internal Server Error for unexpected issues
            return new ResponseEntity<>(new ReportStatusResponse(reportId, "ERROR", null, "Internal server error while fetching report status."), HttpStatus.INTERNAL_SERVER_ERROR);
        }
    }

    /**
     * Downloads a completed report.
     * The report content is returned as a byte array, with appropriate content type and disposition headers.
     *
     * @param reportId The unique identifier of the report to download.
     * @return A {@link ResponseEntity} containing the report file as a byte array,
     *         or an error response if the report is not found, not ready, or an error occurs.
     */
    @GetMapping("/{reportId}/download")
    public ResponseEntity<Resource> downloadReport(@PathVariable String reportId) {
        logger.info("Received request to download report ID: {}", reportId);
        try {
            // The service should return the byte array of the report and its content type/filename
            byte[] reportBytes = reportService.downloadReport(reportId);
            String fileName = reportService.getReportFileName(reportId); // Assume service provides filename
            String contentType = reportService.getReportContentType(reportId); // Assume service provides content type

            if (reportBytes == null || reportBytes.length == 0) {
                logger.warn("Report content for ID {} is empty or not available.", reportId);
                return new ResponseEntity<>(HttpStatus.NO_CONTENT); // Or 404 if it implies not found
            }

            ByteArrayResource resource = new ByteArrayResource(reportBytes);

            // Set headers for file download
            HttpHeaders headers = new HttpHeaders();
            headers.add(HttpHeaders.CONTENT_DISPOSITION, "attachment; filename=\"" + fileName + "\"");
            headers.add(HttpHeaders.CACHE_CONTROL, "no-cache, no-store, must-revalidate");
            headers.add(HttpHeaders.PRAGMA, "no-cache");
            headers.add(HttpHeaders.EXPIRES, "0");

            logger.info("Successfully prepared report ID {} for download. Filename: {}", reportId, fileName);
            return ResponseEntity.ok()
                    .headers(headers)
                    .contentLength(reportBytes.length)
                    .contentType(MediaType.parseMediaType(contentType)) // e.g., "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" for Excel
                    .body(resource);

        } catch (ReportNotFoundException e) {
            logger.warn("Report with ID {} not found or not ready for download: {}", reportId, e.getMessage());
            // Return 404 Not Found if the report ID does not exist or is not in a downloadable state
            return new ResponseEntity<>(HttpStatus.NOT_FOUND);
        } catch (IllegalStateException e) {
            logger.warn("Report with ID {} is not yet ready for download: {}", reportId, e.getMessage());
            // Return 409 Conflict if the report is still being generated
            return new ResponseEntity<>(HttpStatus.CONFLICT);
        } catch (Exception e) {
            logger.error("An unexpected error occurred while downloading report ID {}: {}", reportId, e.getMessage(), e);
            // Return 500 Internal Server Error for unexpected issues
            return new ResponseEntity<>(HttpStatus.INTERNAL_SERVER_ERROR);
        }
    }
}

// --- Placeholder DTOs and Service Interface (would typically be in separate files) ---

// File: src/main/java/com/ltfs/cdp/reporting/dto/ReportGenerationRequest.java
package com.ltfs.cdp.reporting.dto;

import javax.validation.constraints.NotBlank;
import javax.validation.constraints.NotNull;
import java.util.Map;

public class ReportGenerationRequest {
    @NotBlank(message = "Report type cannot be empty")
    private String reportType; // e.g., "CUSTOMER_PROFILE_SUMMARY", "CAMPAIGN_PERFORMANCE"
    private Map<String, String> parameters; // e.g., {"startDate": "2023-01-01", "endDate": "2023-01-31", "campaignId": "C001"}

    public ReportGenerationRequest() {
    }

    public ReportGenerationRequest(String reportType, Map<String, String> parameters) {
        this.reportType = reportType;
        this.parameters = parameters;
    }

    public String getReportType() {
        return reportType;
    }

    public void setReportType(String reportType) {
        this.reportType = reportType;
    }

    public Map<String, String> getParameters() {
        return parameters;
    }

    public void setParameters(Map<String, String> parameters) {
        this.parameters = parameters;
    }

    @Override
    public String toString() {
        return "ReportGenerationRequest{" +
               "reportType='" + reportType + '\'' +
               ", parameters=" + parameters +
               '}';
    }
}

// File: src/main/java/com/ltfs/cdp/reporting/dto/ReportGenerationResponse.java
package com.ltfs.cdp.reporting.dto;

public class ReportGenerationResponse {
    private String reportId;
    private String status; // e.g., "INITIATED", "FAILED"
    private String message;

    public ReportGenerationResponse() {
    }

    public ReportGenerationResponse(String reportId, String status, String message) {
        this.reportId = reportId;
        this.status = status;
        this.message = message;
    }

    public String getReportId() {
        return reportId;
    }

    public void setReportId(String reportId) {
        this.reportId = reportId;
    }

    public String getStatus() {
        return status;
    }

    public void setStatus(String status) {
        this.status = status;
    }

    public String getMessage() {
        return message;
    }

    public void setMessage(String message) {
        this.message = message;
    }
}

// File: src/main/java/com/ltfs/cdp/reporting/dto/ReportStatusResponse.java
package com.ltfs.cdp.reporting.dto;

public class ReportStatusResponse {
    private String reportId;
    private String status; // e.g., "PENDING", "IN_PROGRESS", "COMPLETED", "FAILED"
    private String downloadUrl; // Only if status is COMPLETED
    private String errorMessage; // Only if status is FAILED

    public ReportStatusResponse() {
    }

    public ReportStatusResponse(String reportId, String status, String downloadUrl, String errorMessage) {
        this.reportId = reportId;
        this.status = status;
        this.downloadUrl = downloadUrl;
        this.errorMessage = errorMessage;
    }

    public String getReportId() {
        return reportId;
    }

    public void setReportId(String reportId) {
        this.reportId = reportId;
    }

    public String getStatus() {
        return status;
    }

    public void setStatus(String status) {
        this.status = status;
    }

    public String getDownloadUrl() {
        return downloadUrl;
    }

    public void setDownloadUrl(String downloadUrl) {
        this.downloadUrl = downloadUrl;
    }

    public String getErrorMessage() {
        return errorMessage;
    }

    public void setErrorMessage(String errorMessage) {
        this.errorMessage = errorMessage;
    }
}

// File: src/main/java/com/ltfs/cdp/reporting/exception/ReportGenerationException.java
package com.ltfs.cdp.reporting.exception;

public class ReportGenerationException extends RuntimeException {
    public ReportGenerationException(String message) {
        super(message);
    }

    public ReportGenerationException(String message, Throwable cause) {
        super(message, cause);
    }
}

// File: src/main/java/com/ltfs/cdp/reporting/exception/ReportNotFoundException.java
package com.ltfs.cdp.reporting.exception;

public class ReportNotFoundException extends RuntimeException {
    public ReportNotFoundException(String message) {
        super(message);
    }

    public ReportNotFoundException(String message, Throwable cause) {
        super(message, cause);
    }
}

// File: src/main/java/com/ltfs/cdp/reporting/service/ReportService.java
package com.ltfs.cdp.reporting.service;

import com.ltfs.cdp.reporting.dto.ReportGenerationRequest;
import com.ltfs.cdp.reporting.dto.ReportGenerationResponse;
import com.ltfs.cdp.reporting.dto.ReportStatusResponse;
import com.ltfs.cdp.reporting.exception.ReportGenerationException;
import com.ltfs.cdp.reporting.exception.ReportNotFoundException;
import org.springframework.stereotype.Service;

/**
 * Service interface for managing report generation and retrieval.
 * This interface defines the contract for report-related operations.
 */
public interface ReportService {

    /**
     * Initiates the generation of a report based on the provided request.
     * This method should handle the business logic for starting a report generation process,
     * which might be asynchronous.
     *
     * @param request The {@link ReportGenerationRequest} containing report details.
     * @return A {@link ReportGenerationResponse} with the unique ID of the initiated report
     *         and its initial status.
     * @throws ReportGenerationException If there's an issue preventing the report generation from starting.
     */
    ReportGenerationResponse initiateReportGeneration(ReportGenerationRequest request) throws ReportGenerationException;

    /**
     * Retrieves the current status of a specific report.
     *
     * @param reportId The unique identifier of the report.
     * @return A {@link ReportStatusResponse} indicating the report's status (e.g., PENDING, COMPLETED).
     * @throws ReportNotFoundException If no report with the given ID is found.
     */
    ReportStatusResponse getReportStatus(String reportId) throws ReportNotFoundException;

    /**
     * Downloads the content of a completed report.
     *
     * @param reportId The unique identifier of the report.
     * @return A byte array containing the report's data.
     * @throws ReportNotFoundException If the report is not found or not yet completed.
     * @throws IllegalStateException If the report is found but not in a downloadable state (e.g., still in progress).
     */
    byte[] downloadReport(String reportId) throws ReportNotFoundException, IllegalStateException;

    /**
     * Retrieves the suggested filename for a given report ID.
     *
     * @param reportId The unique identifier of the report.
     * @return The filename string.
     * @throws ReportNotFoundException If the report is not found.
     */
    String getReportFileName(String reportId) throws ReportNotFoundException;

    /**
     * Retrieves the content type (MIME type) for a given report ID.
     *
     * @param reportId The unique identifier of the report.
     * @return The content type string (e.g., "application/pdf", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet").
     * @throws ReportNotFoundException If the report is not found.
     */
    String getReportContentType(String reportId) throws ReportNotFoundException;
}

// File: src/main/java/com/ltfs/cdp/reporting/service/impl/ReportServiceImpl.java
package com.ltfs.cdp.reporting.service.impl;

import com.ltfs.cdp.reporting.dto.ReportGenerationRequest;
import com.ltfs.cdp.reporting.dto.ReportGenerationResponse;
import com.ltfs.cdp.reporting.dto.ReportStatusResponse;
import com.ltfs.cdp.reporting.exception.ReportGenerationException;
import com.ltfs.cdp.reporting.exception.ReportNotFoundException;
import com.ltfs.cdp.reporting.service.ReportService;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;

import java.util.HashMap;
import java.util.Map;
import java.util.UUID;
import java.util.concurrent.ConcurrentHashMap;

/**
 * Placeholder implementation of the {@link ReportService} interface.
 * In a real application, this service would interact with a database,
 * a message queue (for async processing), and a report generation engine.
 *
 * This mock implementation uses in-memory maps to simulate report states and data.
 */
@Service
public class ReportServiceImpl implements ReportService {

    private static final Logger logger = LoggerFactory.getLogger(ReportServiceImpl.class);

    // In-memory storage for report statuses and data (for demonstration purposes)
    private final Map<String, ReportStatusResponse> reportStatuses = new ConcurrentHashMap<>();
    private final Map<String, byte[]> reportData = new ConcurrentHashMap<>();
    private final Map<String, String> reportFileNames = new ConcurrentHashMap<>();
    private final Map<String, String> reportContentTypes = new ConcurrentHashMap<>();

    @Override
    public ReportGenerationResponse initiateReportGeneration(ReportGenerationRequest request) throws ReportGenerationException {
        // Simulate validation of report type and parameters
        if (request.getReportType() == null || request.getReportType().isEmpty()) {
            throw new ReportGenerationException("Report type must be specified.");
        }
        if (!isValidReportType(request.getReportType())) {
            throw new ReportGenerationException("Invalid report type: " + request.getReportType());
        }

        String reportId = UUID.randomUUID().toString();
        logger.info("Initiating report generation for type '{}' with ID '{}'", request.getReportType(), reportId);

        // Simulate asynchronous report generation
        // In a real scenario, this would publish an event to a message queue (e.g., Kafka)
        // or submit a task to an ExecutorService.
        ReportStatusResponse initialStatus = new ReportStatusResponse(reportId, "PENDING", null, null);
        reportStatuses.put(reportId, initialStatus);

        // Simulate a background task that eventually completes the report
        new Thread(() -> {
            try {
                Thread.sleep(5000); // Simulate work
                byte[] generatedBytes = generateMockReportContent(request.getReportType());
                String fileName = generateMockReportFileName(request.getReportType());
                String contentType = generateMockReportContentType(request.getReportType());

                reportData.put(reportId, generatedBytes);
                reportFileNames.put(reportId, fileName);
                reportContentTypes.put(reportId, contentType);

                ReportStatusResponse completedStatus = new ReportStatusResponse(reportId, "COMPLETED", "/api/v1/reports/" + reportId + "/download", null);
                reportStatuses.put(reportId, completedStatus);
                logger.info("Report ID '{}' generation completed successfully.", reportId);
            } catch (InterruptedException e) {
                Thread.currentThread().interrupt();
                ReportStatusResponse failedStatus = new ReportStatusResponse(reportId, "FAILED", null, "Report generation interrupted.");
                reportStatuses.put(reportId, failedStatus);
                logger.error("Report ID '{}' generation interrupted.", reportId, e);
            } catch (Exception e) {
                ReportStatusResponse failedStatus = new ReportStatusResponse(reportId, "FAILED", null, "Report generation failed: " + e.getMessage());
                reportStatuses.put(reportId, failedStatus);
                logger.error("Report ID '{}' generation failed.", reportId, e);
            }
        }).start();

        return new ReportGenerationResponse(reportId, "INITIATED", "Report generation started successfully.");
    }

    @Override
    public ReportStatusResponse getReportStatus(String reportId) throws ReportNotFoundException {
        ReportStatusResponse status = reportStatuses.get(reportId);
        if (status == null) {
            logger.warn("Attempted to get status for non-existent report ID: {}", reportId);
            throw new ReportNotFoundException("Report with ID " + reportId + " not found.");
        }
        return status;
    }

    @Override
    public byte[] downloadReport(String reportId) throws ReportNotFoundException, IllegalStateException {
        ReportStatusResponse status = getReportStatus(reportId); // Reuses status check logic
        if (!"COMPLETED".equals(status.getStatus())) {
            logger.warn("Attempted to download report ID {} which is not yet completed. Current status: {}", reportId, status.getStatus());
            throw new IllegalStateException("Report with ID " + reportId + " is not yet completed. Current status: " + status.getStatus());
        }

        byte[] bytes = reportData.get(reportId);
        if (bytes == null) {
            logger.error("Report data for ID {} is missing despite status being COMPLETED. Data inconsistency detected.", reportId);
            throw new ReportNotFoundException("Report data for ID " + reportId + " not found.");
        }
        logger.info("Providing download for report ID: {}", reportId);
        return bytes;
    }

    @Override
    public String getReportFileName(String reportId) throws ReportNotFoundException {
        String fileName = reportFileNames.get(reportId);
        if (fileName == null) {
            logger.warn("Filename not found for report ID: {}", reportId);
            throw new ReportNotFoundException("Filename for report ID " + reportId + " not found.");
        }
        return fileName;
    }

    @Override
    public String getReportContentType(String reportId) throws ReportNotFoundException {
        String contentType = reportContentTypes.get(reportId);
        if (contentType == null) {
            logger.warn("Content type not found for report ID: {}", reportId);
            throw new ReportNotFoundException("Content type for report ID " + reportId + " not found.");
        }
        return contentType;
    }

    /**
     * Helper method to validate report types.
     * In a real system, this would be based on configuration or a registry of available reports.
     */
    private boolean isValidReportType(String reportType) {
        return "CUSTOMER_PROFILE_SUMMARY".equals(reportType) ||
               "CAMPAIGN_PERFORMANCE".equals(reportType) ||
               "OFFER_DEDUPLICATION_SUMMARY".equals(reportType);
    }

    /**
     * Generates mock report content based on report type.
     */
    private byte[] generateMockReportContent(String reportType) {
        String content = "Mock Report Content for " + reportType + "\n" +
                         "Generated on: " + new java.util.Date() + "\n" +
                         "This is a placeholder for actual report data.";
        return content.getBytes();
    }

    /**
     * Generates a mock filename based on report type.
     */
    private String generateMockReportFileName(String reportType) {
        return reportType.toLowerCase().replace("_", "-") + "-" + System.currentTimeMillis() + ".txt";
    }

    /**
     * Generates a mock content type based on report type.
     */
    private String generateMockReportContentType(String reportType) {
        // In a real scenario, this would depend on the actual report format (e.g., Excel, PDF)
        return "text/plain";
    }
}
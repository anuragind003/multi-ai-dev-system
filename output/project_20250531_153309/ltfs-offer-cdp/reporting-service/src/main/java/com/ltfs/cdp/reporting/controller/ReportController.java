package com.ltfs.cdp.reporting.controller;

import com.ltfs.cdp.reporting.dto.ReportGenerationResponseDTO;
import com.ltfs.cdp.reporting.dto.ReportRequestDTO;
import com.ltfs.cdp.reporting.exception.ReportGenerationException;
import com.ltfs.cdp.reporting.exception.ReportNotFoundException;
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

import java.io.IOException;
import java.time.LocalDate;
import java.util.Arrays;
import java.util.List;
import java.util.Map;

/**
 * REST Controller for handling report generation and download requests.
 * This controller exposes endpoints for initiating report generation based on various criteria
 * and for downloading previously generated reports.
 */
@RestController
@RequestMapping("/api/reports")
public class ReportController {

    private static final Logger logger = LoggerFactory.getLogger(ReportController.class);

    private final ReportService reportService;

    /**
     * Constructs a new ReportController with the given ReportService.
     * Spring's dependency injection automatically provides the ReportService instance.
     *
     * @param reportService The service responsible for report generation and retrieval logic.
     */
    @Autowired
    public ReportController(ReportService reportService) {
        this.reportService = reportService;
    }

    /**
     * Initiates the generation of a new report based on the provided request parameters.
     * This endpoint is typically used for long-running report generation tasks,
     * returning an identifier that can be used to check the status or download the report later.
     *
     * @param reportRequestDTO A DTO containing parameters for report generation, such as report type,
     *                         date range, filters, etc.
     * @return A ResponseEntity containing a ReportGenerationResponseDTO with the report ID
     *         and status, or an error message if generation fails.
     */
    @PostMapping("/generate")
    public ResponseEntity<ReportGenerationResponseDTO> generateReport(@RequestBody ReportRequestDTO reportRequestDTO) {
        logger.info("Received request to generate report: {}", reportRequestDTO.getReportType());
        try {
            // Delegate the report generation logic to the service layer
            ReportGenerationResponseDTO response = reportService.generateReport(reportRequestDTO);
            logger.info("Report generation initiated successfully for type: {}. Report ID: {}",
                    reportRequestDTO.getReportType(), response.getReportId());
            return ResponseEntity.status(HttpStatus.ACCEPTED).body(response);
        } catch (ReportGenerationException e) {
            logger.error("Error during report generation for type {}: {}", reportRequestDTO.getReportType(), e.getMessage());
            // Return a bad request or internal server error depending on the nature of the exception
            return ResponseEntity.status(HttpStatus.BAD_REQUEST)
                    .body(new ReportGenerationResponseDTO(null, "Failed to generate report: " + e.getMessage(), "FAILED"));
        } catch (Exception e) {
            logger.error("An unexpected error occurred while generating report for type {}: {}", reportRequestDTO.getReportType(), e.getMessage(), e);
            return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR)
                    .body(new ReportGenerationResponseDTO(null, "An unexpected error occurred: " + e.getMessage(), "ERROR"));
        }
    }

    /**
     * Downloads a previously generated report by its unique identifier.
     * The report content is returned as a byte array resource, with appropriate
     * content type and disposition headers for file download.
     *
     * @param reportId The unique identifier of the report to be downloaded.
     * @return A ResponseEntity containing the report file as a Resource, or an error if the report is not found
     *         or an issue occurs during retrieval.
     */
    @GetMapping("/download/{reportId}")
    public ResponseEntity<Resource> downloadReport(@PathVariable String reportId) {
        logger.info("Received request to download report with ID: {}", reportId);
        try {
            // Retrieve the report file data and metadata from the service
            Map.Entry<byte[], String> reportData = reportService.getReportFile(reportId);
            byte[] fileContent = reportData.getKey();
            String fileName = reportData.getValue(); // e.g., "customer_report_20231026.csv"

            // Determine content type based on file extension or a predefined mapping
            MediaType contentType = getMediaTypeForFileName(fileName);

            // Create a ByteArrayResource from the file content
            ByteArrayResource resource = new ByteArrayResource(fileContent);

            // Set HTTP headers for file download
            HttpHeaders headers = new HttpHeaders();
            headers.add(HttpHeaders.CONTENT_DISPOSITION, "attachment; filename=\"" + fileName + "\"");
            headers.add(HttpHeaders.CONTENT_TYPE, contentType.toString());
            headers.add(HttpHeaders.CONTENT_LENGTH, String.valueOf(fileContent.length));

            logger.info("Successfully prepared report {} for download. Size: {} bytes", fileName, fileContent.length);
            return ResponseEntity.ok()
                    .headers(headers)
                    .contentType(contentType)
                    .body(resource);

        } catch (ReportNotFoundException e) {
            logger.warn("Report with ID {} not found: {}", reportId, e.getMessage());
            return ResponseEntity.status(HttpStatus.NOT_FOUND).body(null);
        } catch (IOException e) {
            logger.error("I/O error while retrieving report with ID {}: {}", reportId, e.getMessage(), e);
            return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR).body(null);
        } catch (Exception e) {
            logger.error("An unexpected error occurred while downloading report with ID {}: {}", reportId, e.getMessage(), e);
            return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR).body(null);
        }
    }

    /**
     * Provides a list of available report types that can be generated by the system.
     * This can be useful for front-end applications to dynamically populate report options.
     *
     * @return A ResponseEntity containing a list of strings, each representing an available report type.
     */
    @GetMapping("/types")
    public ResponseEntity<List<String>> getAvailableReportTypes() {
        logger.info("Received request for available report types.");
        try {
            List<String> reportTypes = reportService.getAvailableReportTypes();
            logger.debug("Available report types: {}", reportTypes);
            return ResponseEntity.ok(reportTypes);
        } catch (Exception e) {
            logger.error("Error retrieving available report types: {}", e.getMessage(), e);
            return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR).body(null);
        }
    }

    /**
     * Helper method to determine the MediaType based on the file extension.
     *
     * @param fileName The name of the file, including its extension.
     * @return The corresponding MediaType. Defaults to application/octet-stream if unknown.
     */
    private MediaType getMediaTypeForFileName(String fileName) {
        if (fileName == null || fileName.isEmpty()) {
            return MediaType.APPLICATION_OCTET_STREAM;
        }
        String fileExtension = "";
        int dotIndex = fileName.lastIndexOf('.');
        if (dotIndex > 0 && dotIndex < fileName.length() - 1) {
            fileExtension = fileName.substring(dotIndex + 1).toLowerCase();
        }

        return switch (fileExtension) {
            case "csv" -> new MediaType("text", "csv");
            case "xlsx" -> new MediaType("application", "vnd.openxmlformats-officedocument.spreadsheetml.sheet");
            case "xls" -> new MediaType("application", "vnd.ms-excel");
            case "pdf" -> MediaType.APPLICATION_PDF;
            case "json" -> MediaType.APPLICATION_JSON;
            default -> MediaType.APPLICATION_OCTET_STREAM; // Default for unknown types
        };
    }
}

// --- DTOs and Service Interface (Assumed to be in separate files/packages in a real project) ---
// For the purpose of providing a complete, runnable code snippet,
// these are included here. In a production setup, they would be in:
// com.ltfs.cdp.reporting.dto.ReportRequestDTO
// com.ltfs.cdp.reporting.dto.ReportGenerationResponseDTO
// com.ltfs.cdp.reporting.exception.ReportGenerationException
// com.ltfs.cdp.reporting.exception.ReportNotFoundException
// com.ltfs.cdp.reporting.service.ReportService

// Dummy DTOs and Service for compilation and demonstration purposes
// In a real project, these would be proper classes/records in their respective packages.

package com.ltfs.cdp.reporting.dto;

import java.time.LocalDate;
import java.util.Map;

/**
 * DTO for requesting report generation.
 */
class ReportRequestDTO {
    private String reportType;
    private LocalDate startDate;
    private LocalDate endDate;
    private Map<String, String> filters; // e.g., {"customerSegment": "Premium", "campaignId": "C001"}

    // Getters and Setters
    public String getReportType() { return reportType; }
    public void setReportType(String reportType) { this.reportType = reportType; }
    public LocalDate getStartDate() { return startDate; }
    public void setStartDate(LocalDate startDate) { this.startDate = startDate; }
    public LocalDate getEndDate() { return endDate; }
    public void setEndDate(LocalDate endDate) { this.endDate = endDate; }
    public Map<String, String> getFilters() { return filters; }
    public void setFilters(Map<String, String> filters) { this.filters = filters; }

    @Override
    public String toString() {
        return "ReportRequestDTO{" +
               "reportType='" + reportType + '\'' +
               ", startDate=" + startDate +
               ", endDate=" + endDate +
               ", filters=" + filters +
               '}';
    }
}

/**
 * DTO for responding to report generation requests.
 */
class ReportGenerationResponseDTO {
    private String reportId;
    private String message;
    private String status; // e.g., "PENDING", "COMPLETED", "FAILED"

    public ReportGenerationResponseDTO(String reportId, String message, String status) {
        this.reportId = reportId;
        this.message = message;
        this.status = status;
    }

    // Getters
    public String getReportId() { return reportId; }
    public String getMessage() { return message; }
    public String getStatus() { return status; }
}

package com.ltfs.cdp.reporting.exception;

/**
 * Custom exception for errors during report generation.
 */
class ReportGenerationException extends RuntimeException {
    public ReportGenerationException(String message) {
        super(message);
    }
    public ReportGenerationException(String message, Throwable cause) {
        super(message, cause);
    }
}

/**
 * Custom exception for when a requested report is not found.
 */
class ReportNotFoundException extends RuntimeException {
    public ReportNotFoundException(String message) {
        super(message);
    }
}

package com.ltfs.cdp.reporting.service;

import com.ltfs.cdp.reporting.dto.ReportGenerationResponseDTO;
import com.ltfs.cdp.reporting.dto.ReportRequestDTO;
import com.ltfs.cdp.reporting.exception.ReportGenerationException;
import com.ltfs.cdp.reporting.exception.ReportNotFoundException;
import org.springframework.stereotype.Service;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.time.LocalDate;
import java.time.format.DateTimeFormatter;
import java.util.Arrays;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import java.util.concurrent.ConcurrentHashMap;

/**
 * Service interface for report operations.
 * Defines the contract for report generation and retrieval.
 */
interface ReportService {
    ReportGenerationResponseDTO generateReport(ReportRequestDTO request) throws ReportGenerationException;
    Map.Entry<byte[], String> getReportFile(String reportId) throws ReportNotFoundException, IOException;
    List<String> getAvailableReportTypes();
}

/**
 * Dummy implementation of ReportService for demonstration.
 * In a real application, this would interact with a database,
 * a file storage system, or a dedicated report generation engine.
 */
@Service
class ReportServiceImpl implements ReportService {

    // In-memory store for generated reports (for demonstration purposes only)
    private final Map<String, byte[]> generatedReports = new ConcurrentHashMap<>();
    private final Map<String, String> reportFileNames = new ConcurrentHashMap<>(); // reportId -> fileName

    @Override
    public ReportGenerationResponseDTO generateReport(ReportRequestDTO request) throws ReportGenerationException {
        // Simulate report generation time
        try {
            Thread.sleep(1000); // Simulate work
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
            throw new ReportGenerationException("Report generation interrupted", e);
        }

        String reportId = UUID.randomUUID().toString();
        String reportType = request.getReportType();
        LocalDate startDate = request.getStartDate();
        LocalDate endDate = request.getEndDate();
        Map<String, String> filters = request.getFilters();

        String content;
        String fileName;

        switch (reportType.toLowerCase()) {
            case "customer_profile":
                content = "Customer ID,Name,Email,Phone,Loan Product,Offer Status\n" +
                          "C001,John Doe,john.doe@example.com,1234567890,Home Loan,Approved\n" +
                          "C002,Jane Smith,jane.smith@example.com,0987654321,Personal Loan,Pending";
                fileName = "customer_profile_report_" + LocalDate.now().format(DateTimeFormatter.BASIC_ISO_DATE) + ".csv";
                break;
            case "campaign_performance":
                content = "Campaign ID,Campaign Name,Offers Sent,Offers Accepted,Conversion Rate\n" +
                          "CMP001,Summer Loan Offer,10000,500,5%\n" +
                          "CMP002,Top-up Loan Promo,5000,150,3%";
                fileName = "campaign_performance_report_" + LocalDate.now().format(DateTimeFormatter.BASIC_ISO_DATE) + ".csv";
                break;
            case "offer_deduplication_summary":
                content = "Date,Total Offers,Deduped Offers,Unique Offers\n" +
                          "2023-10-25,15000,2000,13000\n" +
                          "2023-10-26,16000,2500,13500";
                fileName = "offer_deduplication_summary_" + LocalDate.now().format(DateTimeFormatter.BASIC_ISO_DATE) + ".csv";
                break;
            default:
                throw new ReportGenerationException("Unsupported report type: " + reportType);
        }

        generatedReports.put(reportId, content.getBytes(StandardCharsets.UTF_8));
        reportFileNames.put(reportId, fileName);

        return new ReportGenerationResponseDTO(reportId, "Report generation initiated successfully.", "PENDING");
    }

    @Override
    public Map.Entry<byte[], String> getReportFile(String reportId) throws ReportNotFoundException, IOException {
        byte[] fileContent = generatedReports.get(reportId);
        String fileName = reportFileNames.get(reportId);

        if (fileContent == null || fileName == null) {
            throw new ReportNotFoundException("Report with ID " + reportId + " not found or not yet generated.");
        }

        // Simulate reading from a file system or database
        // In a real scenario, this might involve fetching from S3, Blob Storage, or a file server
        return new HashMap.SimpleEntry<>(fileContent, fileName);
    }

    @Override
    public List<String> getAvailableReportTypes() {
        return Arrays.asList(
                "Customer_Profile",
                "Campaign_Performance",
                "Offer_Deduplication_Summary"
        );
    }
}
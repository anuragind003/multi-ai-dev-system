package com.ltfs.cdp.adminportal.controller;

import com.ltfs.cdp.adminportal.service.FileUploadService;
import com.ltfs.cdp.adminportal.service.LeadGenerationService;
import com.ltfs.cdp.adminportal.service.ProcessingLogService;
import com.ltfs.cdp.adminportal.model.ProcessingJobStatus;
import com.ltfs.cdp.adminportal.exception.FileProcessingException;
import com.ltfs.cdp.adminportal.exception.ResourceNotFoundException;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.multipart.MultipartFile;

import java.io.IOException;
import java.util.List;
import java.util.Map;
import java.util.UUID; // Used for generating mock job IDs
import java.time.LocalDateTime; // Used for mock timestamps
import java.util.HashMap; // Used for mock in-memory storage
import java.util.ArrayList; // Used for mock list return

/**
 * REST Controller for handling administrative tasks within the LTFS Offer CDP Admin Portal.
 * This includes functionalities like file uploads for customer and offer data,
 * triggering lead generation processes, and accessing processing logs.
 */
@RestController
@RequestMapping("/api/admin") // Base path for all admin-related API endpoints
public class AdminController {

    private final FileUploadService fileUploadService;
    private final LeadGenerationService leadGenerationService;
    private final ProcessingLogService processingLogService;

    /**
     * Constructor for dependency injection. Spring automatically injects the required service beans.
     *
     * @param fileUploadService     Service responsible for handling file upload operations.
     * @param leadGenerationService Service responsible for initiating lead generation processes.
     * @param processingLogService  Service responsible for retrieving processing job statuses and logs.
     */
    @Autowired
    public AdminController(FileUploadService fileUploadService,
                           LeadGenerationService leadGenerationService,
                           ProcessingLogService processingLogService) {
        this.fileUploadService = fileUploadService;
        this.leadGenerationService = leadGenerationService;
        this.processingLogService = processingLogService;
    }

    /**
     * Handles the upload of customer data files.
     * This endpoint accepts a multipart file, typically a CSV or Excel, containing customer information.
     * The file processing is delegated to the {@code FileUploadService}, which should handle
     * saving the file, parsing its content, and initiating asynchronous data ingestion.
     *
     * @param file The {@link MultipartFile} containing customer data. Expected to be sent as 'file' in form-data.
     * @return A {@link ResponseEntity} indicating the status of the upload.
     *         Returns HTTP 202 (Accepted) with a job ID if the upload is successfully initiated.
     *         Returns HTTP 400 (Bad Request) if no file is provided or if there's a file processing error.
     *         Returns HTTP 500 (Internal Server Error) for unexpected server-side issues.
     */
    @PostMapping("/upload/customer-data")
    public ResponseEntity<Map<String, String>> uploadCustomerData(@RequestParam("file") MultipartFile file) {
        if (file.isEmpty()) {
            return new ResponseEntity<>(Map.of("message", "Please select a file to upload."), HttpStatus.BAD_REQUEST);
        }
        try {
            // Delegate the file upload and initial processing to the service layer.
            // The service is expected to return a unique job ID for tracking the asynchronous process.
            String jobId = fileUploadService.uploadCustomerDataFile(file);
            return new ResponseEntity<>(Map.of("message", "Customer data upload initiated successfully.", "jobId", jobId), HttpStatus.ACCEPTED);
        } catch (IOException e) {
            // Catches errors related to file I/O operations (e.g., reading the file stream).
            return new ResponseEntity<>(Map.of("message", "Failed to upload file due to I/O error: " + e.getMessage()), HttpStatus.INTERNAL_SERVER_ERROR);
        } catch (FileProcessingException e) {
            // Catches custom exceptions indicating issues with the file content or format.
            return new ResponseEntity<>(Map.of("message", "File processing error: " + e.getMessage()), HttpStatus.BAD_REQUEST);
        } catch (Exception e) {
            // Catches any other unexpected runtime exceptions.
            return new ResponseEntity<>(Map.of("message", "An unexpected error occurred during customer data upload: " + e.getMessage()), HttpStatus.INTERNAL_SERVER_ERROR);
        }
    }

    /**
     * Handles the upload of offer data files.
     * Similar to customer data upload, this endpoint processes files containing offer-specific information.
     *
     * @param file The {@link MultipartFile} containing offer data. Expected to be sent as 'file' in form-data.
     * @return A {@link ResponseEntity} indicating the status of the upload.
     *         Returns HTTP 202 (Accepted) with a job ID if the upload is successfully initiated.
     *         Returns HTTP 400 (Bad Request) if no file is provided or if there's a file processing error.
     *         Returns HTTP 500 (Internal Server Error) for unexpected server-side issues.
     */
    @PostMapping("/upload/offer-data")
    public ResponseEntity<Map<String, String>> uploadOfferData(@RequestParam("file") MultipartFile file) {
        if (file.isEmpty()) {
            return new ResponseEntity<>(Map.of("message", "Please select a file to upload."), HttpStatus.BAD_REQUEST);
        }
        try {
            // Delegate the file upload and initial processing to the service layer.
            String jobId = fileUploadService.uploadOfferDataFile(file);
            return new ResponseEntity<>(Map.of("message", "Offer data upload initiated successfully.", "jobId", jobId), HttpStatus.ACCEPTED);
        } catch (IOException e) {
            return new ResponseEntity<>(Map.of("message", "Failed to upload file due to I/O error: " + e.getMessage()), HttpStatus.INTERNAL_SERVER_ERROR);
        } catch (FileProcessingException e) {
            return new ResponseEntity<>(Map.of("message", "File processing error: " + e.getMessage()), HttpStatus.BAD_REQUEST);
        } catch (Exception e) {
            return new ResponseEntity<>(Map.of("message", "An unexpected error occurred during offer data upload: " + e.getMessage()), HttpStatus.INTERNAL_SERVER_ERROR);
        }
    }

    /**
     * Triggers the lead generation process.
     * This endpoint initiates a backend process to generate new leads based on predefined rules
     * and existing customer/offer data. The actual generation logic resides in the service layer.
     *
     * @return A {@link ResponseEntity} indicating the status of the lead generation initiation.
     *         Returns HTTP 202 (Accepted) with a job ID if the process is successfully initiated.
     *         Returns HTTP 500 (Internal Server Error) for any failure during initiation.
     */
    @PostMapping("/generate-leads")
    public ResponseEntity<Map<String, String>> generateLeads() {
        try {
            // Delegate the lead generation initiation to the service layer.
            // This process is typically asynchronous and returns a job ID.
            String jobId = leadGenerationService.initiateLeadGeneration();
            return new ResponseEntity<>(Map.of("message", "Lead generation process initiated successfully.", "jobId", jobId), HttpStatus.ACCEPTED);
        } catch (Exception e) {
            // Catches any unexpected exceptions during the initiation of lead generation.
            return new ResponseEntity<>(Map.of("message", "Failed to initiate lead generation: " + e.getMessage()), HttpStatus.INTERNAL_SERVER_ERROR);
        }
    }

    /**
     * Retrieves a list of all available processing job statuses.
     * This endpoint provides an overview of all data ingestion, deduplication, and lead generation
     * jobs that have been executed or are currently in progress.
     *
     * @return A {@link ResponseEntity} containing a list of {@link ProcessingJobStatus} objects.
     *         Returns HTTP 200 (OK) with the list of job statuses.
     *         Returns HTTP 500 (Internal Server Error) if there's an issue retrieving the logs.
     */
    @GetMapping("/processing-logs")
    public ResponseEntity<List<ProcessingJobStatus>> getAllProcessingLogs() {
        try {
            List<ProcessingJobStatus> logs = processingLogService.getAllJobStatuses();
            return new ResponseEntity<>(logs, HttpStatus.OK);
        } catch (Exception e) {
            // Catches any unexpected exceptions during log retrieval.
            // In a production system, this might return a more structured error response.
            System.err.println("Error retrieving all processing logs: " + e.getMessage());
            return new ResponseEntity<>(HttpStatus.INTERNAL_SERVER_ERROR);
        }
    }

    /**
     * Retrieves the detailed status of a specific processing job by its unique ID.
     * This allows administrators to monitor the progress and outcome of individual tasks.
     *
     * @param jobId The unique identifier (UUID or similar string) of the processing job.
     * @return A {@link ResponseEntity} containing the {@link ProcessingJobStatus} object for the specified job.
     *         Returns HTTP 200 (OK) if the job status is found.
     *         Returns HTTP 404 (Not Found) if no job with the given ID exists.
     *         Returns HTTP 500 (Internal Server Error) for any other unexpected issues.
     */
    @GetMapping("/processing-logs/{jobId}")
    public ResponseEntity<ProcessingJobStatus> getProcessingLogById(@PathVariable String jobId) {
        try {
            ProcessingJobStatus status = processingLogService.getJobStatusById(jobId);
            return new ResponseEntity<>(status, HttpStatus.OK);
        } catch (ResourceNotFoundException e) {
            // Catches custom exception when the requested job ID does not exist.
            return new ResponseEntity<>(HttpStatus.NOT_FOUND);
        } catch (Exception e) {
            // Catches any other unexpected exceptions during retrieval.
            System.err.println("Error retrieving processing log for job ID " + jobId + ": " + e.getMessage());
            return new ResponseEntity<>(HttpStatus.INTERNAL_SERVER_ERROR);
        }
    }
}

// --- Placeholder Service Interfaces and Models for direct runnability ---
// In a real-world project, these would reside in separate files within their respective packages.

/**
 * Service interface for handling file upload operations.
 */
interface FileUploadService {
    /**
     * Uploads and initiates processing for a customer data file.
     * @param file The multipart file containing customer data.
     * @return A unique job ID for tracking the processing.
     * @throws IOException If an I/O error occurs during file handling.
     * @throws FileProcessingException If the file content or format is invalid.
     */
    String uploadCustomerDataFile(MultipartFile file) throws IOException, FileProcessingException;

    /**
     * Uploads and initiates processing for an offer data file.
     * @param file The multipart file containing offer data.
     * @return A unique job ID for tracking the processing.
     * @throws IOException If an I/O error occurs during file handling.
     * @throws FileProcessingException If the file content or format is invalid.
     */
    String uploadOfferDataFile(MultipartFile file) throws IOException, FileProcessingException;
}

/**
 * Service interface for handling lead generation processes.
 */
interface LeadGenerationService {
    /**
     * Initiates the lead generation process.
     * @return A unique job ID for tracking the lead generation process.
     */
    String initiateLeadGeneration();
}

/**
 * Service interface for accessing processing job logs and statuses.
 */
interface ProcessingLogService {
    /**
     * Retrieves a list of all processing job statuses.
     * @return A list of {@link ProcessingJobStatus} objects.
     */
    List<ProcessingJobStatus> getAllJobStatuses();

    /**
     * Retrieves the status of a specific processing job by its ID.
     * @param jobId The ID of the job to retrieve.
     * @return The {@link ProcessingJobStatus} object for the given ID.
     * @throws ResourceNotFoundException If no job with the specified ID is found.
     */
    ProcessingJobStatus getJobStatusById(String jobId) throws ResourceNotFoundException;
}

/**
 * Model representing the status of a processing job.
 */
class ProcessingJobStatus {
    private String jobId;
    private String type; // e.g., "CUSTOMER_DATA_UPLOAD", "OFFER_DATA_UPLOAD", "LEAD_GENERATION"
    private String status; // e.g., "PENDING", "IN_PROGRESS", "COMPLETED", "FAILED"
    private String startTime; // ISO 8601 timestamp
    private String endTime;   // ISO 8601 timestamp (null if in progress)
    private String message;   // Detailed message or error description

    /**
     * Constructs a new ProcessingJobStatus.
     * @param jobId Unique identifier for the job.
     * @param type Type of the processing job.
     * @param status Current status of the job.
     * @param startTime Timestamp when the job started.
     * @param endTime Timestamp when the job ended (can be null if in progress).
     * @param message A descriptive message about the job's status or outcome.
     */
    public ProcessingJobStatus(String jobId, String type, String status, String startTime, String endTime, String message) {
        this.jobId = jobId;
        this.type = type;
        this.status = status;
        this.startTime = startTime;
        this.endTime = endTime;
        this.message = message;
    }

    // Getters for all fields
    public String getJobId() { return jobId; }
    public String getType() { return type; }
    public String getStatus() { return status; }
    public String getStartTime() { return startTime; }
    public String getEndTime() { return endTime; }
    public String getMessage() { return message; }

    // Setters (optional, depending on mutability requirements)
    public void setJobId(String jobId) { this.jobId = jobId; }
    public void setType(String type) { this.type = type; }
    public void setStatus(String status) { this.status = status; }
    public void setStartTime(String startTime) { this.startTime = startTime; }
    public void setEndTime(String endTime) { this.endTime = endTime; }
    public void setMessage(String message) { this.message = message; }

    @Override
    public String toString() {
        return "ProcessingJobStatus{" +
               "jobId='" + jobId + '\'' +
               ", type='" + type + '\'' +
               ", status='" + status + '\'' +
               ", startTime='" + startTime + '\'' +
               ", endTime='" + endTime + '\'' +
               ", message='" + message + '\'' +
               '}';
    }
}

/**
 * Custom exception for errors encountered during file processing (e.g., invalid format, content issues).
 */
class FileProcessingException extends RuntimeException {
    public FileProcessingException(String message) {
        super(message);
    }
    public FileProcessingException(String message, Throwable cause) {
        super(message, cause);
    }
}

/**
 * Custom exception for when a requested resource (e.g., a processing job) is not found.
 */
class ResourceNotFoundException extends RuntimeException {
    public ResourceNotFoundException(String message) {
        super(message);
    }
}

// --- Simple Mock Implementations for Services (for direct runnability) ---
// In a real project, these would be in separate files within an 'impl' package.

/**
 * Mock implementation of {@link FileUploadService} for demonstration purposes.
 * Simulates file upload and returns a mock job ID.
 */
@org.springframework.stereotype.Service // Marks this class as a Spring service component
class FileUploadServiceImpl implements FileUploadService {
    @Override
    public String uploadCustomerDataFile(MultipartFile file) throws IOException, FileProcessingException {
        // Simulate file validation and processing logic
        if (file.getOriginalFilename() != null && file.getOriginalFilename().toLowerCase().contains("invalid")) {
            throw new FileProcessingException("Simulated error: Invalid customer data file content or format.");
        }
        System.out.println("Mock: Uploading customer data file: " + file.getOriginalFilename() + " (" + file.getSize() + " bytes)");
        // In a real scenario, this would save the file and trigger an asynchronous processing job.
        String jobId = "CUST-" + UUID.randomUUID().toString().substring(0, 8).toUpperCase();
        // Add a mock status for this job
        ((ProcessingLogServiceImpl) SpringContext.getBean(ProcessingLogService.class)).addJobStatus(
            new ProcessingJobStatus(jobId, "CUSTOMER_DATA_UPLOAD", "IN_PROGRESS", LocalDateTime.now().toString(), null, "File received, processing started.")
        );
        return jobId;
    }

    @Override
    public String uploadOfferDataFile(MultipartFile file) throws IOException, FileProcessingException {
        System.out.println("Mock: Uploading offer data file: " + file.getOriginalFilename() + " (" + file.getSize() + " bytes)");
        String jobId = "OFFER-" + UUID.randomUUID().toString().substring(0, 8).toUpperCase();
        ((ProcessingLogServiceImpl) SpringContext.getBean(ProcessingLogService.class)).addJobStatus(
            new ProcessingJobStatus(jobId, "OFFER_DATA_UPLOAD", "IN_PROGRESS", LocalDateTime.now().toString(), null, "File received, processing started.")
        );
        return jobId;
    }
}

/**
 * Mock implementation of {@link LeadGenerationService} for demonstration purposes.
 * Simulates initiating a lead generation process.
 */
@org.springframework.stereotype.Service
class LeadGenerationServiceImpl implements LeadGenerationService {
    @Override
    public String initiateLeadGeneration() {
        System.out.println("Mock: Initiating lead generation process.");
        String jobId = "LEAD-" + UUID.randomUUID().toString().substring(0, 8).toUpperCase();
        ((ProcessingLogServiceImpl) SpringContext.getBean(ProcessingLogService.class)).addJobStatus(
            new ProcessingJobStatus(jobId, "LEAD_GENERATION", "PENDING", LocalDateTime.now().toString(), null, "Lead generation process queued.")
        );
        return jobId;
    }
}

/**
 * Mock implementation of {@link ProcessingLogService} using an in-memory map.
 * Provides dummy data and basic retrieval functionality.
 */
@org.springframework.stereotype.Service
class ProcessingLogServiceImpl implements ProcessingLogService {
    private final Map<String, ProcessingJobStatus> jobStatuses = new HashMap<>();

    public ProcessingLogServiceImpl() {
        // Populate with some initial dummy data for demonstration
        String now = LocalDateTime.now().toString();
        jobStatuses.put("CUST-MOCK1", new ProcessingJobStatus("CUST-MOCK1", "CUSTOMER_DATA_UPLOAD", "COMPLETED", now, now, "Successfully processed 1000 customer records."));
        jobStatuses.put("OFFER-MOCK2", new ProcessingJobStatus("OFFER-MOCK2", "OFFER_DATA_UPLOAD", "IN_PROGRESS", now, null, "Processing batch 1 of 5 for offers."));
        jobStatuses.put("LEAD-MOCK3", new ProcessingJobStatus("LEAD-MOCK3", "LEAD_GENERATION", "FAILED", now, now, "Failed due to data inconsistency in source."));
    }

    /**
     * Adds or updates a job status in the mock store.
     * This method is used by other mock services to simulate job status updates.
     * @param status The {@link ProcessingJobStatus} to add or update.
     */
    public void addJobStatus(ProcessingJobStatus status) {
        jobStatuses.put(status.getJobId(), status);
    }

    @Override
    public List<ProcessingJobStatus> getAllJobStatuses() {
        return new ArrayList<>(jobStatuses.values());
    }

    @Override
    public ProcessingJobStatus getJobStatusById(String jobId) throws ResourceNotFoundException {
        ProcessingJobStatus status = jobStatuses.get(jobId);
        if (status == null) {
            throw new ResourceNotFoundException("Processing job with ID " + jobId + " not found.");
        }
        return status;
    }
}

// --- Spring Context Holder for accessing beans in mock services ---
// This is a workaround for direct runnability without a full Spring Boot application setup.
// In a real application, services would be injected directly.
class SpringContext implements org.springframework.context.ApplicationContextAware {
    private static org.springframework.context.ApplicationContext context;

    @Override
    public void setApplicationContext(org.springframework.context.ApplicationContext applicationContext) throws org.springframework.beans.BeansException {
        context = applicationContext;
    }

    public static <T> T getBean(Class<T> beanClass) {
        return context.getBean(beanClass);
    }
}
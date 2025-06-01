package com.ltfs.cdp.admin.file;

import com.ltfs.cdp.admin.exception.FileProcessingException;
import com.ltfs.cdp.admin.service.CustomerDataUploadService;
import com.ltfs.cdp.admin.service.CampaignDataUploadService;
import com.ltfs.cdp.admin.service.OfferDataUploadService;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import org.springframework.web.multipart.MultipartFile;

import java.io.IOException;

/**
 * Enum to define supported file types for upload in the Admin Portal.
 * This helps in routing the uploaded file to the correct processing service.
 */
enum UploadFileType {
    CUSTOMER_DATA,
    CAMPAIGN_DATA,
    OFFER_DATA,
    UNKNOWN;

    /**
     * Converts a string representation to an UploadFileType enum.
     * Case-insensitive. Returns UNKNOWN if the string does not match any defined type.
     * @param type The string representation of the file type.
     * @return The corresponding UploadFileType enum.
     */
    public static UploadFileType fromString(String type) {
        if (type == null || type.trim().isEmpty()) {
            return UNKNOWN;
        }
        try {
            return UploadFileType.valueOf(type.toUpperCase());
        } catch (IllegalArgumentException e) {
            return UNKNOWN;
        }
    }
}

/**
 * Represents the result of a file processing operation.
 * Provides information about the success status, a message, and optional details.
 */
class ProcessingResult {
    private boolean success;
    private String message;
    private String details; // e.g., number of records processed, errors encountered

    /**
     * Constructs a new ProcessingResult.
     * @param success True if the operation was successful, false otherwise.
     * @param message A descriptive message about the outcome.
     */
    public ProcessingResult(boolean success, String message) {
        this.success = success;
        this.message = message;
    }

    /**
     * Constructs a new ProcessingResult with additional details.
     * @param success True if the operation was successful, false otherwise.
     * @param message A descriptive message about the outcome.
     * @param details Additional specific details about the processing (e.g., record counts, error summaries).
     */
    public ProcessingResult(boolean success, String message, String details) {
        this.success = success;
        this.message = message;
        this.details = details;
    }

    // Getters
    public boolean isSuccess() {
        return success;
    }

    public String getMessage() {
        return message;
    }

    public String getDetails() {
        return details;
    }

    // Setters (optional, but can be useful for mutable results or builder patterns)
    public void setSuccess(boolean success) {
        this.success = success;
    }

    public void setMessage(String message) {
        this.message = message;
    }

    public void setDetails(String details) {
        this.details = details;
    }
}

/**
 * Service class responsible for orchestrating the processing of uploaded files.
 * It delegates the actual data parsing, validation, and persistence to specific
 * data upload services based on the identified file type.
 *
 * This processor acts as a central point for file upload operations within the
 * admin portal, ensuring proper routing and error handling.
 */
@Service
public class FileUploadProcessor {

    private static final Logger logger = LoggerFactory.getLogger(FileUploadProcessor.class);

    private final CustomerDataUploadService customerDataUploadService;
    private final CampaignDataUploadService campaignDataUploadService;
    private final OfferDataUploadService offerDataUploadService;

    /**
     * Constructs a FileUploadProcessor with necessary data upload services injected by Spring.
     * These services are responsible for the specific business logic related to each file type.
     *
     * @param customerDataUploadService Service for processing customer data files.
     * @param campaignDataUploadService Service for processing campaign data files.
     * @param offerDataUploadService Service for processing offer data files.
     */
    @Autowired
    public FileUploadProcessor(CustomerDataUploadService customerDataUploadService,
                               CampaignDataUploadService campaignDataUploadService,
                               OfferDataUploadService offerDataUploadService) {
        this.customerDataUploadService = customerDataUploadService;
        this.campaignDataUploadService = campaignDataUploadService;
        this.offerDataUploadService = offerDataUploadService;
    }

    /**
     * Processes an uploaded file based on its designated type.
     * This method performs initial checks (e.g., file emptiness, known file type)
     * and then dispatches the file's input stream to the appropriate specialized
     * service for detailed processing (parsing, validation, deduplication, persistence).
     *
     * @param file The {@link MultipartFile} representing the uploaded file.
     * @param fileType The {@link UploadFileType} indicating the type of data contained in the file.
     * @return A {@link ProcessingResult} object indicating the success or failure of the operation,
     *         along with a message and optional details.
     * @throws FileProcessingException if an unrecoverable I/O error occurs while reading the file
     *                                 or if an unexpected error occurs during delegated processing.
     */
    public ProcessingResult processFile(MultipartFile file, UploadFileType fileType) throws FileProcessingException {
        // Validate input file: check for null or empty file content.
        if (file == null || file.isEmpty()) {
            logger.warn("Attempted to process an empty or null file for type: {}", fileType);
            return new ProcessingResult(false, "Uploaded file is empty or invalid. Please upload a non-empty file.");
        }

        // Validate file type: ensure a known type is provided for processing.
        if (fileType == UploadFileType.UNKNOWN) {
            logger.error("Attempted to process file with unknown type. Original filename: {}", file.getOriginalFilename());
            return new ProcessingResult(false, "Unknown file type specified for processing. Please provide a valid type (e.g., CUSTOMER_DATA, CAMPAIGN_DATA, OFFER_DATA).");
        }

        logger.info("Starting processing for file: '{}' (Type: {}, Size: {} bytes)",
                file.getOriginalFilename(), fileType, file.getSize());

        try {
            // Delegate processing based on the identified file type.
            // Each specific service is responsible for its own parsing, validation,
            // deduplication (as per project context), and persistence logic.
            switch (fileType) {
                case CUSTOMER_DATA:
                    // Process customer-related data, including deduplication against Customer 360.
                    return customerDataUploadService.processCustomerFile(file.getInputStream(), file.getOriginalFilename());
                case CAMPAIGN_DATA:
                    // Process campaign-related data.
                    return campaignDataUploadService.processCampaignFile(file.getInputStream(), file.getOriginalFilename());
                case OFFER_DATA:
                    // Process offer-related data, including top-up offer specific deduplication.
                    return offerDataUploadService.processOfferFile(file.getInputStream(), file.getOriginalFilename());
                default:
                    // This 'default' case acts as a safeguard. If 'UNKNOWN' is handled above,
                    // this block should ideally not be reached unless a new enum type is added
                    // without a corresponding processing logic.
                    logger.error("No specific processor found for file type: {}. This indicates a potential configuration or logic error.", fileType);
                    return new ProcessingResult(false, "Internal server error: No specific processor found for the given file type. Please contact support.");
            }
        } catch (IOException e) {
            // Catch I/O errors that occur when trying to read the content of the uploaded file.
            logger.error("I/O error while reading uploaded file '{}': {}", file.getOriginalFilename(), e.getMessage(), e);
            throw new FileProcessingException("Failed to read uploaded file '" + file.getOriginalFilename() + "'. Please ensure the file is accessible and try again.", e);
        } catch (Exception e) {
            // Catch any other unexpected exceptions that might originate from the delegated services
            // during their complex processing (e.g., parsing errors, validation failures, database errors,
            // or issues during deduplication logic).
            logger.error("An unexpected error occurred during file processing for '{}' (Type: {}): {}",
                    file.getOriginalFilename(), fileType, e.getMessage(), e);
            throw new FileProcessingException("An unexpected error occurred during file processing: " + e.getMessage() + ". Please check the file content or contact support.", e);
        }
    }
}
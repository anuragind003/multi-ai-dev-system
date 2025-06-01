package com.ltfs.cdp.adminportal.service;

import com.ltfs.cdp.adminportal.exception.FileProcessingException;
import com.ltfs.cdp.adminportal.model.CustomerDetailUploadDTO;
import org.apache.commons.csv.CSVFormat;
import org.apache.commons.csv.CSVParser;
import org.apache.commons.csv.CSVRecord;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.kafka.core.KafkaTemplate;
import org.springframework.stereotype.Service;
import org.springframework.web.multipart.MultipartFile;

import java.io.BufferedReader;
import java.io.IOException;
import java.io.InputStreamReader;
import java.util.ArrayList;
import java.util.List;
import java.util.Objects;
import java.util.UUID;

/**
 * Service class responsible for processing uploaded customer detail files.
 * This processor handles file validation, parsing of CSV content, and
 * publishing the extracted customer data to a Kafka topic for asynchronous
 * processing by downstream services (e.g., Data Validation Service, Integration Service).
 */
@Service
public class FileUploadProcessor {

    private static final Logger log = LoggerFactory.getLogger(FileUploadProcessor.class);

    private final KafkaTemplate<String, List<CustomerDetailUploadDTO>> kafkaTemplate;
    private final String customerUploadTopic;

    /**
     * Constructor for FileUploadProcessor, injecting necessary dependencies.
     *
     * @param kafkaTemplate The Spring KafkaTemplate configured to send messages.
     *                      It is parameterized to send a list of CustomerDetailUploadDTOs.
     * @param customerUploadTopic The Kafka topic name for customer uploads,
     *                            injected from application properties (e.g., `kafka.topic.customer-upload`).
     */
    public FileUploadProcessor(KafkaTemplate<String, List<CustomerDetailUploadDTO>> kafkaTemplate,
                               @Value("${kafka.topic.customer-upload}") String customerUploadTopic) {
        this.kafkaTemplate = kafkaTemplate;
        this.customerUploadTopic = customerUploadTopic;
    }

    /**
     * Processes an uploaded customer detail file.
     * This method performs the following steps:
     * 1. Basic validation of the uploaded file (e.g., not empty, correct content type).
     * 2. Reads the CSV content from the file.
     * 3. Parses each record into a {@link CustomerDetailUploadDTO}.
     * 4. Publishes the list of parsed DTOs to a configured Kafka topic.
     *
     * @param file The {@link MultipartFile} representing the uploaded customer detail file.
     * @return A unique batch ID generated for this file upload, which can be used for tracking.
     * @throws FileProcessingException If any error occurs during file validation, reading, parsing,
     *                                 or publishing to Kafka.
     *
     * Dependencies:
     * - {@link com.ltfs.cdp.adminportal.exception.FileProcessingException}: Custom exception for file processing errors.
     * - {@link com.ltfs.cdp.adminportal.model.CustomerDetailUploadDTO}: Data Transfer Object representing a customer record.
     * - Apache Commons CSV library (org.apache.commons:commons-csv) for CSV parsing.
     * - Spring Kafka (org.springframework.kafka:spring-kafka) for message publishing.
     */
    public String processCustomerDetailFile(MultipartFile file) throws FileProcessingException {
        // 1. Perform basic file validation
        if (file.isEmpty()) {
            log.error("Uploaded file is empty.");
            throw new FileProcessingException("Uploaded file cannot be empty.");
        }

        // Validate file content type. Assuming customer detail files are CSV.
        if (!Objects.equals(file.getContentType(), "text/csv")) {
            log.error("Invalid file type: {}. Only CSV files are allowed for customer detail uploads.", file.getContentType());
            throw new FileProcessingException("Invalid file type. Only CSV files are allowed.");
        }

        // Generate a unique batch ID for this file upload for tracking purposes.
        String batchId = UUID.randomUUID().toString();
        log.info("Starting processing for file: '{}' (size: {} bytes) with batchId: {}",
                file.getOriginalFilename(), file.getSize(), batchId);

        List<CustomerDetailUploadDTO> customerDetails = new ArrayList<>();

        // 2. Read and parse the CSV file content
        try (BufferedReader fileReader = new BufferedReader(new InputStreamReader(file.getInputStream()))) {
            // Configure CSV parser:
            // - DEFAULT: Standard CSV format.
            // - withFirstRecordAsHeader(): Treats the first row as headers.
            // - withIgnoreHeaderCase(): Ignores case when matching headers.
            // - withTrim(): Trims whitespace from values.
            CSVParser csvParser = new CSVParser(fileReader, CSVFormat.DEFAULT
                    .withFirstRecordAsHeader()
                    .withIgnoreHeaderCase()
                    .withTrim());

            // Iterate over each record in the CSV file
            for (CSVRecord csvRecord : csvParser) {
                try {
                    // Map each CSV record to a CustomerDetailUploadDTO.
                    // This method assumes specific column names in the CSV.
                    CustomerDetailUploadDTO dto = mapCsvRecordToCustomerDetailDTO(csvRecord);
                    customerDetails.add(dto);
                } catch (IllegalArgumentException e) {
                    // Log a warning for malformed records and continue processing other records.
                    // This allows partial processing of valid data even if some records are bad.
                    log.warn("Skipping malformed CSV record at line {}: {}. Details: {}",
                            csvRecord.getRecordNumber(), csvRecord.toMap(), e.getMessage());
                    // Depending on business requirements, you might want to:
                    // - Collect these errors for a report.
                    // - Stop processing the entire file.
                }
            }
            log.info("Successfully parsed {} valid records from file: '{}' for batchId: {}",
                    customerDetails.size(), file.getOriginalFilename(), batchId);

        } catch (IOException e) {
            // Catch I/O errors during file reading.
            log.error("Failed to read or parse the uploaded file: '{}' for batchId: {}", file.getOriginalFilename(), batchId, e);
            throw new FileProcessingException("Failed to read or parse the uploaded file: " + e.getMessage(), e);
        } catch (Exception e) {
            // Catch any other unexpected exceptions during the parsing phase.
            log.error("An unexpected error occurred during file parsing for batchId: {}", batchId, e);
            throw new FileProcessingException("An unexpected error occurred during file parsing: " + e.getMessage(), e);
        }

        // 3. Publish parsed data to Kafka
        if (customerDetails.isEmpty()) {
            log.warn("No valid customer records found in the uploaded file: '{}' for batchId: {}. Not publishing to Kafka.",
                    file.getOriginalFilename(), batchId);
            return batchId; // Return batchId even if no records were processed or all were invalid.
        }

        try {
            // Send the list of DTOs to the Kafka topic.
            // The batchId is used as the Kafka message key, which can help ensure
            // that all records from a single file are processed by the same consumer partition
            // if key-based partitioning is configured.
            kafkaTemplate.send(customerUploadTopic, batchId, customerDetails)
                    .addCallback(
                            result -> log.info("Successfully published {} customer records for batchId: '{}' to Kafka topic: {}",
                                    customerDetails.size(), batchId, customerUploadTopic),
                            ex -> log.error("Failed to publish customer records for batchId: '{}' to Kafka topic: {}",
                                    batchId, customerUploadTopic, ex)
                    );
            log.info("Customer detail file processing initiated and data sent to Kafka for batchId: {}", batchId);
        } catch (Exception e) {
            // Catch any exceptions during Kafka message sending.
            log.error("Failed to send customer details to Kafka for batchId: {}", batchId, e);
            throw new FileProcessingException("Failed to send customer details to Kafka: " + e.getMessage(), e);
        }

        return batchId;
    }

    /**
     * Maps a single {@link CSVRecord} to a {@link CustomerDetailUploadDTO}.
     * This method extracts values from the CSV record based on predefined header names.
     * It performs basic validation to ensure required fields are present and not empty.
     *
     * @param csvRecord The {@link CSVRecord} representing a row from the CSV file.
     * @return A new {@link CustomerDetailUploadDTO} instance populated with data from the CSV record.
     * @throws IllegalArgumentException if a required column is missing or its value is empty.
     *                                  This exception is caught by the calling method to handle malformed records.
     */
    private CustomerDetailUploadDTO mapCsvRecordToCustomerDetailDTO(CSVRecord csvRecord) {
        // Example mapping. Adjust column names and data types as per the actual CSV structure
        // and the CustomerDetailUploadDTO definition.
        // Ensure header names match exactly (case-insensitive due to withIgnoreHeaderCase()).

        String customerId = getRequiredCsvValue(csvRecord, "CUSTOMER_ID");
        String firstName = getRequiredCsvValue(csvRecord, "FIRST_NAME");
        String lastName = getRequiredCsvValue(csvRecord, "LAST_NAME");
        String mobileNumber = getRequiredCsvValue(csvRecord, "MOBILE_NUMBER");
        String email = csvRecord.get("EMAIL"); // Optional field
        String pan = csvRecord.get("PAN");     // Optional field
        String aadhar = csvRecord.get("AADHAR"); // Optional field
        String productType = getRequiredCsvValue(csvRecord, "PRODUCT_TYPE");
        String loanAccountNumber = csvRecord.get("LOAN_ACCOUNT_NUMBER"); // Optional field

        // Further validation (e.g., regex for mobile/email, length checks)
        // and type conversions (e.g., String to Date, String to BigDecimal)
        // can be added here or in the DTO's constructor/setters.

        return new CustomerDetailUploadDTO(
                customerId,
                firstName,
                lastName,
                mobileNumber,
                email,
                pan,
                aadhar,
                productType,
                loanAccountNumber
        );
    }

    /**
     * Helper method to safely retrieve a required string value from a {@link CSVRecord}.
     *
     * @param csvRecord The {@link CSVRecord} from which to extract the value.
     * @param headerName The name of the CSV column header.
     * @return The trimmed string value from the specified column.
     * @throws IllegalArgumentException if the column is not found or its value is null/empty.
     */
    private String getRequiredCsvValue(CSVRecord csvRecord, String headerName) {
        String value = csvRecord.get(headerName);
        if (value == null || value.trim().isEmpty()) {
            throw new IllegalArgumentException(
                    String.format("Required column '%s' is missing or empty at line %d. Record: %s",
                            headerName, csvRecord.getRecordNumber(), csvRecord.toMap()));
        }
        return value.trim();
    }
}
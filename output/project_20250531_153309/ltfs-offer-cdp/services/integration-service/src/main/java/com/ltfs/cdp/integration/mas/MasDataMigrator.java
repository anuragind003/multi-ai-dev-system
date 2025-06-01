package com.ltfs.cdp.integration.mas;

import com.ltfs.cdp.integration.mas.dto.MasCustomerDto;
import com.ltfs.cdp.integration.mas.exception.MasIntegrationException;
import com.ltfs.cdp.integration.mas.mapper.MasDataMapper;
import com.ltfs.cdp.integration.mas.service.MasClient;
import com.ltfs.cdp.integration.mas.validator.MasDataValidator;
import com.ltfs.cdp.integration.service.DeduplicationService;
import com.ltfs.cdp.model.Customer;
import com.ltfs.cdp.repository.CustomerRepository;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;

/**
 * Service component responsible for migrating customer data from the MAS (Master Account System)
 * to the CDP (Customer Data Platform) system. This class orchestrates the data retrieval,
 * validation, transformation, persistence, and subsequent deduplication of customer records.
 * It is designed for one-time or periodic execution.
 */
@Service
public class MasDataMigrator {

    private static final Logger log = LoggerFactory.getLogger(MasDataMigrator.class);

    private final MasClient masClient;
    private final MasDataMapper masDataMapper;
    private final MasDataValidator masDataValidator;
    private final CustomerRepository customerRepository;
    private final DeduplicationService deduplicationService;

    /**
     * Constructs a new MasDataMigrator with necessary dependencies.
     *
     * @param masClient The client for fetching raw customer data from the MAS system.
     * @param masDataMapper The mapper for transforming MAS DTOs to CDP Customer entities.
     * @param masDataValidator The validator for performing basic column-level validation on MAS data.
     * @param customerRepository The repository for persisting Customer entities to the CDP database.
     * @param deduplicationService The service responsible for performing deduplication against the 'live book'.
     */
    @Autowired
    public MasDataMigrator(MasClient masClient,
                           MasDataMapper masDataMapper,
                           MasDataValidator masDataValidator,
                           CustomerRepository customerRepository,
                           DeduplicationService deduplicationService) {
        this.masClient = masClient;
        this.masDataMapper = masDataMapper;
        this.masDataValidator = masDataValidator;
        this.customerRepository = customerRepository;
        this.deduplicationService = deduplicationService;
    }

    /**
     * Initiates the data migration process from the MAS system to the CDP system.
     * This method performs the following steps:
     * 1. Fetches raw customer data from MAS.
     * 2. Iterates through each MAS customer record.
     * 3. Performs basic column-level validation on the MAS DTO.
     * 4. Maps the validated MAS DTO to a CDP Customer entity.
     * 5. Persists the CDP Customer entity to the database.
     * 6. Triggers the deduplication process for the newly saved customer.
     *
     * The entire migration process is wrapped in a transaction to ensure data consistency.
     * If an error occurs during fetching, the entire migration is aborted.
     * If an error occurs for an individual record (validation, mapping, or persistence),
     * it is logged, and the process attempts to continue with the next record.
     *
     * @return A {@link MigrationSummary} object detailing the outcome of the migration,
     *         including total records processed, successful records, failed records, and duration.
     */
    @Transactional // Ensures atomicity for the entire migration batch. Rollback on unchecked exceptions.
    public MigrationSummary migrateData() {
        log.info("Starting MAS data migration process...");
        long startTime = System.currentTimeMillis();
        int totalRecordsProcessed = 0;
        int successfulRecords = 0;
        int failedRecords = 0;

        try {
            // 1. Fetch raw data from MAS
            log.debug("Attempting to fetch raw customer data from MAS...");
            List<MasCustomerDto> masCustomers = masClient.fetchMasCustomerData();
            log.info("Successfully fetched {} customer records from MAS.", masCustomers.size());

            if (masCustomers.isEmpty()) {
                log.info("No new MAS customer data found for migration.");
                return new MigrationSummary(0, 0, 0, 0, "No data to migrate.");
            }

            totalRecordsProcessed = masCustomers.size();

            // Process each MAS customer record individually
            for (MasCustomerDto masCustomerDto : masCustomers) {
                try {
                    // Log the MAS ID for better traceability in case of errors
                    String currentMasId = masCustomerDto.getMasId() != null ? masCustomerDto.getMasId() : "UNKNOWN_MAS_ID";
                    log.debug("Processing MAS record with ID: {}", currentMasId);

                    // 2. Perform basic column-level validation
                    masDataValidator.validate(masCustomerDto);

                    // 3. Map raw MAS data to CDP Customer entity
                    Customer cdpCustomer = masDataMapper.toCustomerEntity(masCustomerDto);

                    // 4. Persist validated data
                    // The save operation is part of the overall transaction.
                    Customer savedCustomer = customerRepository.save(cdpCustomer);
                    log.debug("Successfully saved customer with CDP ID: {} (MAS ID: {})", savedCustomer.getId(), currentMasId);
                    successfulRecords++;

                    // 5. Trigger deduplication for the newly saved customer
                    // This call can be asynchronous in a high-volume scenario to avoid blocking.
                    // For simplicity, it's a direct call here.
                    deduplicationService.deduplicateCustomer(savedCustomer.getId());
                    log.debug("Deduplication triggered for customer with CDP ID: {}", savedCustomer.getId());

                } catch (MasIntegrationException e) {
                    // Catch specific validation or mapping errors
                    log.error("Data processing error for MAS record (ID: {}): {}. Skipping this record.",
                            masCustomerDto.getMasId(), e.getMessage());
                    failedRecords++;
                } catch (Exception e) {
                    // Catch any other unexpected errors during processing of a single record
                    log.error("Unexpected error processing MAS record (ID: {}): {}. Skipping this record.",
                            masCustomerDto.getMasId(), e.getMessage(), e);
                    failedRecords++;
                }
            }

            long endTime = System.currentTimeMillis();
            long duration = endTime - startTime;
            String message = String.format("MAS data migration completed in %d ms. Total records processed: %d, Successful: %d, Failed: %d.",
                    duration, totalRecordsProcessed, successfulRecords, failedRecords);
            log.info(message);
            return new MigrationSummary(totalRecordsProcessed, successfulRecords, failedRecords, duration, message);

        } catch (MasIntegrationException e) {
            // Catch errors specifically from MAS client (e.g., connectivity issues)
            log.error("Failed to fetch data from MAS system: {}", e.getMessage(), e);
            return new MigrationSummary(totalRecordsProcessed, successfulRecords, failedRecords, System.currentTimeMillis() - startTime, "Failed to fetch data from MAS: " + e.getMessage());
        } catch (Exception e) {
            // Catch any other unexpected errors that might occur outside the record-by-record processing loop
            log.error("An unexpected critical error occurred during MAS data migration: {}", e.getMessage(), e);
            return new MigrationSummary(totalRecordsProcessed, successfulRecords, failedRecords, System.currentTimeMillis() - startTime, "An unexpected critical error occurred: " + e.getMessage());
        }
    }

    /**
     * A simple immutable class to encapsulate the summary of a data migration operation.
     */
    public static class MigrationSummary {
        private final int totalRecordsProcessed;
        private final int successfulRecords;
        private final int failedRecords;
        private final long durationMillis;
        private final String message;

        /**
         * Constructs a new MigrationSummary.
         *
         * @param totalRecordsProcessed The total number of records attempted to be processed.
         * @param successfulRecords The number of records successfully processed and persisted.
         * @param failedRecords The number of records that failed processing (validation, mapping, or persistence).
         * @param durationMillis The total duration of the migration process in milliseconds.
         * @param message A descriptive message about the migration outcome.
         */
        public MigrationSummary(int totalRecordsProcessed, int successfulRecords, int failedRecords, long durationMillis, String message) {
            this.totalRecordsProcessed = totalRecordsProcessed;
            this.successfulRecords = successfulRecords;
            this.failedRecords = failedRecords;
            this.durationMillis = durationMillis;
            this.message = message;
        }

        public int getTotalRecordsProcessed() {
            return totalRecordsProcessed;
        }

        public int getSuccessfulRecords() {
            return successfulRecords;
        }

        public int getFailedRecords() {
            return failedRecords;
        }

        public long getDurationMillis() {
            return durationMillis;
        }

        public String getMessage() {
            return message;
        }

        @Override
        public String toString() {
            return "MigrationSummary{" +
                   "totalRecordsProcessed=" + totalRecordsProcessed +
                   ", successfulRecords=" + successfulRecords +
                   ", failedRecords=" + failedRecords +
                   ", durationMillis=" + durationMillis +
                   ", message='" + message + '\'' +
                   '}';
        }
    }
}
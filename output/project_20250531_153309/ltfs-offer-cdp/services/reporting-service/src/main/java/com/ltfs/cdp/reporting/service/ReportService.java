package com.ltfs.cdp.reporting.service;

import com.ltfs.cdp.reporting.exception.ReportGenerationException;
import com.ltfs.cdp.reporting.model.ReportData;
import com.ltfs.cdp.reporting.model.ReportFormat;
import com.ltfs.cdp.reporting.model.ReportRequest;
import com.ltfs.cdp.reporting.model.ReportType;
import com.ltfs.cdp.reporting.service.aggregator.ReportDataAggregator;
import com.ltfs.cdp.reporting.service.generator.ReportGenerator;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import java.util.Objects;

/**
 * Service orchestrating the report generation process.
 * This service acts as a facade, interacting with various data aggregators
 * to fetch the necessary data and then delegating to report generators
 * to produce the final report in the desired format.
 *
 * It handles the lifecycle from request validation, data aggregation,
 * to report generation and error handling.
 */
@Service
public class ReportService {

    private static final Logger log = LoggerFactory.getLogger(ReportService.class);

    private final ReportDataAggregator reportDataAggregator;
    private final ReportGenerator reportGenerator;

    /**
     * Constructs a new ReportService with the given data aggregator and report generator.
     * Spring's dependency injection will automatically provide these beans.
     *
     * @param reportDataAggregator The service responsible for aggregating raw data into report-ready formats.
     *                             This dependency is crucial for fetching and preparing the data required for reports.
     * @param reportGenerator The service responsible for generating the final report document (e.g., PDF, CSV).
     *                        This dependency handles the actual rendering of the report data into a file format.
     */
    @Autowired
    public ReportService(ReportDataAggregator reportDataAggregator, ReportGenerator reportGenerator) {
        this.reportDataAggregator = Objects.requireNonNull(reportDataAggregator, "ReportDataAggregator cannot be null");
        this.reportGenerator = Objects.requireNonNull(reportGenerator, "ReportGenerator cannot be null");
    }

    /**
     * Generates a report based on the provided report request.
     * This method orchestrates the entire report generation lifecycle:
     * 1. Validates the report request to ensure all necessary parameters are present and valid.
     * 2. Aggregates the necessary data from various sources based on the report type and parameters.
     *    This step typically involves querying databases, calling other microservices, and processing raw data.
     * 3. Delegates to the appropriate report generator to create the report content in the specified format.
     *    The generator transforms the structured aggregated data into a byte array representing the report file.
     *
     * @param request The {@link ReportRequest} containing parameters for report generation,
     *                such as report type, date range, customer ID, and desired output format.
     * @return A byte array representing the generated report file content (e.g., PDF, CSV bytes).
     * @throws IllegalArgumentException if the report request is invalid or missing required parameters.
     * @throws ReportGenerationException if any error occurs during data aggregation or report generation,
     *                                   indicating a failure in the report creation process.
     */
    public byte[] generateReport(ReportRequest request) {
        log.info("Initiating report generation for request: {}", request);

        // 1. Validate the request to ensure all necessary parameters are provided and are in a valid state.
        validateReportRequest(request);

        try {
            // 2. Aggregate data based on report type and request parameters.
            // The ReportDataAggregator fetches and processes data, returning it in a structured format.
            ReportData aggregatedData = reportDataAggregator.aggregateData(request);
            log.debug("Data aggregated successfully for report type: {}. Aggregated data records: {}.",
                      request.getReportType(), aggregatedData != null && aggregatedData.getData() != null ? aggregatedData.getData().size() : 0);

            // 3. Generate the report using the aggregated data and the specified format.
            // The ReportGenerator takes the structured data and produces the final report content as a byte array.
            byte[] reportContent = reportGenerator.generateReport(aggregatedData, request.getReportFormat());
            log.info("Report of type {} generated successfully. Report content size: {} bytes.",
                     request.getReportType(), reportContent != null ? reportContent.length : 0);

            return reportContent;
        } catch (ReportGenerationException e) {
            // Catch specific report generation exceptions and re-throw them to allow higher layers to handle.
            log.error("Failed to generate report for request {}: {}", request, e.getMessage(), e);
            throw e;
        } catch (Exception e) {
            // Catch any other unexpected exceptions during the process and wrap them in a custom exception.
            log.error("An unexpected error occurred during report generation for request {}: {}", request, e.getMessage(), e);
            throw new ReportGenerationException("An unexpected error occurred during report generation: " + e.getMessage(), e);
        }
    }

    /**
     * Validates the incoming report request.
     * This method performs checks to ensure that essential parameters like report type,
     * report format, and date range (for time-bound reports) are present and logically sound.
     *
     * @param request The {@link ReportRequest} object to validate.
     * @throws IllegalArgumentException if the request is null or contains invalid/missing parameters.
     */
    private void validateReportRequest(ReportRequest request) {
        if (request == null) {
            log.error("Report request cannot be null.");
            throw new IllegalArgumentException("Report request cannot be null.");
        }
        if (request.getReportType() == null) {
            log.error("Report type is missing in the request: {}", request);
            throw new IllegalArgumentException("Report type is required for report generation.");
        }
        if (request.getReportFormat() == null) {
            log.error("Report format is missing in the request: {}", request);
            throw new IllegalArgumentException("Report format is required for report generation.");
        }

        // Example of conditional validation based on report type.
        // For 'OFFER_PERFORMANCE' and 'CAMPAIGN_EFFECTIVENESS' reports, a date range is mandatory.
        if (request.getReportType() == ReportType.OFFER_PERFORMANCE || request.getReportType() == ReportType.CAMPAIGN_EFFECTIVENESS) {
            if (request.getStartDate() == null || request.getEndDate() == null) {
                log.error("Start date and End date are required for report type {}: {}", request.getReportType(), request);
                throw new IllegalArgumentException("Start date and End date are required for " + request.getReportType() + " reports.");
            }
            if (request.getStartDate().isAfter(request.getEndDate())) {
                log.error("Start date cannot be after end date for report type {}: {}", request.getReportType(), request);
                throw new IllegalArgumentException("Start date cannot be after end date.");
            }
        }
        // Add more validation rules as per specific report requirements.
        // For instance, if ReportType.CUSTOMER_360 requires a customerId:
        if (request.getReportType() == ReportType.CUSTOMER_360) {
            if (request.getCustomerId() == null || request.getCustomerId().trim().isEmpty()) {
                log.error("Customer ID is required for report type {}: {}", request.getReportType(), request);
                throw new IllegalArgumentException("Customer ID is required for " + request.getReportType() + " reports.");
            }
        }

        log.debug("Report request validated successfully: {}", request);
    }
}
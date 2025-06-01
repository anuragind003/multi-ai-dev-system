package com.ltfs.cdp.reporting.generator;

import com.ltfs.cdp.reporting.model.ReportRequest;
import com.ltfs.cdp.reporting.model.ReportType;
import com.ltfs.cdp.reporting.service.ReportDataService;
import com.ltfs.cdp.reporting.exception.ReportGenerationException;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;

import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.io.PrintWriter;
import java.nio.charset.StandardCharsets;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.LinkedHashSet;
import java.util.stream.Collectors;

/**
 * Service component responsible for generating various types of reports
 * based on aggregated data and predefined templates.
 * This class orchestrates the data retrieval and report formatting processes.
 * It leverages a {@link ReportDataService} to fetch raw data and then
 * applies specific formatting logic (e.g., CSV, Excel) to produce the final report.
 */
@Service
public class ReportGenerator {

    private static final Logger logger = LoggerFactory.getLogger(ReportGenerator.class);

    private final ReportDataService reportDataService;

    /**
     * Constructs a new ReportGenerator with the necessary dependencies.
     * Spring's dependency injection framework automatically provides the
     * {@link ReportDataService} instance.
     *
     * @param reportDataService The service responsible for fetching raw report data.
     */
    public ReportGenerator(ReportDataService reportDataService) {
        this.reportDataService = reportDataService;
    }

    /**
     * Generates a report based on the provided report request.
     * The method determines the report type from the request and delegates
     * to specific generation logic for that type. It fetches the necessary
     * data and then formats it into a byte array, typically representing a file.
     *
     * @param request The {@link ReportRequest} containing parameters for report generation,
     *                such as report type, date ranges, and filters.
     * @return A byte array representing the generated report file (e.g., CSV, Excel).
     * @throws ReportGenerationException If an error occurs during report data retrieval,
     *                                   unsupported report type is requested, or formatting fails.
     * @throws IllegalArgumentException If the report request or report type is null.
     */
    public byte[] generateReport(ReportRequest request) throws ReportGenerationException {
        if (request == null || request.getReportType() == null) {
            logger.error("Invalid report request: ReportRequest or ReportType is null.");
            throw new IllegalArgumentException("Report request and report type cannot be null.");
        }

        logger.info("Initiating report generation for type: {} with request: {}", request.getReportType(), request);

        try {
            // Step 1: Fetch raw data based on the report request parameters.
            // The ReportDataService is responsible for querying the database or other
            // data sources and aggregating the necessary information.
            List<Map<String, Object>> rawData = reportDataService.getReportData(request);

            // Step 2: Determine the report format and generate content based on the report type.
            // This switch-case structure allows for different formatting logic for each report type.
            byte[] reportContent;
            switch (request.getReportType()) {
                case CUSTOMER_PROFILE_SUMMARY:
                    // For simplicity, all reports currently generate CSV.
                    // In a real application, this might call a dedicated ExcelGenerator or PDFGenerator.
                    reportContent = generateCustomerProfileSummaryReport(rawData);
                    break;
                case OFFER_PERFORMANCE:
                    reportContent = generateOfferPerformanceReport(rawData);
                    break;
                case CAMPAIGN_EFFECTIVENESS:
                    reportContent = generateCampaignEffectivenessReport(rawData);
                    break;
                case DEDUPLICATION_STATISTICS:
                    reportContent = generateDeduplicationStatisticsReport(rawData);
                    break;
                // Add more report types as the system evolves.
                // Each new report type would require a corresponding private generation method.
                default:
                    logger.error("Unsupported report type requested: {}", request.getReportType());
                    throw new ReportGenerationException("Unsupported report type: " + request.getReportType());
            }

            logger.info("Successfully generated report for type: {}", request.getReportType());
            return reportContent;

        } catch (ReportGenerationException e) {
            // Catch and re-throw custom exceptions to propagate specific report generation errors.
            logger.error("Failed to generate report for type {}: {}", request.getReportType(), e.getMessage());
            throw e;
        } catch (Exception e) {
            // Catch any unexpected exceptions during the process and wrap them in a custom exception.
            logger.error("An unexpected error occurred during report generation for type {}: {}", request.getReportType(), e.getMessage(), e);
            throw new ReportGenerationException("An unexpected error occurred during report generation for type " + request.getReportType(), e);
        }
    }

    /**
     * Generates a CSV report specifically for Customer Profile Summary.
     * This method acts as a wrapper, delegating to the generic CSV generator.
     * In a more complex scenario, this method might apply specific data transformations
     * or use a dedicated template for this report type before calling the formatter.
     *
     * @param data The raw data (list of maps) to be included in the report.
     * @return A byte array containing the CSV report content.
     * @throws ReportGenerationException If an I/O error occurs during CSV writing.
     */
    private byte[] generateCustomerProfileSummaryReport(List<Map<String, Object>> data) throws ReportGenerationException {
        logger.debug("Generating Customer Profile Summary Report (CSV format).");
        // Example: If specific columns or ordering are required, process 'data' here
        // before passing to generateCsvReport.
        return generateCsvReport(data);
    }

    /**
     * Generates a CSV report specifically for Offer Performance.
     *
     * @param data The raw data.
     * @return A byte array containing the CSV report content.
     * @throws ReportGenerationException If an I/O error occurs during CSV writing.
     */
    private byte[] generateOfferPerformanceReport(List<Map<String, Object>> data) throws ReportGenerationException {
        logger.debug("Generating Offer Performance Report (CSV format).");
        return generateCsvReport(data);
    }

    /**
     * Generates a CSV report specifically for Campaign Effectiveness.
     *
     * @param data The raw data.
     * @return A byte array containing the CSV report content.
     * @throws ReportGenerationException If an I/O error occurs during CSV writing.
     */
    private byte[] generateCampaignEffectivenessReport(List<Map<String, Object>> data) throws ReportGenerationException {
        logger.debug("Generating Campaign Effectiveness Report (CSV format).");
        return generateCsvReport(data);
    }

    /**
     * Generates a CSV report specifically for Deduplication Statistics.
     *
     * @param data The raw data.
     * @return A byte array containing the CSV report content.
     * @throws ReportGenerationException If an I/O error occurs during CSV writing.
     */
    private byte[] generateDeduplicationStatisticsReport(List<Map<String, Object>> data) throws ReportGenerationException {
        logger.debug("Generating Deduplication Statistics Report (CSV format).");
        return generateCsvReport(data);
    }

    /**
     * Generic method to generate a CSV report from a list of maps.
     * Each map represents a row, and its keys represent column names.
     * This method dynamically determines headers by collecting all unique keys
     * from all data rows to ensure all possible columns are included.
     * It handles CSV escaping for field values.
     *
     * @param data The list of maps, where each map represents a row and keys are column names.
     * @return A byte array containing the CSV content, encoded in UTF-8.
     * @throws ReportGenerationException If an I/O error occurs during the writing process.
     */
    private byte[] generateCsvReport(List<Map<String, Object>> data) throws ReportGenerationException {
        // Use ByteArrayOutputStream to write CSV content into memory.
        // PrintWriter is used for convenient text writing, with auto-flushing and UTF-8 encoding.
        try (ByteArrayOutputStream baos = new ByteArrayOutputStream();
             PrintWriter writer = new PrintWriter(baos, true, StandardCharsets.UTF_8)) {

            if (data == null || data.isEmpty()) {
                logger.warn("No data provided for CSV report generation. Returning empty report.");
                writer.println("No data available for this report.");
                return baos.toByteArray();
            }

            // Determine headers: Collect all unique keys from all maps in the data list.
            // Using LinkedHashSet preserves the order of insertion, which can be useful
            // for consistent column ordering if keys appear in a particular sequence.
            Set<String> headers = data.stream()
                    .flatMap(map -> map.keySet().stream())
                    .collect(Collectors.toCollection(LinkedHashSet::new));

            // Write the header row to the CSV. Each header is escaped to handle special characters.
            writer.println(String.join(",", headers.stream().map(this::escapeCsvField).collect(Collectors.toList())));

            // Write data rows: Iterate through each map (row) in the data list.
            for (Map<String, Object> row : data) {
                // For each header, retrieve the corresponding value from the current row map.
                // If a value is null, an empty string is used. All values are escaped.
                List<String> rowValues = headers.stream()
                        .map(header -> {
                            Object value = row.get(header);
                            return (value != null) ? escapeCsvField(value.toString()) : "";
                        })
                        .collect(Collectors.toList());
                writer.println(String.join(",", rowValues));
            }

            writer.flush(); // Ensure all buffered data is written to the ByteArrayOutputStream.
            return baos.toByteArray(); // Return the complete CSV content as a byte array.
        } catch (IOException e) {
            logger.error("Error writing CSV report: {}", e.getMessage(), e);
            throw new ReportGenerationException("Failed to generate CSV report due to I/O error.", e);
        }
    }

    /**
     * Escapes a string for CSV output according to RFC 4180.
     * Rules:
     * 1. If a field contains a comma (,), double quote ("), or newline character (\n or \r),
     *    it must be enclosed in double quotes.
     * 2. If a field is enclosed in double quotes, any double quotes within the field
     *    must be escaped by preceding them with another double quote.
     *
     * @param field The string to escape.
     * @return The escaped string, suitable for a CSV field.
     */
    private String escapeCsvField(String field) {
        if (field == null) {
            return ""; // Null fields are represented as empty strings in CSV.
        }
        // Replace all occurrences of a double quote with two double quotes.
        String escapedField = field.replace("\"", "\"\"");
        
        // Check if the field needs to be enclosed in double quotes.
        // This is necessary if it contains a comma, a double quote (even after escaping),
        // or any newline characters.
        if (escapedField.contains(",") || escapedField.contains("\"") || escapedField.contains("\n") || escapedField.contains("\r")) {
            return "\"" + escapedField + "\"";
        }
        return escapedField; // No special characters, return as is.
    }
}
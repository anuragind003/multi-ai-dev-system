package com.ltfs.cdp.campaign.moengage;

import com.ltfs.cdp.campaign.model.MoengageCustomerData;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

import java.io.BufferedWriter;
import java.io.FileWriter;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.List;
import java.util.stream.Collectors;

/**
 * Service component responsible for generating campaign data files in a Moengage-specific CSV format.
 * This class handles the creation of the output directory, file naming, writing CSV headers,
 * and converting customer data objects into CSV rows.
 *
 * The generated files are intended for bulk upload to the Moengage platform for campaign execution
 * or customer profile updates.
 */
@Service
public class MoengageFileGenerator {

    private static final Logger logger = LoggerFactory.getLogger(MoengageFileGenerator.class);

    // Configurable output directory for generated Moengage files.
    // Default to /tmp/moengage_files if not specified in application properties.
    @Value("${moengage.file.output.directory:/tmp/moengage_files}")
    private String outputDirectory;

    // CSV delimiter used in the generated file.
    private static final String CSV_DELIMITER = ",";
    // New line separator for CSV rows.
    private static final String NEW_LINE_SEPARATOR = "\n";

    /**
     * Generates a Moengage-compatible CSV file from a list of customer campaign data.
     * The file will be named using the campaign ID and a timestamp to ensure uniqueness
     * and traceability.
     *
     * @param campaignId The ID of the campaign for which the file is being generated.
     * @param customerDataList A list of {@link MoengageCustomerData} objects to be written to the file.
     *                         Each object represents a single customer's data point for the campaign.
     * @return The absolute path of the generated file as a String, or {@code null} if an error occurred
     *         or if the input data list is empty.
     */
    public String generateMoengageFile(String campaignId, List<MoengageCustomerData> customerDataList) {
        if (customerDataList == null || customerDataList.isEmpty()) {
            logger.warn("No customer data provided for campaignId: {}. Skipping Moengage file generation.", campaignId);
            return null;
        }

        // Construct the full path for the output directory.
        Path outputPath = Paths.get(outputDirectory);
        try {
            // Create the output directory if it does not already exist.
            Files.createDirectories(outputPath);
            logger.debug("Ensured output directory exists: {}", outputPath.toAbsolutePath());
        } catch (IOException e) {
            logger.error("Failed to create output directory: {}. Error: {}", outputDirectory, e.getMessage(), e);
            return null; // Cannot proceed without a valid directory.
        }

        // Generate a unique file name using campaign ID and current timestamp.
        String timestamp = LocalDateTime.now().format(DateTimeFormatter.ofPattern("yyyyMMdd_HHmmss"));
        String fileName = String.format("moengage_campaign_%s_%s.csv", campaignId, timestamp);
        Path filePath = outputPath.resolve(fileName); // Resolve the file path within the output directory.

        try (BufferedWriter writer = new BufferedWriter(new FileWriter(filePath.toFile()))) {
            // Write the CSV header row.
            writer.append(getMoengageCsvHeader());
            writer.append(NEW_LINE_SEPARATOR);

            // Iterate through the list of customer data and write each as a CSV row.
            for (MoengageCustomerData data : customerDataList) {
                writer.append(convertToCsvRow(data));
                writer.append(NEW_LINE_SEPARATOR);
            }

            logger.info("Successfully generated Moengage file for campaignId: {} at path: {}", campaignId, filePath.toAbsolutePath());
            return filePath.toAbsolutePath().toString(); // Return the path of the generated file.

        } catch (IOException e) {
            // Log any I/O errors during file writing.
            logger.error("Error generating Moengage file for campaignId: {} at {}. Error: {}",
                    campaignId, filePath.toAbsolutePath(), e.getMessage(), e);
            return null; // Indicate failure.
        }
    }

    /**
     * Defines the CSV header for the Moengage file.
     * This header should align with the fields expected by Moengage for customer profile updates
     * or campaign uploads. The order of fields here dictates the order in the generated CSV.
     *
     * @return A comma-separated string representing the CSV header.
     */
    private String getMoengageCsvHeader() {
        // IMPORTANT: Adjust these headers based on the actual Moengage import schema.
        // Common fields for customer data and campaign offers are included as an example.
        return "customer_id,mobile_number,email,campaign_id,offer_id,offer_status,deduplication_status,offer_details";
    }

    /**
     * Converts a {@link MoengageCustomerData} object into a CSV formatted string row.
     * Each field is escaped to handle potential commas, double quotes, or newlines within the data,
     * ensuring proper CSV formatting according to RFC 4180.
     *
     * @param data The {@link MoengageCustomerData} object to convert.
     * @return A comma-separated string representing one row of data.
     */
    private String convertToCsvRow(MoengageCustomerData data) {
        // Collect all fields as a list of escaped strings.
        List<String> fields = List.of(
                escapeCsvField(data.getCustomerId()),
                escapeCsvField(data.getMobileNumber()),
                escapeCsvField(data.getEmail()),
                escapeCsvField(data.getCampaignId()),
                escapeCsvField(data.getOfferId()),
                escapeCsvField(data.getOfferStatus()),
                escapeCsvField(data.getDeduplicationStatus()),
                escapeCsvField(data.getOfferDetails())
        );
        // Join the escaped fields with the CSV delimiter.
        return String.join(CSV_DELIMITER, fields);
    }

    /**
     * Escapes a string for CSV output according to RFC 4180.
     * This method handles special characters (comma, double quotes, newlines) by:
     * 1. Treating {@code null} values as empty strings.
     * 2. Enclosing the field in double quotes if it contains the delimiter, double quotes, or newlines.
     * 3. Doubling any internal double quotes within the field.
     *
     * @param field The string field to escape.
     * @return The escaped string, ready for CSV output.
     */
    private String escapeCsvField(String field) {
        if (field == null) {
            return ""; // Treat null as an empty string in CSV.
        }

        // Check if the field contains characters that require quoting in CSV:
        // - The CSV delimiter (comma)
        // - Double quotes
        // - Newline characters
        boolean needsQuoting = field.contains(CSV_DELIMITER) ||
                               field.contains("\"") ||
                               field.contains(NEW_LINE_SEPARATOR);

        if (needsQuoting) {
            // If the field contains double quotes, they must be escaped by doubling them.
            String escapedField = field.replace("\"", "\"\"");
            // The entire field must then be enclosed in double quotes.
            return "\"" + escapedField + "\"";
        }
        // If no special characters are present, return the field as is.
        return field;
    }
}
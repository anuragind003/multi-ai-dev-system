package com.ltfs.cdp.campaign.service;

import com.ltfs.cdp.campaign.dto.MoengageCampaignDataDto;
import com.ltfs.cdp.campaign.exception.FileGenerationException;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.io.BufferedWriter;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.time.format.DateTimeFormatter;
import java.util.List;
import java.util.Optional;

/**
 * Service class responsible for generating campaign data files in Moengage specific format (CSV).
 * This class fetches campaign-related customer data and transforms it into a CSV file
 * that can be uploaded to Moengage for targeted campaigns.
 *
 * <p>Dependencies:
 * <ul>
 *     <li>{@link MoengageCampaignDataDto}: DTO representing the data structure required by Moengage.
 *         (Expected to be in `com.ltfs.cdp.campaign.dto` package)</li>
 *     <li>{@link CampaignDataFetchService}: Service interface to fetch the raw campaign data.
 *         (Expected to be in `com.ltfs.cdp.campaign.service` or similar package)</li>
 *     <li>{@link FileGenerationException}: Custom exception for handling file generation errors.
 *         (Expected to be in `com.ltfs.cdp.campaign.exception` package)</li>
 * </ul>
 * </p>
 *
 * <p>Configuration:
 * The output directory for Moengage files can be configured via the Spring property
 * {@code moengage.file.output.directory}. Defaults to {@code /tmp/moengage_files}.
 * </p>
 */
@Service
public class MoengageFileGenerator {

    private static final Logger logger = LoggerFactory.getLogger(MoengageFileGenerator.class);

    // Define the CSV header for Moengage file. This header must match Moengage's expected format.
    // Common fields include identifiers (mobile_number, email, customer_id) and custom attributes.
    private static final String CSV_HEADER = "mobile_number,email,customer_id,campaign_name,offer_id,offer_status,loan_product_type,disbursement_amount,campaign_start_date,campaign_end_date,custom_attr_1,custom_attr_2";
    private static final String CSV_DELIMITER = ",";
    // Date formatter for ISO_LOCAL_DATE (e.g., "2023-01-15"). Moengage typically expects YYYY-MM-DD.
    private static final DateTimeFormatter DATE_FORMATTER = DateTimeFormatter.ISO_LOCAL_DATE;

    // Injected service to retrieve campaign data from the database or another source.
    private final CampaignDataFetchService campaignDataFetchService;

    // Configurable output directory for the generated Moengage files.
    @Value("${moengage.file.output.directory:/tmp/moengage_files}")
    private String moengageOutputDirectory;

    /**
     * Constructs a new MoengageFileGenerator with the specified data fetch service.
     *
     * @param campaignDataFetchService The service responsible for fetching campaign data.
     */
    public MoengageFileGenerator(CampaignDataFetchService campaignDataFetchService) {
        this.campaignDataFetchService = campaignDataFetchService;
    }

    /**
     * Generates a CSV file containing campaign data formatted specifically for Moengage.
     * The file will be named using the campaign ID and a timestamp, and stored in the
     * directory configured by {@code moengage.file.output.directory}.
     *
     * <p>The process involves:
     * <ol>
     *     <li>Fetching relevant campaign data using {@link CampaignDataFetchService}.</li>
     *     <li>Constructing the file path and ensuring the output directory exists.</li>
     *     <li>Writing the CSV header to the file.</li>
     *     <li>Iterating through the fetched data, converting each record to a CSV row, and writing it to the file.</li>
     * </ol>
     * </p>
     *
     * @param campaignId The unique identifier of the campaign for which the data file is to be generated.
     * @return The absolute path to the successfully generated Moengage CSV file. Returns {@code null}
     *         if no data is found for the given campaign ID, indicating no file was generated.
     * @throws FileGenerationException if any I/O error occurs during file creation or writing,
     *                                 or if the output directory cannot be created.
     */
    @Transactional(readOnly = true) // Data fetching operation should be read-only
    public String generateMoengageFile(String campaignId) throws FileGenerationException {
        logger.info("Initiating Moengage file generation process for campaign ID: {}", campaignId);

        // 1. Fetch campaign data from the underlying service.
        List<MoengageCampaignDataDto> campaignDataList = campaignDataFetchService.fetchCampaignDataForMoengage(campaignId);

        if (campaignDataList.isEmpty()) {
            logger.warn("No campaign data found for campaign ID: {}. Skipping Moengage file generation.", campaignId);
            // Returning null indicates no file was generated due to lack of data.
            return null;
        }

        // 2. Construct the file name and path.
        // File name includes campaign ID and a timestamp to ensure uniqueness.
        String fileName = String.format("moengage_campaign_%s_%d.csv", campaignId, System.currentTimeMillis());
        Path outputPath = Paths.get(moengageOutputDirectory, fileName);

        // Ensure the parent directory for the output file exists.
        try {
            Files.createDirectories(outputPath.getParent());
            logger.debug("Ensured output directory exists: {}", outputPath.getParent());
        } catch (IOException e) {
            logger.error("Failed to create output directory for Moengage file at: {}", outputPath.getParent(), e);
            throw new FileGenerationException("Failed to create output directory for Moengage file: " + outputPath.getParent(), e);
        }

        // 3. Write data to the CSV file.
        try (BufferedWriter writer = Files.newBufferedWriter(outputPath)) {
            // Write the CSV header as the first line.
            writer.write(CSV_HEADER);
            writer.newLine();

            // Write each data record as a new CSV row.
            for (MoengageCampaignDataDto data : campaignDataList) {
                writer.write(convertToCsvRow(data));
                writer.newLine();
            }

            logger.info("Successfully generated Moengage file for campaign ID: {} at path: {}", campaignId, outputPath.toAbsolutePath());
            return outputPath.toAbsolutePath().toString();

        } catch (IOException e) {
            logger.error("Error writing Moengage file for campaign ID: {} to path: {}", campaignId, outputPath.toAbsolutePath(), e);
            // Wrap IOException in a custom FileGenerationException for consistent error handling in the service layer.
            throw new FileGenerationException("Failed to write Moengage file for campaign ID: " + campaignId, e);
        } catch (Exception e) {
            // Catch any other unexpected exceptions during the process.
            logger.error("An unexpected error occurred during Moengage file generation for campaign ID: {}", campaignId, e);
            throw new FileGenerationException("An unexpected error occurred during Moengage file generation for campaign ID: " + campaignId, e);
        }
    }

    /**
     * Converts a {@link MoengageCampaignDataDto} object into a single CSV formatted string row.
     * This method handles null values by converting them to empty strings and performs basic
     * CSV escaping for values that might contain the delimiter (comma) or quotes.
     *
     * @param data The DTO containing campaign data for a single customer.
     * @return A CSV formatted string representing one row of data.
     */
    private String convertToCsvRow(MoengageCampaignDataDto data) {
        // Using StringBuilder for efficient string concatenation.
        StringBuilder sb = new StringBuilder();

        // Append each field, ensuring nulls are handled and basic CSV rules are followed.
        // The order of appending must match the CSV_HEADER.
        appendCsvValue(sb, data.getMobileNumber());
        appendCsvValue(sb, data.getEmail());
        appendCsvValue(sb, data.getCustomerId());
        appendCsvValue(sb, data.getCampaignName());
        appendCsvValue(sb, data.getOfferId());
        appendCsvValue(sb, data.getOfferStatus());
        appendCsvValue(sb, data.getLoanProductType());
        // Convert BigDecimal to String, handle null.
        appendCsvValue(sb, Optional.ofNullable(data.getDisbursementAmount()).map(Object::toString).orElse(""));
        // Format LocalDate to String, handle null.
        appendCsvValue(sb, Optional.ofNullable(data.getCampaignStartDate()).map(DATE_FORMATTER::format).orElse(""));
        // Format LocalDate to String, handle null.
        appendCsvValue(sb, Optional.ofNullable(data.getCampaignEndDate()).map(DATE_FORMATTER::format).orElse(""));
        appendCsvValue(sb, data.getCustomAttr1());
        // The last column should not have a trailing delimiter.
        appendCsvValue(sb, data.getCustomAttr2(), true);

        return sb.toString();
    }

    /**
     * Appends a string value to the StringBuilder, followed by the CSV delimiter.
     * This is a helper for all but the last column.
     *
     * @param sb The StringBuilder to append to.
     * @param value The string value to append.
     */
    private void appendCsvValue(StringBuilder sb, String value) {
        appendCsvValue(sb, value, false);
    }

    /**
     * Appends a string value to the StringBuilder, applying basic CSV escaping rules.
     * If the value contains the delimiter (comma), double quotes, or newlines, it will be
     * enclosed in double quotes, and any internal double quotes will be escaped by doubling them.
     *
     * @param sb The StringBuilder to append to.
     * @param value The string value to append. Null values are treated as empty strings.
     * @param isLastColumn A boolean indicating if this is the last column in the row.
     *                     If true, no delimiter is appended after the value.
     */
    private void appendCsvValue(StringBuilder sb, String value, boolean isLastColumn) {
        String actualValue = Optional.ofNullable(value).orElse("");

        // Basic CSV escaping logic:
        // If the value contains the delimiter, a double quote, or a newline,
        // it must be enclosed in double quotes. Any double quotes within the value
        // must be escaped by doubling them.
        if (actualValue.contains(CSV_DELIMITER) || actualValue.contains("\"") || actualValue.contains("\n") || actualValue.contains("\r")) {
            String escapedValue = actualValue.replace("\"", "\"\""); // Escape internal quotes
            sb.append("\"").append(escapedValue).append("\"");
        } else {
            sb.append(actualValue);
        }

        // Append delimiter if it's not the last column.
        if (!isLastColumn) {
            sb.append(CSV_DELIMITER);
        }
    }
}
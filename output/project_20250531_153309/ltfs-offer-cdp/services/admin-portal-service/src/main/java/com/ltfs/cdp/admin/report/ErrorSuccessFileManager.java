package com.ltfs.cdp.admin.report;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.nio.file.StandardOpenOption;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.List;
import java.util.stream.Stream;

/**
 * Service class responsible for managing the generation, storage, and retrieval of
 * error and success reports for batch processes initiated via the admin portal.
 * Reports are stored on the file system.
 *
 * This class handles file system operations, including creating directories,
 * writing report content, and reading report content. It uses configurable
 * storage paths and generates unique file names based on process IDs and timestamps.
 */
@Service
public class ErrorSuccessFileManager {

    private static final Logger logger = LoggerFactory.getLogger(ErrorSuccessFileManager.class);

    // Configurable base directory for storing reports.
    // Default value is provided for local development/testing.
    @Value("${report.storage.base-path:/tmp/cdp/reports}")
    private String reportStorageBasePath;

    // Date-time formatter for generating unique timestamps in file names.
    private static final DateTimeFormatter FILENAME_TIMESTAMP_FORMATTER = DateTimeFormatter.ofPattern("yyyyMMdd_HHmmssSSS");

    /**
     * Enum to represent the type of report (Error or Success).
     * Provides a string representation for use in file names.
     */
    public enum ReportType {
        ERROR("error"),
        SUCCESS("success");

        private final String typeName;

        ReportType(String typeName) {
            this.typeName = typeName;
        }

        public String getTypeName() {
            return typeName;
        }
    }

    /**
     * Saves a report (either error or success) to the file system.
     * The report content is expected as a list of strings, where each string represents a line.
     * The file will be created if it doesn't exist, or truncated if it does.
     *
     * @param processId The unique identifier for the batch process (e.g., a batch job ID).
     * @param reportType The type of report (ERROR or SUCCESS).
     * @param content The list of strings representing the report content. Each string will be written as a new line.
     * @return The absolute {@link Path} to the saved report file.
     * @throws IOException If an I/O error occurs during directory creation or file writing.
     */
    public Path saveReport(String processId, ReportType reportType, List<String> content) throws IOException {
        // Resolve the base directory path
        Path baseDirPath = Paths.get(reportStorageBasePath);

        // Ensure the base directory exists. If not, attempt to create it.
        if (!Files.exists(baseDirPath)) {
            try {
                Files.createDirectories(baseDirPath);
                logger.info("Created report storage directory: {}", baseDirPath.toAbsolutePath());
            } catch (IOException e) {
                logger.error("Failed to create report storage directory {}: {}", baseDirPath.toAbsolutePath(), e.getMessage());
                // Re-throw as a specific IOException to indicate directory creation failure
                throw new IOException("Could not create report storage directory: " + baseDirPath.toAbsolutePath(), e);
            }
        }

        // Generate a unique file name for the report.
        String fileName = generateReportFileName(processId, reportType);
        // Resolve the full path to the report file.
        Path filePath = baseDirPath.resolve(fileName);

        try {
            // Write all lines to the file.
            // StandardOpenOption.CREATE: Creates the file if it doesn't exist.
            // StandardOpenOption.TRUNCATE_EXISTING: Truncates the file to 0 bytes if it already exists.
            Files.write(filePath, content, StandardOpenOption.CREATE, StandardOpenOption.TRUNCATE_EXISTING);
            logger.info("Successfully saved {} report for processId '{}' to: {}", reportType.getTypeName(), processId, filePath.toAbsolutePath());
            return filePath;
        } catch (IOException e) {
            logger.error("Failed to save {} report for processId '{}' to {}: {}", reportType.getTypeName(), processId, filePath.toAbsolutePath(), e.getMessage());
            // Re-throw as a specific IOException to indicate file writing failure
            throw new IOException("Could not save report to: " + filePath.toAbsolutePath(), e);
        }
    }

    /**
     * Retrieves the content of a specific report file as a list of strings.
     * This method first attempts to find the latest report file matching the process ID and report type.
     *
     * @param processId The unique identifier for the batch process.
     * @param reportType The type of report (ERROR or SUCCESS).
     * @return A {@link List} of strings, where each string is a line from the report file.
     * @throws IOException If an I/O error occurs during file reading or if no matching report file is found.
     */
    public List<String> getReportContent(String processId, ReportType reportType) throws IOException {
        // Find the path to the latest report file for the given processId and reportType.
        Path filePath = findLatestReportPath(processId, reportType);

        // Check if a file was found and if it actually exists.
        if (filePath == null || !Files.exists(filePath)) {
            logger.warn("No {} report found for processId '{}' or file does not exist at expected path.", reportType.getTypeName(), processId);
            throw new IOException("Report file not found for processId: " + processId + ", type: " + reportType.getTypeName());
        }

        try {
            // Read all lines from the found file.
            List<String> lines = Files.readAllLines(filePath);
            logger.debug("Successfully read {} lines from {} report for processId '{}' from: {}", lines.size(), reportType.getTypeName(), processId, filePath.toAbsolutePath());
            return lines;
        } catch (IOException e) {
            logger.error("Failed to read {} report for processId '{}' from {}: {}", reportType.getTypeName(), processId, filePath.toAbsolutePath(), e.getMessage());
            // Re-throw as a specific IOException to indicate file reading failure
            throw new IOException("Could not read report from: " + filePath.toAbsolutePath(), e);
        }
    }

    /**
     * Finds the path to the latest report file for a given process ID and report type.
     * This method assumes a specific naming convention (`[processId]_[timestamp]_[reportType].txt`)
     * and searches the configured base directory. It returns the path to the most recently
     * modified file matching the pattern.
     *
     * @param processId The unique identifier for the batch process.
     * @param reportType The type of report (ERROR or SUCCESS).
     * @return The {@link Path} to the latest report file, or {@code null} if no matching file is found.
     * @throws IOException If an I/O error occurs during directory listing.
     */
    public Path findLatestReportPath(String processId, ReportType reportType) throws IOException {
        Path baseDirPath = Paths.get(reportStorageBasePath);

        // If the base directory doesn't exist, no reports can be found.
        if (!Files.exists(baseDirPath)) {
            logger.warn("Report storage directory does not exist: {}", baseDirPath.toAbsolutePath());
            return null;
        }

        // Define the expected file name pattern parts.
        final String prefix = processId + "_";
        final String suffix = "_" + reportType.getTypeName() + ".txt"; // Assuming .txt extension for simplicity

        try (Stream<Path> paths = Files.list(baseDirPath)) {
            // Filter files by name pattern and find the one with the latest modification time.
            return paths
                    .filter(Files::isRegularFile) // Ensure it's a regular file, not a directory
                    .filter(p -> p.getFileName().toString().startsWith(prefix) && p.getFileName().toString().endsWith(suffix))
                    .max((p1, p2) -> {
                        try {
                            // Compare by last modified time to find the latest report.
                            return Files.getLastModifiedTime(p1).compareTo(Files.getLastModifiedTime(p2));
                        } catch (IOException e) {
                            // Log a warning if modification time comparison fails for specific files.
                            logger.warn("Error comparing file modification times for {} and {}: {}", p1, p2, e.getMessage());
                            return 0; // Treat as equal if comparison fails to avoid breaking the stream.
                        }
                    })
                    .orElse(null); // Return null if no matching file is found.
        } catch (IOException e) {
            logger.error("Failed to list files in report storage directory {}: {}", baseDirPath.toAbsolutePath(), e.getMessage());
            // Re-throw as a specific IOException to indicate directory listing failure.
            throw new IOException("Could not list files in report directory: " + baseDirPath.toAbsolutePath(), e);
        }
    }

    /**
     * Generates a unique file name for a report based on the process ID, current timestamp, and report type.
     * The format is: {@code [processId]_[yyyyMMdd_HHmmssSSS]_[reportType].txt}
     * This ensures uniqueness and provides context within the file system.
     *
     * @param processId The unique identifier for the batch process.
     * @param reportType The type of report (ERROR or SUCCESS).
     * @return A string representing the generated file name.
     */
    private String generateReportFileName(String processId, ReportType reportType) {
        String timestamp = LocalDateTime.now().format(FILENAME_TIMESTAMP_FORMATTER);
        return String.format("%s_%s_%s.txt", processId, timestamp, reportType.getTypeName());
    }
}
package com.ltfs.cdp.reporting.service;

import org.apache.poi.ss.usermodel.*;
import org.apache.poi.xssf.usermodel.XSSFWorkbook;
import org.springframework.core.io.ByteArrayResource;
import org.springframework.stereotype.Service;

import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.io.PrintWriter;
import java.nio.charset.StandardCharsets;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.LinkedHashSet;
import java.util.StringJoiner;
import java.util.stream.Collectors;

/**
 * Manages the export of reports to different formats (e.g., CSV, Excel, PDF).
 * This service provides methods to convert a list of data maps into various file formats,
 * returning the content as a byte array resource suitable for download.
 *
 * <p>Dependencies for Excel functionality (Apache POI) are assumed to be present in the project's build configuration (e.g., pom.xml):</p>
 * <pre>{@code
 * <dependency>
 *     <groupId>org.apache.poi</groupId>
 *     <artifactId>poi-ooxml</artifactId>
 *     <version>5.2.3</version> <!-- Use a compatible version -->
 * </dependency>
 * }</pre>
 * <p>For production-grade PDF generation, a dedicated library like iText or JasperReports would be required.</p>
 */
@Service
public class FileExportManager {

    /**
     * Enum representing the supported report export formats.
     */
    public enum ExportFormat {
        CSV("text/csv", ".csv"),
        EXCEL("application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", ".xlsx"),
        /**
         * PDF generation is complex and typically requires a dedicated reporting library
         * like iText or JasperReports for production-grade, formatted output.
         * This implementation provides a basic text-based representation that is NOT a true PDF.
         * A proper PDF library dependency is required for actual PDF generation.
         */
        PDF("application/pdf", ".pdf");

        private final String mediaType;
        private final String fileExtension;

        ExportFormat(String mediaType, String fileExtension) {
            this.mediaType = mediaType;
            this.fileExtension = fileExtension;
        }

        public String getMediaType() {
            return mediaType;
        }

        public String getFileExtension() {
            return fileExtension;
        }
    }

    /**
     * Exports the given report data to the specified format.
     *
     * @param reportData A list of maps, where each map represents a row and keys are column headers.
     *                   It's assumed that all maps have a consistent set of keys for columns,
     *                   though the method attempts to derive headers robustly.
     * @param format The desired export format (CSV, EXCEL, PDF).
     * @return A ByteArrayResource containing the exported file content.
     * @throws ReportExportException if an error occurs during the export process or an unsupported format is requested.
     */
    public ByteArrayResource exportReport(List<Map<String, Object>> reportData, ExportFormat format) throws ReportExportException {
        if (reportData == null || reportData.isEmpty()) {
            // If no data, return an empty resource. A specific business requirement might
            // dictate throwing an exception or returning a file with only headers.
            return new ByteArrayResource(new byte[0]);
        }

        // Extract headers from all maps to ensure all possible columns are included.
        // Using LinkedHashSet to preserve the order of appearance of headers.
        Set<String> headers = reportData.stream()
                .flatMap(map -> map.keySet().stream())
                .collect(Collectors.toCollection(LinkedHashSet::new));

        try (ByteArrayOutputStream baos = new ByteArrayOutputStream()) {
            byte[] fileContent;
            switch (format) {
                case CSV:
                    fileContent = exportToCsv(reportData, headers);
                    break;
                case EXCEL:
                    fileContent = exportToExcel(reportData, headers);
                    break;
                case PDF:
                    // This is a placeholder. A real PDF generation requires a dedicated library.
                    fileContent = exportToPdf(reportData, headers);
                    break;
                default:
                    throw new ReportExportException("Unsupported export format: " + format);
            }
            return new ByteArrayResource(fileContent);
        } catch (IOException e) {
            throw new ReportExportException("Failed to export report due to an I/O error.", e);
        } catch (Exception e) {
            // Catch any other unexpected exceptions during export process
            throw new ReportExportException("An unexpected error occurred during report export.", e);
        }
    }

    /**
     * Exports the report data to CSV format.
     *
     * @param reportData The data to export.
     * @param headers The ordered list of headers for the CSV file.
     * @return A byte array containing the CSV content.
     * @throws IOException if an I/O error occurs during CSV generation.
     */
    private byte[] exportToCsv(List<Map<String, Object>> reportData, Set<String> headers) throws IOException {
        try (ByteArrayOutputStream baos = new ByteArrayOutputStream();
             // Use PrintWriter with UTF-8 for broad compatibility
             PrintWriter writer = new PrintWriter(baos, true, StandardCharsets.UTF_8)) {

            // Write headers row
            writer.println(String.join(",", headers.stream().map(this::escapeCsvValue).collect(Collectors.toList())));

            // Write data rows
            for (Map<String, Object> row : reportData) {
                StringJoiner sj = new StringJoiner(",");
                for (String header : headers) {
                    // Get value, default to empty string if key is not present in a row
                    Object value = row.getOrDefault(header, "");
                    sj.add(escapeCsvValue(String.valueOf(value)));
                }
                writer.println(sj.toString());
            }
            writer.flush(); // Ensure all buffered data is written to the output stream
            return baos.toByteArray();
        }
    }

    /**
     * Escapes a string value for CSV format.
     * Handles commas, double quotes, and newlines by enclosing the value in double quotes
     * and doubling any existing double quotes within the value.
     *
     * @param value The string value to escape.
     * @return The escaped CSV string.
     */
    private String escapeCsvValue(String value) {
        if (value == null) {
            return "";
        }
        // Replace all double quotes with two double quotes
        String escaped = value.replace("\"", "\"\"");
        // If the value contains a comma, double quote, or newline, enclose it in double quotes
        if (escaped.contains(",") || escaped.contains("\"") || escaped.contains("\n") || escaped.contains("\r")) {
            return "\"" + escaped + "\"";
        }
        return escaped;
    }

    /**
     * Exports the report data to Excel (XLSX) format using Apache POI.
     *
     * @param reportData The data to export.
     * @param headers The ordered list of headers for the Excel file.
     * @return A byte array containing the Excel content.
     * @throws IOException if an I/O error occurs during Excel generation.
     */
    private byte[] exportToExcel(List<Map<String, Object>> reportData, Set<String> headers) throws IOException {
        // XSSFWorkbook is used for .xlsx format (Excel 2007 and later)
        try (Workbook workbook = new XSSFWorkbook();
             ByteArrayOutputStream baos = new ByteArrayOutputStream()) {

            Sheet sheet = workbook.createSheet("Report");

            // Create header row and apply bold style
            Row headerRow = sheet.createRow(0);
            CellStyle headerStyle = workbook.createCellStyle();
            Font headerFont = workbook.createFont();
            headerFont.setBold(true);
            headerStyle.setFont(headerFont);

            int colNum = 0;
            for (String header : headers) {
                Cell cell = headerRow.createCell(colNum++);
                cell.setCellValue(header);
                cell.setCellStyle(headerStyle);
            }

            // Create data rows starting from the second row (index 1)
            int rowNum = 1;
            for (Map<String, Object> rowData : reportData) {
                Row row = sheet.createRow(rowNum++);
                colNum = 0;
                for (String header : headers) {
                    Cell cell = row.createCell(colNum++);
                    Object value = rowData.getOrDefault(header, ""); // Get value, default to empty string
                    setCellValue(cell, value); // Set cell value based on type
                }
            }

            // Auto-size columns for better readability. This should be done after all data is written.
            for (int i = 0; i < headers.size(); i++) {
                sheet.autoSizeColumn(i);
            }

            workbook.write(baos); // Write the workbook content to the output stream
            return baos.toByteArray();
        }
    }

    /**
     * Sets the cell value based on the object's type.
     * Handles String, Number, Boolean, and java.util.Date types.
     * For other types, it defaults to their string representation.
     *
     * @param cell The Excel cell to set the value for.
     * @param value The object value to be placed in the cell.
     */
    private void setCellValue(Cell cell, Object value) {
        if (value == null) {
            cell.setCellValue(""); // Treat null as empty string
        } else if (value instanceof String) {
            cell.setCellValue((String) value);
        } else if (value instanceof Number) {
            cell.setCellValue(((Number) value).doubleValue()); // Convert all numbers to double for Excel
        } else if (value instanceof Boolean) {
            cell.setCellValue((Boolean) value);
        } else if (value instanceof java.util.Date) {
            // For dates, a specific cell style with a date format might be desired in a real application.
            cell.setCellValue((java.util.Date) value);
        } else {
            cell.setCellValue(String.valueOf(value)); // Fallback to string representation for other types
        }
    }

    /**
     * Exports the report data to PDF format (placeholder implementation).
     * <p>
     * IMPORTANT: This is a highly simplified text-based representation and is NOT a true PDF file.
     * For complex, formatted, and production-grade PDF reports, a dedicated PDF generation library
     * such as iText (e.g., `com.itextpdf:itextpdf` or `com.itextpdf:itext7-core`) or
     * a reporting tool like JasperReports would be required.
     * This method returns a byte array of plain text content, which, if saved with a .pdf extension,
     * will not be a valid PDF document.
     * </p>
     *
     * @param reportData The data to export.
     * @param headers The ordered list of headers.
     * @return A byte array containing the text content that *could* be rendered into a PDF.
     * @throws IOException if an I/O error occurs (though unlikely for this text-based approach).
     */
    private byte[] exportToPdf(List<Map<String, Object>> reportData, Set<String> headers) throws IOException {
        StringBuilder pdfContentBuilder = new StringBuilder();
        pdfContentBuilder.append("LTFS Offer CDP Report\n");
        pdfContentBuilder.append("Generated On: ").append(java.time.LocalDateTime.now()).append("\n\n");

        // Format headers
        pdfContentBuilder.append(String.join(" | ", headers)).append("\n");
        // Add a separator line
        pdfContentBuilder.append("-".repeat(headers.stream().mapToInt(String::length).sum() + (headers.size() - 1) * 3)).append("\n");

        // Format data rows
        for (Map<String, Object> row : reportData) {
            StringJoiner sj = new StringJoiner(" | ");
            for (String header : headers) {
                Object value = row.getOrDefault(header, "");
                sj.add(String.valueOf(value));
            }
            pdfContentBuilder.append(sj.toString()).append("\n");
        }

        // In a real application, this `pdfContentBuilder.toString()` would be passed
        // to a PDF library's API (e.g., iText's Document.add(new Paragraph(text)))
        // to generate the actual binary PDF content.
        // For this exercise, we return the byte representation of this text content.
        return pdfContentBuilder.toString().getBytes(StandardCharsets.UTF_8);
    }

    /**
     * Custom exception for report export failures.
     * This exception wraps underlying I/O or other exceptions during the export process,
     * providing a consistent error handling mechanism for the service layer.
     */
    public static class ReportExportException extends Exception {
        public ReportExportException(String message) {
            super(message);
        }

        public ReportExportException(String message, Throwable cause) {
            super(message, cause);
        }
    }
}
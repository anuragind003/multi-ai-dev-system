package com.ltfs.cdp.reporting.service;

import com.opencsv.CSVWriter;
import org.apache.poi.ss.usermodel.*;
import org.apache.poi.xssf.usermodel.XSSFWorkbook;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

import com.itextpdf.kernel.colors.ColorConstants;
import com.itextpdf.kernel.pdf.PdfDocument;
import com.itextpdf.kernel.pdf.PdfWriter;
import com.itextpdf.layout.Document;
import com.itextpdf.layout.element.Cell;
import com.itextpdf.layout.element.Paragraph;
import com.itextpdf.layout.element.Table;
import com.itextpdf.layout.properties.UnitValue;

import java.io.FileWriter;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.LinkedHashSet;
import java.util.stream.Collectors;

/**
 * Service class responsible for managing the export of reports to various formats
 * such as CSV, Excel, and PDF, and handling their storage.
 * This class leverages OpenCSV for CSV exports, Apache POI for Excel exports,
 * and iText 7 for PDF exports.
 */
@Service
public class FileExportManager {

    private static final Logger logger = LoggerFactory.getLogger(FileExportManager.class);

    /**
     * Configurable base directory where exported reports will be stored.
     * Defaults to "./reports" if not specified in application properties.
     */
    @Value("${reporting.export.base-directory:./reports}")
    private String exportBaseDirectory;

    /**
     * Enum to define supported report export formats.
     */
    public enum ExportFormat {
        CSV,
        EXCEL,
        PDF
    }

    /**
     * Exports the given data to a file in the specified format.
     * This method acts as a dispatcher, calling the appropriate private export method
     * based on the requested format. It also ensures the export directory exists.
     *
     * @param data The list of maps, where each map represents a row and keys are column headers.
     *             The order of columns in the output file will be determined by the order
     *             in which keys first appear across all maps.
     * @param filename The desired name of the output file (without extension).
     * @param format The desired export format (CSV, EXCEL, PDF).
     * @return The Path to the generated file.
     * @throws IOException If an I/O error occurs during file creation or writing.
     * @throws IllegalArgumentException If data, filename, or format is null/empty,
     *                                  or if an unsupported export format is requested.
     */
    public Path exportReport(List<Map<String, Object>> data, String filename, ExportFormat format) throws IOException {
        if (data == null || data.isEmpty()) {
            throw new IllegalArgumentException("Data for export cannot be null or empty.");
        }
        if (filename == null || filename.trim().isEmpty()) {
            throw new IllegalArgumentException("Filename cannot be null or empty.");
        }
        if (format == null) {
            throw new IllegalArgumentException("Export format cannot be null.");
        }

        // Ensure the base directory exists before attempting to write files
        Path baseDirPath = Paths.get(exportBaseDirectory);
        if (!Files.exists(baseDirPath)) {
            Files.createDirectories(baseDirPath);
            logger.info("Created export base directory: {}", baseDirPath.toAbsolutePath());
        }

        Path filePath;
        switch (format) {
            case CSV:
                filePath = Paths.get(exportBaseDirectory, filename + ".csv");
                exportToCsv(data, filePath);
                break;
            case EXCEL:
                filePath = Paths.get(exportBaseDirectory, filename + ".xlsx");
                exportToExcel(data, filePath);
                break;
            case PDF:
                filePath = Paths.get(exportBaseDirectory, filename + ".pdf");
                exportToPdf(data, filePath);
                break;
            default:
                // This case should ideally not be reached if the enum is exhaustive,
                // but serves as a safeguard for future format additions.
                throw new IllegalArgumentException("Unsupported export format: " + format);
        }
        logger.info("Report successfully exported to {} at {}", format, filePath.toAbsolutePath());
        return filePath;
    }

    /**
     * Exports the given data to a CSV file using OpenCSV library.
     * It dynamically determines column headers from the data.
     *
     * @param data The list of maps, where each map represents a row and keys are column headers.
     * @param filePath The full path to the output CSV file.
     * @throws IOException If an I/O error occurs during file writing.
     */
    private void exportToCsv(List<Map<String, Object>> data, Path filePath) throws IOException {
        // Determine all unique headers from the data.
        // LinkedHashSet is used to maintain the insertion order of headers,
        // ensuring consistent column order in the output CSV.
        Set<String> headers = data.stream()
                .flatMap(map -> map.keySet().stream())
                .collect(Collectors.toCollection(LinkedHashSet::new));

        try (CSVWriter writer = new CSVWriter(new FileWriter(filePath.toFile()))) {
            // Write headers as the first row in the CSV
            writer.writeNext(headers.toArray(new String[0]));

            // Write data rows
            for (Map<String, Object> row : data) {
                // For each row, retrieve values based on the determined header order.
                // If a header is missing in a specific row, an empty string is used.
                String[] rowData = headers.stream()
                        .map(header -> {
                            Object value = row.get(header);
                            return value != null ? value.toString() : "";
                        })
                        .toArray(String[]::new);
                writer.writeNext(rowData);
            }
        } catch (IOException e) {
            logger.error("Error exporting data to CSV file {}: {}", filePath, e.getMessage());
            // Re-throw as a more specific exception or wrap for higher-level handling
            throw new IOException("Failed to export data to CSV.", e);
        }
    }

    /**
     * Exports the given data to an Excel (XLSX) file using Apache POI library.
     * It dynamically determines column headers and attempts to set cell values
     * based on their data type (String, Number, Boolean).
     *
     * @param data The list of maps, where each map represents a row and keys are column headers.
     * @param filePath The full path to the output Excel file.
     * @throws IOException If an I/O error occurs during file writing.
     */
    private void exportToExcel(List<Map<String, Object>> data, Path filePath) throws IOException {
        // Determine all unique headers from the data.
        // LinkedHashSet is used to maintain the insertion order of headers,
        // ensuring consistent column order in the output Excel sheet.
        Set<String> headers = data.stream()
                .flatMap(map -> map.keySet().stream())
                .collect(Collectors.toCollection(LinkedHashSet::new));

        try (Workbook workbook = new XSSFWorkbook()) { // Use XSSFWorkbook for .xlsx format
            Sheet sheet = workbook.createSheet("Report Data");

            // Create header row at the top of the sheet
            Row headerRow = sheet.createRow(0);
            int colNum = 0;
            for (String header : headers) {
                org.apache.poi.ss.usermodel.Cell cell = headerRow.createCell(colNum++);
                cell.setCellValue(header);
            }

            // Create data rows starting from the second row (index 1)
            int rowNum = 1;
            for (Map<String, Object> rowDataMap : data) {
                Row row = sheet.createRow(rowNum++);
                colNum = 0;
                for (String header : headers) {
                    org.apache.poi.ss.usermodel.Cell cell = row.createCell(colNum++);
                    Object value = rowDataMap.get(header);
                    if (value != null) {
                        // Set cell value based on the type of the object for proper Excel formatting
                        if (value instanceof String) {
                            cell.setCellValue((String) value);
                        } else if (value instanceof Number) {
                            cell.setCellValue(((Number) value).doubleValue());
                        } else if (value instanceof Boolean) {
                            cell.setCellValue((Boolean) value);
                        } else {
                            cell.setCellValue(value.toString()); // Fallback for other types
                        }
                    } else {
                        cell.setCellValue(""); // Empty string for null values
                    }
                }
            }

            // Auto-size columns for better readability.
            // This can be performance intensive for very large datasets.
            for (int i = 0; i < headers.size(); i++) {
                sheet.autoSizeColumn(i);
            }

            // Write the workbook content to the specified file path
            workbook.write(Files.newOutputStream(filePath));

        } catch (IOException e) {
            logger.error("Error exporting data to Excel file {}: {}", filePath, e.getMessage());
            throw new IOException("Failed to export data to Excel.", e);
        }
    }

    /**
     * Exports the given data to a PDF file using iText 7 library.
     * This implementation generates a basic PDF document with a title, generation date,
     * and a table containing the report data. For advanced layouts, styling, or complex
     * content, more extensive iText API usage or a dedicated PDF templating engine
     * (e.g., JasperReports) would be required.
     *
     * @param data The list of maps, where each map represents a row and keys are column headers.
     * @param filePath The full path to the output PDF file.
     * @throws IOException If an I/O error occurs during file writing.
     */
    private void exportToPdf(List<Map<String, Object>> data, Path filePath) throws IOException {
        try (PdfWriter writer = new PdfWriter(filePath.toFile());
             PdfDocument pdf = new PdfDocument(writer);
             Document document = new Document(pdf)) {

            // Add a title and generation date to the PDF document
            document.add(new Paragraph("Report Data").setBold().setFontSize(18));
            document.add(new Paragraph("Generated on: " + java.time.LocalDate.now()).setFontSize(10));
            document.add(new Paragraph("\n")); // Add some vertical space

            // Determine all unique headers from the data.
            // LinkedHashSet is used to maintain the insertion order of headers,
            // ensuring consistent column order in the PDF table.
            Set<String> headers = data.stream()
                    .flatMap(map -> map.keySet().stream())
                    .collect(Collectors.toCollection(LinkedHashSet::new));

            // Create a table with a dynamic number of columns based on the headers.
            // UnitValue.createPercentArray(headers.size()) makes columns equally wide.
            Table table = new Table(UnitValue.createPercentArray(headers.size())).useAllAvailableWidth();

            // Add headers to the table
            for (String header : headers) {
                table.addHeaderCell(new Cell().add(new Paragraph(header).setBold()).setBackgroundColor(ColorConstants.LIGHT_GRAY));
            }

            // Add data rows to the table
            for (Map<String, Object> rowDataMap : data) {
                for (String header : headers) {
                    Object value = rowDataMap.get(header);
                    // Add cell with value, or empty string if null
                    table.addCell(new Cell().add(new Paragraph(value != null ? value.toString() : "")));
                }
            }
            document.add(table); // Add the completed table to the document

        } catch (IOException e) {
            logger.error("Error exporting data to PDF file {}: {}", filePath, e.getMessage());
            throw new IOException("Failed to export data to PDF.", e);
        }
    }
}
package com.ltfs.cdp.reporting.export;

import com.ltfs.cdp.reporting.exception.ReportExportException;
import com.ltfs.cdp.reporting.export.enums.ExportFormat;
import com.ltfs.cdp.reporting.export.strategy.ReportExporter;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import java.io.IOException;
import java.io.OutputStream;
import java.util.List;
import java.util.Map;
import java.util.function.Function;
import java.util.stream.Collectors;

/**
 * Manages the export of generated reports into various file formats (e.g., CSV, Excel, PDF).
 * This service acts as a facade, delegating the actual export logic to specific
 * {@link ReportExporter} implementations based on the requested format.
 */
@Service
public class FileExportManager {

    private static final Logger log = LoggerFactory.getLogger(FileExportManager.class);

    /**
     * A map holding different report exporters, keyed by their respective {@link ExportFormat}.
     * This allows for dynamic selection of the correct exporter at runtime.
     */
    private final Map<ExportFormat, ReportExporter> exporterMap;

    /**
     * Constructs a new FileExportManager.
     * Spring automatically injects all beans that implement the {@link ReportExporter} interface.
     * These are then collected into a map for easy lookup.
     *
     * @param exporters A list of all available {@link ReportExporter} implementations.
     */
    @Autowired
    public FileExportManager(List<ReportExporter> exporters) {
        this.exporterMap = exporters.stream()
                .collect(Collectors.toMap(ReportExporter::getFormat, Function.identity()));
        log.info("Initialized FileExportManager with {} exporters: {}", exporters.size(), exporterMap.keySet());
    }

    /**
     * Exports the given report data to the specified output stream in the desired format.
     *
     * @param data The list of maps, where each map represents a row and its keys are column names.
     *             Example: `[{"id": 1, "name": "John"}, {"id": 2, "name": "Jane"}]`
     * @param headers The ordered list of column headers. This is crucial for maintaining column order
     *                in formats like CSV and Excel, as map keys do not guarantee order.
     *                Example: `["id", "name"]`
     * @param format The desired {@link ExportFormat} (e.g., CSV, EXCEL, PDF).
     * @param outputStream The {@link OutputStream} to which the exported data will be written.
     *                     This could be a `FileOutputStream`, `ByteArrayOutputStream`, or a `ServletOutputStream`.
     * @param reportName A descriptive name for the report, useful for logging or potential file naming.
     * @throws ReportExportException if an error occurs during the export process or if the format is not supported.
     */
    public void exportReport(List<Map<String, Object>> data, List<String> headers,
                             ExportFormat format, OutputStream outputStream, String reportName) {
        log.info("Attempting to export report '{}' in {} format. Data rows: {}", reportName, format, data.size());

        ReportExporter exporter = exporterMap.get(format);

        if (exporter == null) {
            log.error("No exporter found for format: {}", format);
            throw new ReportExportException("Unsupported export format: " + format);
        }

        try {
            exporter.export(data, headers, outputStream);
            log.info("Successfully exported report '{}' in {} format.", reportName, format);
        } catch (IOException e) {
            log.error("Failed to export report '{}' in {} format due to an I/O error: {}", reportName, format, e.getMessage(), e);
            throw new ReportExportException("Failed to export report '" + reportName + "' to " + format + " format.", e);
        } catch (Exception e) {
            log.error("An unexpected error occurred while exporting report '{}' in {} format: {}", reportName, format, e.getMessage(), e);
            throw new ReportExportException("An unexpected error occurred during export of report '" + reportName + "' to " + format + " format.", e);
        }
    }
}

// --- Supporting Interfaces and Enums (typically in separate files, but included here for completeness) ---

/**
 * Defines the contract for report exporters.
 * Each implementation will handle a specific export format.
 */
// package com.ltfs.cdp.reporting.export.strategy;
interface ReportExporter {
    /**
     * Returns the {@link ExportFormat} that this exporter handles.
     * @return The export format.
     */
    ExportFormat getFormat();

    /**
     * Exports the given report data to the specified output stream.
     *
     * @param data The list of maps, where each map represents a row and its keys are column names.
     * @param headers The ordered list of column headers.
     * @param outputStream The {@link OutputStream} to which the exported data will be written.
     * @throws IOException If an I/O error occurs during the export process.
     */
    void export(List<Map<String, Object>> data, List<String> headers, OutputStream outputStream) throws IOException;
}

/**
 * Enumeration of supported report export formats.
 */
// package com.ltfs.cdp.reporting.export.enums;
enum ExportFormat {
    CSV,
    EXCEL,
    PDF
}

/**
 * Custom runtime exception for report export failures.
 */
// package com.ltfs.cdp.reporting.exception;
class ReportExportException extends RuntimeException {
    public ReportExportException(String message) {
        super(message);
    }

    public ReportExportException(String message, Throwable cause) {
        super(message, cause);
    }
}

// --- Example Implementations of ReportExporter (would be in separate files) ---

// package com.ltfs.cdp.reporting.export.strategy.impl;
// import com.ltfs.cdp.reporting.export.enums.ExportFormat;
// import com.ltfs.cdp.reporting.export.strategy.ReportExporter;
// import org.springframework.stereotype.Component;
// import org.apache.commons.csv.CSVFormat;
// import org.apache.commons.csv.CSVPrinter;
// import java.io.BufferedWriter;
// import java.io.IOException;
// import java.io.OutputStream;
// import java.io.OutputStreamWriter;
// import java.util.List;
// import java.util.Map;

/*
@Component
class CsvExporter implements ReportExporter {

    private static final Logger log = LoggerFactory.getLogger(CsvExporter.class);

    @Override
    public ExportFormat getFormat() {
        return ExportFormat.CSV;
    }

    @Override
    public void export(List<Map<String, Object>> data, List<String> headers, OutputStream outputStream) throws IOException {
        log.debug("Exporting data to CSV format. Rows: {}, Headers: {}", data.size(), headers);
        try (BufferedWriter writer = new BufferedWriter(new OutputStreamWriter(outputStream));
             CSVPrinter csvPrinter = new CSVPrinter(writer, CSVFormat.DEFAULT.withHeader(headers.toArray(new String[0])))) {

            for (Map<String, Object> row : data) {
                Object[] record = headers.stream()
                        .map(row::get)
                        .toArray();
                csvPrinter.printRecord(record);
            }
            csvPrinter.flush();
            log.debug("CSV export completed successfully.");
        } catch (IOException e) {
            log.error("Error during CSV export: {}", e.getMessage(), e);
            throw e;
        }
    }
}
*/

// package com.ltfs.cdp.reporting.export.strategy.impl;
// import com.ltfs.cdp.reporting.export.enums.ExportFormat;
// import com.ltfs.cdp.reporting.export.strategy.ReportExporter;
// import org.springframework.stereotype.Component;
// import org.apache.poi.ss.usermodel.*;
// import org.apache.poi.xssf.usermodel.XSSFWorkbook;
// import java.io.IOException;
// import java.io.OutputStream;
// import java.util.List;
// import java.util.Map;

/*
@Component
class ExcelExporter implements ReportExporter {

    private static final Logger log = LoggerFactory.getLogger(ExcelExporter.class);

    @Override
    public ExportFormat getFormat() {
        return ExportFormat.EXCEL;
    }

    @Override
    public void export(List<Map<String, Object>> data, List<String> headers, OutputStream outputStream) throws IOException {
        log.debug("Exporting data to Excel format. Rows: {}, Headers: {}", data.size(), headers);
        try (Workbook workbook = new XSSFWorkbook()) {
            Sheet sheet = workbook.createSheet("Report");

            // Create header row
            Row headerRow = sheet.createRow(0);
            for (int i = 0; i < headers.size(); i++) {
                Cell cell = headerRow.createCell(i);
                cell.setCellValue(headers.get(i));
            }

            // Create data rows
            int rowNum = 1;
            for (Map<String, Object> rowData : data) {
                Row row = sheet.createRow(rowNum++);
                for (int i = 0; i < headers.size(); i++) {
                    Cell cell = row.createCell(i);
                    Object value = rowData.get(headers.get(i));
                    if (value != null) {
                        cell.setCellValue(value.toString()); // Simple string conversion for now
                    }
                }
            }

            workbook.write(outputStream);
            log.debug("Excel export completed successfully.");
        } catch (IOException e) {
            log.error("Error during Excel export: {}", e.getMessage(), e);
            throw e;
        }
    }
}
*/

// package com.ltfs.cdp.reporting.export.strategy.impl;
// import com.ltfs.cdp.reporting.export.enums.ExportFormat;
// import com.ltfs.cdp.reporting.export.strategy.ReportExporter;
// import org.springframework.stereotype.Component;
// import java.io.IOException;
// import java.io.OutputStream;
// import java.util.List;
// import java.util.Map;

/*
@Component
class PdfExporter implements ReportExporter {

    private static final Logger log = LoggerFactory.getLogger(PdfExporter.class);

    @Override
    public ExportFormat getFormat() {
        return ExportFormat.PDF;
    }

    @Override
    public void export(List<Map<String, Object>> data, List<String> headers, OutputStream outputStream) throws IOException {
        log.warn("PDF export is a complex feature and requires a dedicated library (e.g., iText, Apache PDFBox). " +
                 "This is a placeholder implementation.");
        // Placeholder: In a real scenario, you would use a PDF library here.
        // Example (conceptual, requires iText/PDFBox setup):
        // Document document = new Document();
        // PdfWriter.getInstance(document, outputStream);
        // document.open();
        // document.add(new Paragraph("Report Name"));
        // PdfPTable table = new PdfPTable(headers.size());
        // for (String header : headers) {
        //     table.addCell(header);
        // }
        // for (Map<String, Object> row : data) {
        //     for (String header : headers) {
        //         table.addCell(String.valueOf(row.getOrDefault(header, "")));
        //     }
        // }
        // document.add(table);
        // document.close();
        outputStream.write("PDF Export Not Fully Implemented Yet.".getBytes());
        log.debug("PDF export placeholder executed.");
    }
}
*/
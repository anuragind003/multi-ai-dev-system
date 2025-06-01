package com.ltfs.cdp.datavalidation.repository;

import com.ltfs.cdp.datavalidation.model.ErrorLog;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

/**
 * Repository interface for managing {@link ErrorLog} entities.
 * This interface extends {@link JpaRepository} to provide standard CRUD operations
 * and pagination/sorting capabilities for error log entries.
 *
 * <p>The {@code ErrorLogRepository} is responsible for persisting and retrieving
 * detailed data validation error logs from the PostgreSQL database.
 * It acts as a bridge between the service layer and the database for error log management.</p>
 *
 * <p>Usage:</p>
 * <pre>
 * {@code
 * @Autowired
 * private ErrorLogRepository errorLogRepository;
 *
 * public void logError(ErrorLog errorLog) {
 *     errorLogRepository.save(errorLog);
 * }
 *
 * public List<ErrorLog> getAllErrors() {
 *     return errorLogRepository.findAll();
 * }
 * }
 * </pre>
 */
@Repository
public interface ErrorLogRepository extends JpaRepository<ErrorLog, Long> {
    // JpaRepository provides common CRUD operations (save, findById, findAll, delete, etc.)
    // No custom methods are explicitly required based on the current context,
    // but they can be added here if specific query needs arise (e.g., findByValidationType, findByTimestampBetween).
}
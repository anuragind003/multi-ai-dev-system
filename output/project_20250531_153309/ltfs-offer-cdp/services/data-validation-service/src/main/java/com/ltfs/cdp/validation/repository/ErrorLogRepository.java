package com.ltfs.cdp.validation.repository;

import com.ltfs.cdp.validation.model.ErrorLog;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

/**
 * Repository interface for managing {@link ErrorLog} entities.
 * This interface extends Spring Data JPA's JpaRepository, providing standard
 * CRUD (Create, Read, Update, Delete) operations and pagination/sorting capabilities
 * for the ErrorLog entity.
 *
 * The ErrorLog entity is used to persist detailed logs of data validation errors
 * encountered during the data ingestion and processing within the LTFS Offer CDP system.
 *
 * The primary key type for the ErrorLog entity is assumed to be Long.
 *
 * @author LTFS Offer CDP Team
 * @version 1.0
 * @since 2025-05-29
 */
@Repository
public interface ErrorLogRepository extends JpaRepository<ErrorLog, Long> {
    // Spring Data JPA automatically provides implementations for standard CRUD operations
    // such as save(), findById(), findAll(), delete(), etc.
    // No custom methods are explicitly required based on the current request.

    // Example of a potential custom method (not required by current instructions, but for context):
    // List<ErrorLog> findByValidationBatchId(String validationBatchId);
    // List<ErrorLog> findByRecordIdentifierAndFieldName(String recordIdentifier, String fieldName);
}
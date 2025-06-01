package com.ltfs.cdp.customer.repository;

import com.ltfs.cdp.customer.entity.DeduplicationLog;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

/**
 * Repository interface for managing {@link DeduplicationLog} entities.
 * This interface extends {@link JpaRepository} to provide standard CRUD operations
 * and custom query capabilities for deduplication log records.
 *
 * <p>The deduplication log captures details about each deduplication event,
 * including the input customer data, the matched customer (if any),
 * the deduplication outcome, and timestamps. This is crucial for auditing,
 * debugging, and understanding the effectiveness of the deduplication process.</p>
 *
 * @author Code Generation Agent
 * @version 1.0
 * @since 2025-05-31
 */
@Repository
public interface DeduplicationLogRepository extends JpaRepository<DeduplicationLog, Long> {

    // No custom methods are explicitly required based on the prompt,
    // as JpaRepository provides common operations like save, findById, findAll, etc.
    // Custom queries can be added here if specific search criteria are needed,
    // e.g., findByCustomerId, findByOutcome, findByTimestampBetween.

    /**
     * Example of a potential custom query method (uncomment if needed):
     * <pre>{@code
     * List<DeduplicationLog> findByInputCustomerId(String inputCustomerId);
     * }</pre>
     * This method would retrieve all deduplication logs associated with a specific input customer ID.
     */

    /**
     * Example of another potential custom query method (uncomment if needed):
     * <pre>{@code
     * List<DeduplicationLog> findByDeduplicationOutcome(DeduplicationOutcome outcome);
     * }</pre>
     * This method would retrieve all deduplication logs based on their outcome (e.g., MATCHED, NO_MATCH, REMOVED).
     * (Assumes DeduplicationOutcome is an enum or String field in DeduplicationLog entity)
     */
}
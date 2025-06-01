package com.ltfs.cdp.customer.dedupe;

// Assuming the Customer entity/DTO resides in a common model package within the customer-service.
// This import is crucial for the 'apply' method's signature.
// If the Customer class is located elsewhere or has a different name, this import path will need adjustment.
import com.ltfs.cdp.customer.model.Customer;

/**
 * <p>Interface defining a contract for individual deduplication rules within the Customer Data Platform (CDP).</p>
 *
 * <p>Each implementation of this interface represents a specific criterion or logic used to identify
 * potential duplicate customer profiles. These rules are fundamental to achieving a single, unified
 * view of the customer, aligning with the project's goal of providing a comprehensive customer 360 profile
 * and performing robust deduplication against the 'live book'.</p>
 *
 * <p>Deduplication rules can vary in complexity, from simple exact matches on unique identifiers
 * to more sophisticated fuzzy matching or composite rules involving multiple data points.</p>
 *
 * <p>Examples of deduplication rules could include:</p>
 * <ul>
 *     <li>Matching by exact Permanent Account Number (PAN)</li>
 *     <li>Matching by exact Aadhaar number</li>
 *     <li>Matching by a combination of Name, Date of Birth, and Mobile Number (with potential fuzzy logic)</li>
 *     <li>Product-specific matching, e.g., for Top-up loan offers, ensuring deduplication only within other Top-up offers.</li>
 * </ul>
 *
 * <p>Implementations of this interface should ideally be stateless and thread-safe, as they might be
 * invoked concurrently across various customer records during batch processing or real-time ingestion.</p>
 */
public interface DedupeRule {

    /**
     * Applies this specific deduplication rule to two customer profiles to determine if they are a match.
     * This method encapsulates the core logic for a particular deduplication criterion.
     *
     * @param customer1 The first customer profile object, containing all relevant data points
     *                  (e.g., PAN, Aadhaar, Name, DOB, Mobile, Product Type) required by this rule.
     *                  It is expected that this object is not null and contains valid data.
     * @param customer2 The second customer profile object, to be compared against the first.
     *                  It is expected that this object is not null and contains valid data.
     * @return {@code true} if the two customer profiles are considered a match according to the logic
     *         defined by this rule; {@code false} otherwise.
     *         Implementations should handle cases where required data fields are missing or null
     *         gracefully, typically by returning {@code false} if a definitive match cannot be determined.
     */
    boolean apply(Customer customer1, Customer customer2);

    /**
     * Returns a unique identifier or a descriptive name for this deduplication rule.
     * This name is crucial for logging, auditing, configuration, and for identifying
     * which specific rule(s) contributed to a deduplication decision.
     *
     * @return A non-null, unique string representing the name of the deduplication rule.
     *         Examples: "PAN_MATCH_RULE", "AADHAAR_MATCH_RULE", "NAME_DOB_MOBILE_FUZZY_MATCH_RULE".
     */
    String getRuleName();

    /**
     * Returns the priority level of this deduplication rule.
     * In a system where multiple rules are applied, priority can be used to:
     * <ul>
     *     <li>Order the execution of rules (e.g., higher priority rules evaluated first).</li>
     *     <li>Weight the contribution of a rule's outcome to a composite deduplication score.</li>
     *     <li>Determine the confidence level of a match (e.g., a PAN match might have higher priority/confidence than a name match).</li>
     * </ul>
     *
     * @return An integer representing the priority of the rule. Higher integer values typically
     *         indicate higher priority or a stronger matching criterion.
     */
    int getPriority();
}
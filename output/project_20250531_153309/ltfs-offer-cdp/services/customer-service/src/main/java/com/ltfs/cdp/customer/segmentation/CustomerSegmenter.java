package com.ltfs.cdp.customer.segmentation;

import org.springframework.stereotype.Service;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.math.BigDecimal;
import java.util.Collections;
import java.util.HashSet;
import java.util.Set;

/**
 * Service component responsible for assigning customers to specific segments
 * based on their attributes and predefined business rules.
 * This class applies segmentation logic to a given customer profile,
 * enabling targeted offer generation and customer relationship management.
 *
 * <p>Segmentation rules are currently hardcoded for demonstration purposes.
 * In a production environment, these rules would typically be managed externally
 * (e.g., loaded from a database, configuration service, or a dedicated rule engine)
 * to allow for dynamic updates without code changes.</p>
 */
@Service
public class CustomerSegmenter {

    private static final Logger logger = LoggerFactory.getLogger(CustomerSegmenter.class);

    // --- Segmentation Rule Thresholds ---
    // These constants define the criteria for various customer segments.
    // They would ideally be configurable parameters in a real-world application
    // (e.g., via Spring @Value, a configuration service, or a database table).
    private static final BigDecimal HIGH_VALUE_INCOME_THRESHOLD = new BigDecimal("1000000"); // Example: 10 Lakhs INR
    private static final int HIGH_VALUE_LOAN_COUNT_THRESHOLD = 3;
    private static final int LOYAL_CUSTOMER_SCORE_THRESHOLD = 80; // Example: out of 100
    private static final int LOYAL_CUSTOMER_LOAN_COUNT_THRESHOLD = 2;
    private static final int NEW_CUSTOMER_LOAN_COUNT_THRESHOLD = 0; // Customers with 0 loans
    private static final int YOUNG_AGE_UPPER_THRESHOLD = 30;
    private static final int SENIOR_AGE_LOWER_THRESHOLD = 60;


    /**
     * Segments a given customer based on their attributes.
     * The method applies a set of predefined business rules to determine which segments
     * a customer belongs to. A customer can potentially belong to multiple segments
     * if they meet the criteria for more than one rule.
     *
     * @param customer The customer object containing various attributes like age, income, loan history, etc.
     *                 This object is expected to be a consolidated view of the customer profile
     *                 after deduplication, as per project requirements.
     * @return A {@link Set} of {@link String}s, where each String represents a segment name
     *         the customer belongs to. Returns an unmodifiable empty set if the input customer is null.
     *         If no specific rules match, the customer is assigned to a "General Customer" segment.
     */
    public Set<String> segmentCustomer(Customer customer) {
        if (customer == null) {
            logger.warn("Attempted to segment a null customer. Returning an empty set of segments.");
            return Collections.emptySet();
        }

        Set<String> segments = new HashSet<>();
        logger.debug("Starting segmentation process for customer ID: {}", customer.getCustomerId());

        // Rule 1: High-Value Customer
        // Criteria: High annual income AND a significant number of loans taken.
        // This segment targets customers who contribute significantly to revenue.
        if (customer.getAnnualIncome() != null &&
            customer.getAnnualIncome().compareTo(HIGH_VALUE_INCOME_THRESHOLD) >= 0 &&
            customer.getLoanCount() != null &&
            customer.getLoanCount() >= HIGH_VALUE_LOAN_COUNT_THRESHOLD) {
            segments.add("High-Value Customer");
            logger.debug("Customer {} identified as 'High-Value Customer'.", customer.getCustomerId());
        }

        // Rule 2: Loyal Customer
        // Criteria: High loyalty score AND a good number of past loans.
        // This segment identifies customers who have a strong, ongoing relationship with LTFS.
        if (customer.getLoyaltyScore() != null &&
            customer.getLoyaltyScore() >= LOYAL_CUSTOMER_SCORE_THRESHOLD &&
            customer.getLoanCount() != null &&
            customer.getLoanCount() >= LOYAL_CUSTOMER_LOAN_COUNT_THRESHOLD) {
            segments.add("Loyal Customer");
            logger.debug("Customer {} identified as 'Loyal Customer'.", customer.getCustomerId());
        }

        // Rule 3: New Customer
        // Criteria: No previous loans recorded.
        // This segment is crucial for onboarding and initial offer strategies.
        if (customer.getLoanCount() != null && customer.getLoanCount() <= NEW_CUSTOMER_LOAN_COUNT_THRESHOLD) {
            segments.add("New Customer");
            logger.debug("Customer {} identified as 'New Customer'.", customer.getCustomerId());
        }

        // Rule 4: Young Professional
        // Criteria: Age within a typical young professional range.
        // Useful for targeting specific product types or communication styles.
        if (customer.getAge() != null && customer.getAge() > 0 && customer.getAge() <= YOUNG_AGE_UPPER_THRESHOLD) {
            segments.add("Young Professional");
            logger.debug("Customer {} identified as 'Young Professional'.", customer.getCustomerId());
        }

        // Rule 5: Senior Citizen Segment
        // Criteria: Age above a certain threshold.
        // May require different product offerings or support.
        if (customer.getAge() != null && customer.getAge() >= SENIOR_AGE_LOWER_THRESHOLD) {
            segments.add("Senior Citizen");
            logger.debug("Customer {} identified as 'Senior Citizen'.", customer.getCustomerId());
        }

        // Rule 6: Active Loan Holder
        // Criteria: Currently has an active loan with LTFS.
        // Important for top-up offers, cross-selling, or retention strategies.
        if (customer.getHasActiveLoan() != null && customer.getHasActiveLoan()) {
            segments.add("Active Loan Holder");
            logger.debug("Customer {} identified as 'Active Loan Holder'.", customer.getCustomerId());
        }

        // Default Segment: If no specific rules match, assign to a general category.
        if (segments.isEmpty()) {
            segments.add("General Customer");
            logger.debug("Customer {} identified as 'General Customer' (no specific segments matched).", customer.getCustomerId());
        }

        logger.info("Customer {} segmented into: {}", customer.getCustomerId(), segments);
        return segments;
    }

    /**
     * Placeholder for the Customer DTO/Entity.
     * In a real project, this class would be defined in a separate file,
     * typically in `com.ltfs.cdp.customer.model.Customer`.
     * It is included here to make the `CustomerSegmenter` class directly runnable
     * and self-contained for this code generation task.
     */
    public static class Customer {
        private String customerId;
        private Integer age;
        private BigDecimal annualIncome;
        private Integer loanCount;
        private Integer loyaltyScore; // e.g., 0-100
        private Boolean hasActiveLoan;

        /**
         * Constructs a new Customer instance.
         *
         * @param customerId Unique identifier for the customer.
         * @param age The customer's age.
         * @param annualIncome The customer's annual income.
         * @param loanCount The total number of loans the customer has taken.
         * @param loyaltyScore A score indicating customer loyalty (e.g., 0-100).
         * @param hasActiveLoan A boolean indicating if the customer currently has an active loan.
         */
        public Customer(String customerId, Integer age, BigDecimal annualIncome, Integer loanCount, Integer loyaltyScore, Boolean hasActiveLoan) {
            this.customerId = customerId;
            this.age = age;
            this.annualIncome = annualIncome;
            this.loanCount = loanCount;
            this.loyaltyScore = loyaltyScore;
            this.hasActiveLoan = hasActiveLoan;
        }

        // --- Getters for Customer attributes ---
        public String getCustomerId() { return customerId; }
        public Integer getAge() { return age; }
        public BigDecimal getAnnualIncome() { return annualIncome; }
        public Integer getLoanCount() { return loanCount; }
        public Integer getLoyaltyScore() { return loyaltyScore; }
        public Boolean getHasActiveLoan() { return hasActiveLoan; }

        // --- Setters for Customer attributes (optional, depending on immutability strategy) ---
        // These setters are provided for completeness but might not be used if Customer objects are immutable DTOs.
        public void setCustomerId(String customerId) { this.customerId = customerId; }
        public void setAge(Integer age) { this.age = age; }
        public void setAnnualIncome(BigDecimal annualIncome) { this.annualIncome = annualIncome; }
        public void setLoanCount(Integer loanCount) { this.loanCount = loanCount; }
        public void setLoyaltyScore(Integer loyaltyScore) { this.loyaltyScore = loyaltyScore; }
        public void setHasActiveLoan(Boolean hasActiveLoan) { this.hasActiveLoan = hasActiveLoan; }

        @Override
        public String toString() {
            return "Customer{" +
                   "customerId='" + customerId + '\'' +
                   ", age=" + age +
                   ", annualIncome=" + annualIncome +
                   ", loanCount=" + loanCount +
                   ", loyaltyScore=" + loyaltyScore +
                   ", hasActiveLoan=" + hasActiveLoan +
                   '}';
        }
    }
}
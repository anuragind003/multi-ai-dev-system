package com.ltfs.cdp.customer.service;

import org.springframework.stereotype.Service;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;
import java.util.Optional;
import java.util.stream.Collectors;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 * Service class responsible for managing customer attributes and applying segmentation logic.
 * It interacts with the CustomerRepository to fetch and update customer data,
 * and applies predefined or dynamically loaded segmentation rules to assign customers to segments.
 */
@Service
public class CustomerSegmentationService {

    private static final Logger log = LoggerFactory.getLogger(CustomerSegmentationService.class);

    private final CustomerRepository customerRepository;

    /**
     * Constructs a new CustomerSegmentationService with the given CustomerRepository.
     *
     * @param customerRepository The repository for accessing customer data.
     */
    @Autowired
    public CustomerSegmentationService(CustomerRepository customerRepository) {
        this.customerRepository = customerRepository;
    }

    /**
     * Applies segmentation logic to a single customer identified by their ID.
     * The customer's segment attribute is updated based on the defined rules and then saved to the database.
     * This operation is transactional to ensure data consistency.
     *
     * @param customerId The unique identifier of the customer to segment.
     * @return The updated Customer object with the assigned segment.
     * @throws CustomerNotFoundException if no customer is found with the given ID.
     */
    @Transactional
    public Customer applySegmentationToCustomer(String customerId) {
        log.info("Attempting to apply segmentation for customer ID: {}", customerId);
        return customerRepository.findByCustomerId(customerId)
                .map(this::applySegmentationLogic) // Apply segmentation rules
                .map(customerRepository::save)     // Save the updated customer
                .orElseThrow(() -> {
                    log.error("Customer not found with ID: {}", customerId);
                    return new CustomerNotFoundException("Customer not found with ID: " + customerId);
                });
    }

    /**
     * Applies segmentation logic to a list of customers.
     * This method is designed for batch processing, allowing efficient segmentation of multiple customers,
     * for example, during nightly jobs or event-driven updates.
     * All updates are saved in a single transaction.
     *
     * @param customers A list of Customer objects to be segmented.
     * @return A list of updated Customer objects with their assigned segments.
     */
    @Transactional
    public List<Customer> applySegmentationToCustomers(List<Customer> customers) {
        log.info("Applying segmentation to a batch of {} customers.", customers.size());
        List<Customer> segmentedCustomers = customers.stream()
                .map(this::applySegmentationLogic) // Apply segmentation logic to each customer
                .collect(Collectors.toList());
        // Save all segmented customers in a batch for performance optimization
        return customerRepository.saveAll(segmentedCustomers);
    }

    /**
     * Internal method to encapsulate the core business logic for customer segmentation.
     * It iterates through a set of active segmentation rules and assigns the first matching segment
     * to the customer. Rules are applied in a predefined order (e.g., by priority).
     *
     * @param customer The Customer object whose segment needs to be determined.
     * @return The Customer object with its segment attribute updated.
     */
    private Customer applySegmentationLogic(Customer customer) {
        // In a production system, segmentation rules would typically be loaded from a database,
        // a configuration service, or a dedicated rule engine (e.g., Drools).
        // For this example, rules are mocked.
        List<SegmentationRule> activeRules = getActiveSegmentationRules();

        CustomerSegment assignedSegment = CustomerSegment.MASS_MARKET; // Default segment if no rules match

        for (SegmentationRule rule : activeRules) {
            if (evaluateRule(customer, rule)) {
                assignedSegment = rule.getTargetSegment();
                log.debug("Customer {} (ID: {}) matched rule '{}' for segment: {}",
                          customer.getName(), customer.getCustomerId(), rule.getRuleName(), assignedSegment);
                break; // Apply the first matching rule (assuming rules are ordered by priority)
            }
        }

        customer.setSegment(assignedSegment);
        log.debug("Customer {} (ID: {}) finally assigned to segment: {}",
                  customer.getName(), customer.getCustomerId(), assignedSegment);
        return customer;
    }

    /**
     * Evaluates a single segmentation rule against a customer's attributes.
     * This method contains the logic to interpret various rule conditions (e.g., age, income).
     * Additional conditions (e.g., product holdings, credit score, location) can be added here.
     *
     * @param customer The customer object to evaluate against the rule.
     * @param rule The segmentation rule to apply.
     * @return true if the customer satisfies all conditions of the rule, false otherwise.
     */
    private boolean evaluateRule(Customer customer, SegmentationRule rule) {
        // Start with true, and set to false if any condition is not met
        boolean matches = true;

        // Evaluate age criteria
        if (rule.getMinAge() != null && customer.getAge() < rule.getMinAge()) {
            matches = false;
        }
        if (matches && rule.getMaxAge() != null && customer.getAge() > rule.getMaxAge()) {
            matches = false;
        }

        // Evaluate income criteria
        if (matches && rule.getMinIncome() != null && customer.getIncome() < rule.getMinIncome()) {
            matches = false;
        }
        if (matches && rule.getMaxIncome() != null && customer.getIncome() > rule.getMaxIncome()) {
            matches = false;
        }

        // Add more complex rule evaluations here as per business requirements.
        // Example: Check product holdings
        // if (matches && rule.getRequiredProduct() != null && !customer.getProductHoldings().contains(rule.getRequiredProduct())) {
        //     matches = false;
        // }

        return matches;
    }

    /**
     * Mocks the retrieval of active segmentation rules.
     * In a real-world application, these rules would be persisted in a database
     * and fetched via a dedicated repository (e.g., `SegmentationRuleRepository`).
     * Rules should ideally be ordered by priority, so the most specific or highest-priority
     * rules are evaluated first.
     *
     * @return A list of active segmentation rules.
     */
    private List<SegmentationRule> getActiveSegmentationRules() {
        // This is a placeholder for fetching rules from a persistent store.
        // Example: return segmentationRuleRepository.findAllByActiveTrueOrderByPriorityAsc();

        // Mocked rules for demonstration purposes.
        // Order matters: more specific rules should come first if there's an overlap.
        return List.of(
                // Rule 1: High Net Worth (Income >= 1,000,000 AND Age >= 30)
                new SegmentationRule("High Net Worth", CustomerSegment.HIGH_NET_WORTH, 1000000.0, null, 30, null),
                // Rule 2: Young Professional (Income >= 500,000 AND Income < 1,000,000 AND Age <= 30)
                new SegmentationRule("Young Professional", CustomerSegment.YOUNG_PROFESSIONAL, 500000.0, 999999.99, null, 30),
                // Rule 3: Affluent (Income >= 750,000) - broader, placed after more specific rules
                new SegmentationRule("Affluent", CustomerSegment.AFFLUENT, 750000.0, null, null, null)
        );
    }

    // --- Mock DTOs/Entities and Interfaces for compilation within a single file ---
    // In a real project, these would reside in their respective packages (e.g., model, repository, exception).

    /**
     * Mock Customer DTO/Entity representing a customer profile.
     * In a real application, this would be a JPA entity or a dedicated DTO.
     */
    public static class Customer {
        private String customerId;
        private String name;
        private int age;
        private double income;
        private CustomerSegment segment;
        // private List<String> productHoldings; // Example of additional customer attributes

        public Customer(String customerId, String name, int age, double income) {
            this.customerId = customerId;
            this.name = name;
            this.age = age;
            this.income = income;
            this.segment = CustomerSegment.MASS_MARKET; // Default segment upon creation
        }

        // Getters and Setters
        public String getCustomerId() { return customerId; }
        public void setCustomerId(String customerId) { this.customerId = customerId; }
        public String getName() { return name; }
        public void setName(String name) { this.name = name; }
        public int getAge() { return age; }
        public void setAge(int age) { this.age = age; }
        public double getIncome() { return income; }
        public void setIncome(double income) { this.income = income; }
        public CustomerSegment getSegment() { return segment; }
        public void setSegment(CustomerSegment segment) { this.segment = segment; }
        // public List<String> getProductHoldings() { return productHoldings; }
        // public void setProductHoldings(List<String> productHoldings) { this.productHoldings = productHoldings; }
    }

    /**
     * Mock Enum representing different customer segments.
     */
    public enum CustomerSegment {
        HIGH_NET_WORTH,
        YOUNG_PROFESSIONAL,
        AFFLUENT,
        MASS_MARKET,
        // Add more segments as per business requirements
    }

    /**
     * Mock DTO/Entity representing a segmentation rule.
     * In a real application, this would be a JPA entity or a dedicated DTO,
     * potentially with more complex rule definitions (e.g., using a rule expression language).
     */
    public static class SegmentationRule {
        private String ruleName;
        private CustomerSegment targetSegment;
        private Double minIncome;
        private Double maxIncome;
        private Integer minAge;
        private Integer maxAge;
        // private String requiredProduct; // Example of additional rule criteria

        public SegmentationRule(String ruleName, CustomerSegment targetSegment, Double minIncome, Double maxIncome, Integer minAge, Integer maxAge) {
            this.ruleName = ruleName;
            this.targetSegment = targetSegment;
            this.minIncome = minIncome;
            this.maxIncome = maxIncome;
            this.minAge = minAge;
            this.maxAge = maxAge;
        }

        // Getters
        public String getRuleName() { return ruleName; }
        public CustomerSegment getTargetSegment() { return targetSegment; }
        public Double getMinIncome() { return minIncome; }
        public Double getMaxIncome() { return maxIncome; }
        public Integer getMinAge() { return minAge; }
        public Integer getMaxAge() { return maxAge; }
        // public String getRequiredProduct() { return requiredProduct; }
    }

    /**
     * Mock CustomerRepository interface.
     * In a real Spring Boot application, this would extend JpaRepository or a similar Spring Data interface.
     */
    public interface CustomerRepository {
        /**
         * Finds a customer by their unique customer ID.
         * @param customerId The ID of the customer to find.
         * @return An Optional containing the Customer if found, or empty otherwise.
         */
        Optional<Customer> findByCustomerId(String customerId);

        /**
         * Saves a single customer entity to the database.
         * @param customer The customer to save.
         * @return The saved customer entity.
         */
        Customer save(Customer customer);

        /**
         * Saves all given customer entities in a batch.
         * @param customers The list of customers to save.
         * @return The list of saved customer entities.
         */
        List<Customer> saveAll(List<Customer> customers);
        // Other CRUD methods would typically be defined here (e.g., findAll, delete, etc.)
    }

    /**
     * Custom exception for when a customer is not found.
     * This helps in providing specific error handling for missing customer data.
     */
    public static class CustomerNotFoundException extends RuntimeException {
        public CustomerNotFoundException(String message) {
            super(message);
        }
    }
}
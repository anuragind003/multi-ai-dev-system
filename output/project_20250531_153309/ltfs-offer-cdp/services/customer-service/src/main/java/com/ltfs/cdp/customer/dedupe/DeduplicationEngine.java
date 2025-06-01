package com.ltfs.cdp.customer.dedupe;

import com.ltfs.cdp.customer.model.Customer;
import com.ltfs.cdp.customer.repository.CustomerRepository;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import java.time.LocalDate;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.Objects;
import java.util.Optional;
import java.util.UUID;

/**
 * {@code DeduplicationEngine} is a core component responsible for applying deduplication rules
 * across customer records within the LTFS Offer CDP system.
 *
 * It performs deduplication against the 'live book' (Customer 360) and also within batches of
 * incoming customer data. Special rules apply for 'Top-up loan' offers, which are deduped
 * only against other 'Top-up loan' offers.
 */
@Service
public class DeduplicationEngine {

    private static final Logger log = LoggerFactory.getLogger(DeduplicationEngine.class);

    private final CustomerRepository customerRepository;

    // Constants for product types to ensure consistency
    private static final String PRODUCT_TYPE_TOP_UP_LOAN = "TOP_UP_LOAN";
    private static final String PRODUCT_TYPE_CONSUMER_LOAN = "CONSUMER_LOAN"; // General category for other CL products

    /**
     * Constructs a new {@code DeduplicationEngine} with the specified customer repository.
     *
     * @param customerRepository The repository used to access existing customer data from the live book.
     */
    @Autowired
    public DeduplicationEngine(CustomerRepository customerRepository) {
        this.customerRepository = customerRepository;
    }

    /**
     * Performs deduplication on a list of incoming customer records.
     *
     * This method processes each incoming customer by first checking for duplicates against the
     * existing 'live book' (Customer 360) and then against other customers already processed
     * within the current batch.
     *
     * The status of each incoming customer is updated to reflect the deduplication outcome:
     * - "NEW": The customer is unique and should be considered for creation.
     * - "DUPLICATE_OF_EXISTING": The customer matches an existing record in the live book.
     * - "DUPLICATE_IN_BATCH": The customer matches another customer within the same incoming batch.
     *
     * For 'Top-up loan' offers, deduplication is restricted to only other 'Top-up loan' offers.
     *
     * @param incomingCustomers A list of new customer records to be deduped.
     * @return A list of processed customer records, each with an updated status indicating
     *         its deduplication outcome. Records marked as duplicates are typically not
     *         persisted as new unique entries but might trigger updates or be logged.
     */
    public List<Customer> deduplicateCustomers(List<Customer> incomingCustomers) {
        if (incomingCustomers == null || incomingCustomers.isEmpty()) {
            log.info("No incoming customers provided for deduplication. Returning an empty list.");
            return Collections.emptyList();
        }

        log.info("Starting deduplication process for {} incoming customer records.", incomingCustomers.size());

        // Fetch all relevant existing customers from the live book for comparison.
        // In a high-volume production system, this might be optimized to fetch only
        // customers whose identifiers (PAN, Aadhaar, Mobile) are present in the incoming batch
        // to reduce memory footprint and improve performance.
        List<Customer> existingLiveBookCustomers = customerRepository.findAll();
        log.debug("Fetched {} existing customers from the live book for comparison.", existingLiveBookCustomers.size());

        List<Customer> processedCustomers = new ArrayList<>();
        // This list holds customers from the current batch that have been deemed unique so far.
        // Subsequent incoming customers will be checked against this list.
        List<Customer> uniqueCustomersInBatch = new ArrayList<>();

        for (Customer newCustomer : incomingCustomers) {
            if (newCustomer == null) {
                log.warn("Skipping null customer record in incoming batch.");
                continue;
            }
            log.debug("Processing incoming customer: {}", newCustomer.getId());

            // 1. Attempt to find a match in the existing 'live book' (Customer 360).
            Optional<Customer> liveBookMatch = findMatchInLiveBook(newCustomer, existingLiveBookCustomers);
            if (liveBookMatch.isPresent()) {
                Customer matchedExistingCustomer = liveBookMatch.get();
                newCustomer.setStatus("DUPLICATE_OF_EXISTING");
                // Link the incoming customer to the existing 360 profile.
                // If the existing customer doesn't have a 360 ID yet, use its own ID as a placeholder.
                newCustomer.setCustomer360Id(matchedExistingCustomer.getCustomer360Id() != null ?
                                             matchedExistingCustomer.getCustomer360Id() :
                                             matchedExistingCustomer.getId().toString());
                log.info("Customer {} (PAN: {}) is a duplicate of existing live book customer {} (360 ID: {}). Status: {}",
                        newCustomer.getId(), newCustomer.getPan(), matchedExistingCustomer.getId(), newCustomer.getCustomer360Id(), newCustomer.getStatus());
                processedCustomers.add(newCustomer);
                continue; // Move to the next incoming customer as this one is a duplicate of an existing record.
            }

            // 2. If no match in the live book, check against other customers already processed in this batch.
            // This handles duplicates within the same incoming file/stream.
            Optional<Customer> batchMatch = findMatchInBatch(newCustomer, uniqueCustomersInBatch);
            if (batchMatch.isPresent()) {
                Customer matchedBatchCustomer = batchMatch.get();
                newCustomer.setStatus("DUPLICATE_IN_BATCH");
                // Optionally, link to the master customer within the batch if a merging strategy is applied later.
                // newCustomer.setCustomer360Id(matchedBatchCustomer.getId().toString());
                log.info("Customer {} (PAN: {}) is a duplicate of another customer {} (PAN: {}) in the current batch. Status: {}",
                        newCustomer.getId(), newCustomer.getPan(), matchedBatchCustomer.getId(), matchedBatchCustomer.getPan(), newCustomer.getStatus());
                processedCustomers.add(newCustomer);
                continue; // Move to the next incoming customer as this one is a duplicate within the batch.
            }

            // 3. If no match found in live book or within the batch, this customer is considered unique for now.
            newCustomer.setStatus("NEW");
            uniqueCustomersInBatch.add(newCustomer); // Add to the list of unique customers in this batch for future comparisons.
            processedCustomers.add(newCustomer);
            log.debug("Customer {} (PAN: {}) identified as NEW. Added to unique batch list.", newCustomer.getId(), newCustomer.getPan());
        }

        log.info("Deduplication process completed. Total incoming customers: {}, Total processed: {}, Unique identified in batch: {}",
                incomingCustomers.size(), processedCustomers.size(), uniqueCustomersInBatch.size());

        return processedCustomers;
    }

    /**
     * Attempts to find a duplicate for a given new customer within the existing 'live book' customers.
     * This method applies a hierarchy of deduplication rules:
     * 1. Exact PAN match (highest confidence).
     * 2. Exact Aadhaar match (high confidence).
     * 3. Exact Mobile Number match combined with a Name and Date of Birth match (medium confidence).
     * 4. Exact Name and Date of Birth match (lower confidence, might require manual review in production).
     *
     * @param newCustomer The incoming customer record to check.
     * @param liveBookCustomers The list of existing customers from the Customer 360 live book.
     * @return An {@link Optional} containing the matched existing customer if a duplicate is found,
     *         otherwise an empty {@link Optional}.
     */
    private Optional<Customer> findMatchInLiveBook(Customer newCustomer, List<Customer> liveBookCustomers) {
        if (newCustomer == null || liveBookCustomers == null || liveBookCustomers.isEmpty()) {
            return Optional.empty();
        }

        for (Customer existingCustomer : liveBookCustomers) {
            // Ensure we are not comparing the same logical customer if IDs somehow overlap (unlikely for new vs existing)
            if (newCustomer.getId().equals(existingCustomer.getId())) {
                continue;
            }

            // Rule 1: Exact PAN match
            if (newCustomer.getPan() != null && !newCustomer.getPan().trim().isEmpty() &&
                newCustomer.getPan().equalsIgnoreCase(existingCustomer.getPan())) {
                log.debug("Live book match found by PAN: New Customer ID {} vs Existing Customer ID {}", newCustomer.getId(), existingCustomer.getId());
                return Optional.of(existingCustomer);
            }

            // Rule 2: Exact Aadhaar match
            if (newCustomer.getAadhaar() != null && !newCustomer.getAadhaar().trim().isEmpty() &&
                newCustomer.getAadhaar().equals(existingCustomer.getAadhaar())) {
                log.debug("Live book match found by Aadhaar: New Customer ID {} vs Existing Customer ID {}", newCustomer.getId(), existingCustomer.getId());
                return Optional.of(existingCustomer);
            }

            // Rule 3: Exact Mobile Number match + Name & DOB check
            if (newCustomer.getMobileNumber() != null && !newCustomer.getMobileNumber().trim().isEmpty() &&
                newCustomer.getMobileNumber().equals(existingCustomer.getMobileNumber())) {
                if (isNameAndDobMatch(newCustomer, existingCustomer)) {
                    log.debug("Live book match found by Mobile + Name/DOB: New Customer ID {} vs Existing Customer ID {}", newCustomer.getId(), existingCustomer.getId());
                    return Optional.of(existingCustomer);
                }
            }

            // Rule 4: Name + DOB match (as a fallback, potentially lower confidence)
            // This rule alone might be too broad for high-confidence deduplication without other identifiers.
            // In a real system, this might trigger a "potential duplicate" flag for manual review.
            if (isNameAndDobMatch(newCustomer, existingCustomer)) {
                log.debug("Live book potential match found by Name + DOB: New Customer ID {} vs Existing Customer ID {}", newCustomer.getId(), existingCustomer.getId());
                return Optional.of(existingCustomer);
            }
        }
        return Optional.empty();
    }

    /**
     * Attempts to find a duplicate for a given new customer within the list of customers
     * already identified as unique in the current processing batch.
     *
     * This method applies similar deduplication rules as {@link #findMatchInLiveBook},
     * with an additional specific rule for 'Top-up loan' offers:
     * - 'Top-up loan' offers are only deduped against other 'Top-up loan' offers.
     *
     * @param newCustomer The incoming customer record to check.
     * @param uniqueCustomersInBatch The list of customers already identified as unique within the current batch.
     * @return An {@link Optional} containing the matched customer from the batch if a duplicate is found,
     *         otherwise an empty {@link Optional}.
     */
    private Optional<Customer> findMatchInBatch(Customer newCustomer, List<Customer> uniqueCustomersInBatch) {
        if (newCustomer == null || uniqueCustomersInBatch == null || uniqueCustomersInBatch.isEmpty()) {
            return Optional.empty();
        }

        for (Customer existingBatchCustomer : uniqueCustomersInBatch) {
            // Ensure we are not comparing the customer against itself.
            if (newCustomer.getId().equals(existingBatchCustomer.getId())) {
                continue;
            }

            // Special rule: Top-up loan offers must be deduped only within other Top-up offers.
            boolean isNewCustomerTopUp = PRODUCT_TYPE_TOP_UP_LOAN.equalsIgnoreCase(newCustomer.getProductType());
            boolean isExistingBatchCustomerTopUp = PRODUCT_TYPE_TOP_UP_LOAN.equalsIgnoreCase(existingBatchCustomer.getProductType());

            // If one is a Top-up loan and the other is not, they cannot be duplicates according to this rule.
            if (isNewCustomerTopUp != isExistingBatchCustomerTopUp) {
                log.debug("Skipping batch comparison for customer {} and {} due to differing product types (Top-up vs Non-Top-up).",
                        newCustomer.getId(), existingBatchCustomer.getId());
                continue;
            }

            // Apply general deduplication rules (same as live book matching)
            // Rule 1: Exact PAN match
            if (newCustomer.getPan() != null && !newCustomer.getPan().trim().isEmpty() &&
                newCustomer.getPan().equalsIgnoreCase(existingBatchCustomer.getPan())) {
                log.debug("Batch match found by PAN: New Customer ID {} vs Batch Customer ID {}", newCustomer.getId(), existingBatchCustomer.getId());
                return Optional.of(existingBatchCustomer);
            }

            // Rule 2: Exact Aadhaar match
            if (newCustomer.getAadhaar() != null && !newCustomer.getAadhaar().trim().isEmpty() &&
                newCustomer.getAadhaar().equals(existingBatchCustomer.getAadhaar())) {
                log.debug("Batch match found by Aadhaar: New Customer ID {} vs Batch Customer ID {}", newCustomer.getId(), existingBatchCustomer.getId());
                return Optional.of(existingBatchCustomer);
            }

            // Rule 3: Exact Mobile Number match + Name & DOB check
            if (newCustomer.getMobileNumber() != null && !newCustomer.getMobileNumber().trim().isEmpty() &&
                newCustomer.getMobileNumber().equals(existingBatchCustomer.getMobileNumber())) {
                if (isNameAndDobMatch(newCustomer, existingBatchCustomer)) {
                    log.debug("Batch match found by Mobile + Name/DOB: New Customer ID {} vs Batch Customer ID {}", newCustomer.getId(), existingBatchCustomer.getId());
                    return Optional.of(existingBatchCustomer);
                }
            }

            // Rule 4: Name + DOB match
            if (isNameAndDobMatch(newCustomer, existingBatchCustomer)) {
                log.debug("Batch potential match found by Name + DOB: New Customer ID {} vs Batch Customer ID {}", newCustomer.getId(), existingBatchCustomer.getId());
                return Optional.of(existingBatchCustomer);
            }
        }
        return Optional.empty();
    }

    /**
     * Helper method to check if the first name, last name, and date of birth match between two customers.
     * Performs case-insensitive comparison for names and exact comparison for date of birth.
     * Null checks are performed for all fields.
     *
     * @param c1 Customer 1.
     * @param c2 Customer 2.
     * @return {@code true} if names and DOB match, {@code false} otherwise.
     */
    private boolean isNameAndDobMatch(Customer c1, Customer c2) {
        boolean firstNameMatch = c1.getFirstName() != null && c2.getFirstName() != null &&
                                 c1.getFirstName().trim().equalsIgnoreCase(c2.getFirstName().trim());
        boolean lastNameMatch = c1.getLastName() != null && c2.getLastName() != null &&
                                c1.getLastName().trim().equalsIgnoreCase(c2.getLastName().trim());
        boolean dobMatch = Objects.equals(c1.getDateOfBirth(), c2.getDateOfBirth());

        return firstNameMatch && lastNameMatch && dobMatch;
    }

    /**
     * Placeholder interface for CustomerRepository.
     * In a real Spring Boot application, this would typically be a JPA repository
     * extending JpaRepository, located in `com.ltfs.cdp.customer.repository`.
     */
    public interface CustomerRepository {
        /**
         * Retrieves all customer records from the data store.
         * In a production environment, this method would likely be optimized
         * with pagination or specific query criteria.
         * @return A list of all customers.
         */
        List<Customer> findAll();

        /**
         * Finds a customer by its unique identifier (either internal ID or Customer 360 ID).
         * @param id The ID to search for.
         * @return An Optional containing the customer if found, otherwise empty.
         */
        Optional<Customer> findById(String id);
    }

    /**
     * In-memory implementation of {@link CustomerRepository} for demonstration and testing purposes.
     * In a real Spring Boot application, this would be replaced by a database-backed repository.
     */
    @Service // Mark as a Spring service to be discoverable by Spring's component scan
    public static class InMemoryCustomerRepository implements CustomerRepository {
        private final List<Customer> customers = new ArrayList<>();

        /**
         * Initializes the in-memory repository with some dummy customer data.
         */
        public InMemoryCustomerRepository() {
            // Seed with some dummy data for testing deduplication scenarios
            Customer c1 = new Customer("ABCDE1234F", "123456789012", "9876543210", "John", "Doe", LocalDate.of(1980, 1, 1), PRODUCT_TYPE_CONSUMER_LOAN);
            c1.setCustomer360Id("C360-001");
            customers.add(c1);

            Customer c2 = new Customer("FGHIJ5678K", "234567890123", "9988776655", "Jane", "Smith", LocalDate.of(1985, 5, 10), PRODUCT_TYPE_CONSUMER_LOAN);
            c2.setCustomer360Id("C360-002");
            customers.add(c2);

            Customer c3 = new Customer("KLMNO9012L", "345678901234", "9123456789", "Alice", "Brown", LocalDate.of(1990, 10, 15), PRODUCT_TYPE_TOP_UP_LOAN);
            c3.setCustomer360Id("C360-003");
            customers.add(c3);

            Customer c4 = new Customer("PQRST3456M", "456789012345", "9012345678", "Bob", "White", LocalDate.of(1975, 3, 20), PRODUCT_TYPE_CONSUMER_LOAN);
            c4.setCustomer360Id("C360-004");
            customers.add(c4);

            // Example of an existing customer that is a duplicate of C1 by PAN
            Customer c5 = new Customer("ABCDE1234F", "999999999999", "1111111111", "Johnny", "Dough", LocalDate.of(1980, 1, 1), PRODUCT_TYPE_CONSUMER_LOAN);
            c5.setCustomer360Id("C360-001"); // This one is already linked to C360-001
            customers.add(c5);

            log.info("InMemoryCustomerRepository initialized with {} dummy customers.", customers.size());
        }

        @Override
        public List<Customer> findAll() {
            return new ArrayList<>(customers); // Return a copy to prevent external modification
        }

        @Override
        public Optional<Customer> findById(String id) {
            return customers.stream()
                    .filter(c -> c.getId().toString().equals(id) || (c.getCustomer360Id() != null && c.getCustomer360Id().equals(id)))
                    .findFirst();
        }
    }

    /**
     * Placeholder for Customer entity/DTO.
     * In a real Spring Boot application, this would be a JPA entity or a DTO,
     * located in `com.ltfs.cdp.customer.model`.
     */
    public static class Customer {
        private UUID id;
        private String customer360Id; // ID from the live book (Customer 360)
        private String pan;
        private String aadhaar;
        private String mobileNumber;
        private String firstName;
        private String lastName;
        private LocalDate dateOfBirth;
        private String productType; // e.g., "CONSUMER_LOAN", "TOP_UP_LOAN"
        private String status; // e.g., "NEW", "DUPLICATE_OF_EXISTING", "DUPLICATE_IN_BATCH"

        /**
         * Default constructor. Assigns a new random UUID to the customer.
         */
        public Customer() {
            this.id = UUID.randomUUID();
        }

        /**
         * Parameterized constructor for creating new customer records.
         *
         * @param pan The customer's PAN.
         * @param aadhaar The customer's Aadhaar number.
         * @param mobileNumber The customer's mobile number.
         * @param firstName The customer's first name.
         * @param lastName The customer's last name.
         * @param dateOfBirth The customer's date of birth.
         * @param productType The type of product associated with this customer record (e.g., "CONSUMER_LOAN").
         */
        public Customer(String pan, String aadhaar, String mobileNumber, String firstName, String lastName, LocalDate dateOfBirth, String productType) {
            this(); // Call default constructor to set ID
            this.pan = pan;
            this.aadhaar = aadhaar;
            this.mobileNumber = mobileNumber;
            this.firstName = firstName;
            this.lastName = lastName;
            this.dateOfBirth = dateOfBirth;
            this.productType = productType;
            this.status = "NEW"; // Default status for newly created or incoming records
        }

        // --- Getters ---
        public UUID getId() { return id; }
        public String getCustomer360Id() { return customer360Id; }
        public String getPan() { return pan; }
        public String getAadhaar() { return aadhaar; }
        public String getMobileNumber() { return mobileNumber; }
        public String getFirstName() { return firstName; }
        public String getLastName() { return lastName; }
        public LocalDate getDateOfBirth() { return dateOfBirth; }
        public String getProductType() { return productType; }
        public String getStatus() { return status; }

        // --- Setters ---
        public void setId(UUID id) { this.id = id; }
        public void setCustomer360Id(String customer360Id) { this.customer360Id = customer360Id; }
        public void setPan(String pan) { this.pan = pan; }
        public void setAadhaar(String aadhaar) { this.aadhaar = aadhaar; }
        public void setMobileNumber(String mobileNumber) { this.mobileNumber = mobileNumber; }
        public void setFirstName(String firstName) { this.firstName = firstName; }
        public void setLastName(String lastName) { this.lastName = lastName; }
        public void setDateOfBirth(LocalDate dateOfBirth) { this.dateOfBirth = dateOfBirth; }
        public void setProductType(String productType) { this.productType = productType; }
        public void setStatus(String status) { this.status = status; }

        /**
         * Overrides the default equals method. For entity objects, equality is typically
         * based on the unique identifier (ID). Business logic for deduplication
         * (comparing PAN, Aadhaar, etc.) is handled separately in the DeduplicationEngine.
         *
         * @param o The object to compare with.
         * @return True if the objects are equal based on their ID, false otherwise.
         */
        @Override
        public boolean equals(Object o) {
            if (this == o) return true;
            if (o == null || getClass() != o.getClass()) return false;
            Customer customer = (Customer) o;
            return Objects.equals(id, customer.id);
        }

        /**
         * Overrides the default hashCode method. Consistent with the equals method,
         * the hash code is based on the unique identifier (ID).
         *
         * @return The hash code for this customer.
         */
        @Override
        public int hashCode() {
            return Objects.hash(id);
        }

        /**
         * Provides a string representation of the Customer object, redacting sensitive
         * information like full PAN, Aadhaar, and Mobile Number for logging purposes.
         *
         * @return A string representation of the customer.
         */
        @Override
        public String toString() {
            return "Customer{" +
                   "id=" + id +
                   ", customer360Id='" + customer360Id + '\'' +
                   ", pan='" + (pan != null && pan.length() > 4 ? pan.substring(0, 4) + "..." : pan) + '\'' +
                   ", aadhaar='" + (aadhaar != null && aadhaar.length() > 4 ? aadhaar.substring(0, 4) + "..." : aadhaar) + '\'' +
                   ", mobileNumber='" + (mobileNumber != null && mobileNumber.length() > 4 ? mobileNumber.substring(0, 4) + "..." : mobileNumber) + '\'' +
                   ", firstName='" + firstName + '\'' +
                   ", lastName='" + lastName + '\'' +
                   ", dateOfBirth=" + dateOfBirth +
                   ", productType='" + productType + '\'' +
                   ", status='" + status + '\'' +
                   '}';
        }
    }
}
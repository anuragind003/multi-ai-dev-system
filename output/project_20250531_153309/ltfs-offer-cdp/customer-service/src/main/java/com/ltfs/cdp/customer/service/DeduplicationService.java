package com.ltfs.cdp.customer.service;

import com.ltfs.cdp.customer.model.Customer;
import com.ltfs.cdp.customer.model.Offer;
import com.ltfs.cdp.customer.repository.CustomerRepository;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Objects;
import java.util.Optional;
import java.util.Set;
import java.util.stream.Collectors;

/**
 * Service class responsible for implementing complex deduplication logic
 * across various consumer loan products and against the 'live book' (Customer 360).
 * This service ensures a single, unified customer profile view.
 *
 * <p>
 * The deduplication process involves:
 * 1. Matching incoming customer profiles against existing records in the Customer 360 system.
 * 2. Identifying and consolidating duplicate customer profiles within the incoming batch itself.
 * 3. Specific handling for 'Top-up' loan offers, where deduplication occurs only within
 *    the batch of Top-up offers, and duplicates are removed.
 * </p>
 */
@Service
public class DeduplicationService {

    private static final Logger logger = LoggerFactory.getLogger(DeduplicationService.class);

    private final CustomerRepository customerRepository;

    /**
     * Constructs a new DeduplicationService with the given CustomerRepository.
     *
     * @param customerRepository The repository for accessing Customer 360 data.
     */
    @Autowired
    public DeduplicationService(CustomerRepository customerRepository) {
        this.customerRepository = customerRepository;
    }

    /**
     * Performs deduplication for a list of incoming customer profiles.
     * This method first attempts to find matches in the 'live book' (Customer 360).
     * If a match is found, the existing Customer 360 record is considered the canonical one.
     * If no match is found in the 'live book', the incoming customer is then checked
     * against other incoming customers already processed in the current batch to ensure
     * only unique profiles are retained.
     *
     * @param incomingCustomers A list of customer profiles to be deduped.
     * @return A list of unique and deduped customer profiles. These profiles
     *         are either existing Customer 360 records or newly identified unique customers
     *         from the incoming batch.
     */
    @Transactional
    public List<Customer> deduplicateCustomers(List<Customer> incomingCustomers) {
        if (incomingCustomers == null || incomingCustomers.isEmpty()) {
            logger.warn("No incoming customers provided for deduplication. Returning an empty list.");
            return new ArrayList<>();
        }

        logger.info("Starting deduplication for {} incoming customer profiles.", incomingCustomers.size());

        // A Set to efficiently track unique customers based on their deduplication key (defined by Customer.equals/hashCode).
        Set<Customer> uniqueCustomersSet = new HashSet<>();
        // A List to maintain the order or simply collect the deduped results.
        List<Customer> dedupedOutput = new ArrayList<>();

        for (Customer incomingCustomer : incomingCustomers) {
            if (incomingCustomer == null) {
                logger.warn("Skipping null customer in incoming list during customer deduplication.");
                continue;
            }

            // 1. Attempt to find a match in the 'live book' (Customer 360)
            Optional<Customer> existingCustomerOpt = findMatchingCustomerInLiveBook(incomingCustomer);

            if (existingCustomerOpt.isPresent()) {
                Customer existingCustomer = existingCustomerOpt.get();
                logger.debug("Incoming customer (ID: {}) matched with existing Customer 360 (ID: {}).",
                        incomingCustomer.getId(), existingCustomer.getId());

                // If a match is found, the existing customer is the canonical one.
                // Add it to our unique set. If it was already added (e.g., from another incoming record
                // that matched the same existing customer), the Set's add method handles it.
                if (uniqueCustomersSet.add(existingCustomer)) {
                    dedupedOutput.add(existingCustomer);
                }
                // This incomingCustomer is a duplicate of an existing one, so we don't add it to the output.
            } else {
                // 2. No match in live book. Now, check if this incoming customer is a duplicate
                //    of another incoming customer already processed in this batch.
                //    This is handled by the `uniqueCustomersSet.add()` method, which returns false if the element
                //    (based on its equals/hashCode) is already present.
                if (uniqueCustomersSet.add(incomingCustomer)) {
                    logger.debug("Incoming customer (ID: {}) is unique so far. Adding to deduped list.", incomingCustomer.getId());
                    dedupedOutput.add(incomingCustomer);
                } else {
                    logger.debug("Incoming customer (ID: {}) is a duplicate of another incoming customer already processed in this batch.", incomingCustomer.getId());
                }
            }
        }

        logger.info("Customer deduplication completed. Original: {} customers, Deduped: {} customers.",
                incomingCustomers.size(), dedupedOutput.size());

        return dedupedOutput;
    }

    /**
     * Finds a matching customer in the Customer 360 'live book' based on
     * a hierarchy of primary deduplication criteria. The order of matching
     * is typically: PAN -> Mobile Number -> Aadhaar Number -> (Fallback) Name + Date of Birth.
     *
     * @param incomingCustomer The customer profile to find a match for.
     * @return An Optional containing the matching Customer if found, otherwise empty.
     */
    private Optional<Customer> findMatchingCustomerInLiveBook(Customer incomingCustomer) {
        // Prioritize PAN for matching as it's often a strong unique identifier.
        if (incomingCustomer.getPanNumber() != null && !incomingCustomer.getPanNumber().trim().isEmpty()) {
            Optional<Customer> byPan = customerRepository.findByPanNumber(incomingCustomer.getPanNumber());
            if (byPan.isPresent()) {
                logger.debug("Match found in live book by PAN: {}", incomingCustomer.getPanNumber());
                return byPan;
            }
        }

        // If no match by PAN, try Mobile Number.
        if (incomingCustomer.getMobileNumber() != null && !incomingCustomer.getMobileNumber().trim().isEmpty()) {
            Optional<Customer> byMobile = customerRepository.findByMobileNumber(incomingCustomer.getMobileNumber());
            if (byMobile.isPresent()) {
                logger.debug("Match found in live book by Mobile Number: {}", incomingCustomer.getMobileNumber());
                return byMobile;
            }
        }

        // If no match by Mobile, try Aadhaar Number.
        if (incomingCustomer.getAadhaarNumber() != null && !incomingCustomer.getAadhaarNumber().trim().isEmpty()) {
            Optional<Customer> byAadhaar = customerRepository.findByAadhaarNumber(incomingCustomer.getAadhaarNumber());
            if (byAadhaar.isPresent()) {
                logger.debug("Match found in live book by Aadhaar Number: {}", incomingCustomer.getAadhaarNumber());
                return byAadhaar;
            }
        }

        // Fallback: Name + Date of Birth. This is less reliable and might yield multiple potential matches.
        // In a production system, this might trigger a fuzzy matching algorithm or a manual review process.
        if (incomingCustomer.getFirstName() != null && !incomingCustomer.getFirstName().trim().isEmpty() &&
            incomingCustomer.getLastName() != null && !incomingCustomer.getLastName().trim().isEmpty() &&
            incomingCustomer.getDateOfBirth() != null && !incomingCustomer.getDateOfBirth().trim().isEmpty()) {

            List<Customer> potentialMatches = customerRepository.findByFirstNameAndLastNameAndDateOfBirth(
                    incomingCustomer.getFirstName(), incomingCustomer.getLastName(), incomingCustomer.getDateOfBirth());

            if (!potentialMatches.isEmpty()) {
                // For simplicity, we return the first potential match.
                // A more sophisticated approach would involve scoring or further validation.
                logger.debug("Potential match found in live book by Name+DOB for {}.", incomingCustomer.getFirstName());
                return Optional.of(potentialMatches.get(0));
            }
        }

        logger.debug("No strong match found in live book for customer with PAN: {}, Mobile: {}, Aadhaar: {}",
                incomingCustomer.getPanNumber(), incomingCustomer.getMobileNumber(), incomingCustomer.getAadhaarNumber());
        return Optional.empty();
    }

    /**
     * Performs deduplication specifically for 'Top-up' loan offers.
     * This method processes a list of offers and retains only unique 'Top-up' offers.
     * The deduplication logic for Top-up offers is applied *only* within the provided
     * list of incoming offers and does not involve checking against a 'live book' of offers.
     * Matches found (as defined by {@link Offer#equals(Object)}) are removed, meaning
     * only one instance of a duplicate Top-up offer is kept.
     *
     * @param incomingTopUpOffers A list of Top-up offers to be deduped.
     * @return A list of unique Top-up offers.
     */
    public List<Offer> deduplicateTopUpOffers(List<Offer> incomingTopUpOffers) {
        if (incomingTopUpOffers == null || incomingTopUpOffers.isEmpty()) {
            logger.warn("No incoming Top-up offers provided for deduplication. Returning an empty list.");
            return new ArrayList<>();
        }

        logger.info("Starting deduplication for {} incoming Top-up offers.", incomingTopUpOffers.size());

        // Use a Set to automatically handle uniqueness based on Offer's equals/hashCode.
        // The equals/hashCode for Offer should be defined based on what constitutes a duplicate Top-up offer.
        // For example, two Top-up offers for the same customer (customerId) and same product type
        // might be considered duplicates.
        Set<Offer> uniqueTopUpOffers = new HashSet<>();
        List<Offer> dedupedOutput = new ArrayList<>();

        for (Offer offer : incomingTopUpOffers) {
            if (offer == null) {
                logger.warn("Skipping null offer in incoming Top-up list during offer deduplication.");
                continue;
            }
            // Robustness check: ensure the offer is indeed a Top-up offer, though the input list
            // is expected to contain only them.
            if (!"TOP_UP".equalsIgnoreCase(offer.getOfferType())) {
                logger.warn("Offer with ID {} is not a TOP_UP offer. Skipping from Top-up deduplication.", offer.getId());
                continue;
            }

            // Add to the set. If it's a duplicate (based on Offer's equals/hashCode), it won't be added.
            if (uniqueTopUpOffers.add(offer)) {
                dedupedOutput.add(offer);
                logger.debug("Added unique Top-up offer: {}", offer.getId());
            } else {
                logger.debug("Skipping duplicate Top-up offer: {}", offer.getId());
            }
        }

        logger.info("Top-up offer deduplication completed. Original: {} offers, Deduped: {} offers.",
                incomingTopUpOffers.size(), dedupedOutput.size());

        return dedupedOutput;
    }

    // --- Placeholder classes/interfaces for demonstration purposes ---
    // In a real project, these would be proper JPA entities and Spring Data JPA repositories
    // defined in their respective packages (e.g., com.ltfs.cdp.customer.model, com.ltfs.cdp.customer.repository).

    /**
     * Placeholder for Customer entity.
     * In a real application, this would be a JPA entity with proper annotations
     * (e.g., @Entity, @Table, @Id, @Column).
     *
     * <p>
     * For deduplication, it is CRUCIAL that {@code equals()} and {@code hashCode()} methods
     * are correctly implemented based on the fields used for identifying unique customers
     * (e.g., PAN, Mobile Number, Aadhaar Number, or a combination of Name and Date of Birth).
     * The current implementation provides a simplified example of such logic.
     * </p>
     */
    public static class Customer {
        private String id;
        private String mobileNumber;
        private String panNumber;
        private String aadhaarNumber;
        private String email;
        private String firstName;
        private String lastName;
        private String dateOfBirth; // Using String for simplicity; java.time.LocalDate is recommended.
        // Other customer attributes like address, gender, etc.

        public Customer() {}

        public Customer(String id, String mobileNumber, String panNumber, String aadhaarNumber, String email, String firstName, String lastName, String dateOfBirth) {
            this.id = id;
            this.mobileNumber = mobileNumber;
            this.panNumber = panNumber;
            this.aadhaarNumber = aadhaarNumber;
            this.email = email;
            this.firstName = firstName;
            this.lastName = lastName;
            this.dateOfBirth = dateOfBirth;
        }

        // Getters and Setters
        public String getId() { return id; }
        public void setId(String id) { this.id = id; }
        public String getMobileNumber() { return mobileNumber; }
        public void setMobileNumber(String mobileNumber) { this.mobileNumber = mobileNumber; }
        public String getPanNumber() { return panNumber; }
        public void setPanNumber(String panNumber) { this.panNumber = panNumber; }
        public String getAadhaarNumber() { return aadhaarNumber; }
        public void setAadhaarNumber(String aadhaarNumber) { this.aadhaarNumber = aadhaarNumber; }
        public String getEmail() { return email; }
        public void setEmail(String email) { this.email = email; }
        public String getFirstName() { return firstName; }
        public void setFirstName(String firstName) { this.firstName = firstName; }
        public String getLastName() { return lastName; }
        public void setLastName(String lastName) { this.lastName = lastName; }
        public String getDateOfBirth() { return dateOfBirth; }
        public void setDateOfBirth(String dateOfBirth) { this.dateOfBirth = dateOfBirth; }

        /**
         * Defines equality for Customer objects based on deduplication criteria.
         * A customer is considered equal (a duplicate) if they share the same:
         * 1. PAN (Permanent Account Number) - if present and non-empty.
         * OR
         * 2. Mobile Number - if present and non-empty.
         * OR
         * 3. Aadhaar Number - if present and non-empty.
         * OR (as a fallback, if primary identifiers are missing for *both* customers being compared)
         * 4. Combination of First Name, Last Name, and Date of Birth.
         *
         * <p>
         * This is a simplified logic. A real-world scenario might involve:
         * - A scoring system for matches.
         * - Fuzzy matching for names/addresses.
         * - A hierarchy of rules (e.g., PAN match is stronger than Mobile match).
         * - Handling of multiple valid identifiers for the same person (e.g., old vs. new mobile number).
         * </p>
         *
         * @param o The object to compare with.
         * @return true if the objects are considered duplicates based on the defined criteria, false otherwise.
         */
        @Override
        public boolean equals(Object o) {
            if (this == o) return true;
            if (o == null || getClass() != o.getClass()) return false;
            Customer customer = (Customer) o;

            // Primary matching criteria: PAN, Mobile, Aadhaar
            // If any of these match, and they are not null/empty for *both* customers, then it's a match.
            boolean panMatch = (this.panNumber != null && !this.panNumber.trim().isEmpty() &&
                                customer.panNumber != null && !customer.panNumber.trim().isEmpty() &&
                                Objects.equals(this.panNumber.toLowerCase(), customer.panNumber.toLowerCase()));
            boolean mobileMatch = (this.mobileNumber != null && !this.mobileNumber.trim().isEmpty() &&
                                   customer.mobileNumber != null && !customer.mobileNumber.trim().isEmpty() &&
                                   Objects.equals(this.mobileNumber, customer.mobileNumber));
            boolean aadhaarMatch = (this.aadhaarNumber != null && !this.aadhaarNumber.trim().isEmpty() &&
                                    customer.aadhaarNumber != null && !customer.aadhaarNumber.trim().isEmpty() &&
                                    Objects.equals(this.aadhaarNumber, customer.aadhaarNumber));

            if (panMatch || mobileMatch || aadhaarMatch) {
                return true;
            }

            // Fallback: Name + DOB (less reliable, used only if primary identifiers are missing for *both* customers)
            boolean thisHasNoPrimaryId = (this.panNumber == null || this.panNumber.trim().isEmpty()) &&
                                         (this.mobileNumber == null || this.mobileNumber.trim().isEmpty()) &&
                                         (this.aadhaarNumber == null || this.aadhaarNumber.trim().isEmpty());
            boolean otherHasNoPrimaryId = (customer.panNumber == null || customer.panNumber.trim().isEmpty()) &&
                                          (customer.mobileNumber == null || customer.mobileNumber.trim().isEmpty()) &&
                                          (customer.aadhaarNumber == null || customer.aadhaarNumber.trim().isEmpty());

            if (thisHasNoPrimaryId && otherHasNoPrimaryId &&
                this.firstName != null && !this.firstName.trim().isEmpty() &&
                this.lastName != null && !this.lastName.trim().isEmpty() &&
                this.dateOfBirth != null && !this.dateOfBirth.trim().isEmpty() &&
                customer.firstName != null && !customer.firstName.trim().isEmpty() &&
                customer.lastName != null && !customer.lastName.trim().isEmpty() &&
                customer.dateOfBirth != null && !customer.dateOfBirth.trim().isEmpty()) {
                return Objects.equals(firstName.toLowerCase(), customer.firstName.toLowerCase()) &&
                       Objects.equals(lastName.toLowerCase(), customer.lastName.toLowerCase()) &&
                       Objects.equals(dateOfBirth, customer.dateOfBirth);
            }

            return false; // No strong match found based on any criteria
        }

        /**
         * Generates a hash code consistent with the {@code equals()} method.
         * The hash code is derived from the primary unique identifiers in a hierarchical manner:
         * PAN -> Mobile Number -> Aadhaar Number -> (Fallback) Name + Date of Birth.
         * This ensures that objects considered equal by {@code equals()} also have the same hash code,
         * which is crucial for correct behavior in hash-based collections like {@link HashSet} and {@link java.util.HashMap}.
         *
         * @return A hash code for this Customer object.
         */
        @Override
        public int hashCode() {
            // Use the strongest available identifier for hashing.
            if (panNumber != null && !panNumber.trim().isEmpty()) {
                return Objects.hash(panNumber.toLowerCase());
            }
            if (mobileNumber != null && !mobileNumber.trim().isEmpty()) {
                return Objects.hash(mobileNumber);
            }
            if (aadhaarNumber != null && !aadhaarNumber.trim().isEmpty()) {
                return Objects.hash(aadhaarNumber);
            }
            // Fallback for less reliable matches, consistent with equals() logic.
            // Ensure case-insensitivity for names if equals() does.
            return Objects.hash(firstName != null ? firstName.toLowerCase() : null,
                                lastName != null ? lastName.toLowerCase() : null,
                                dateOfBirth);
        }

        @Override
        public String toString() {
            // Mask sensitive data for logging/debugging
            String maskedMobile = (mobileNumber != null && mobileNumber.length() > 4) ?
                                  mobileNumber.substring(0, 4) + "..." : mobileNumber;
            String maskedPan = (panNumber != null && panNumber.length() > 4) ?
                               panNumber.substring(0, 4) + "..." : panNumber;
            String maskedAadhaar = (aadhaarNumber != null && aadhaarNumber.length() > 4) ?
                                   aadhaarNumber.substring(0, 4) + "..." : aadhaarNumber;

            return "Customer{" +
                   "id='" + id + '\'' +
                   ", mobileNumber='" + maskedMobile + '\'' +
                   ", panNumber='" + maskedPan + '\'' +
                   ", aadhaarNumber='" + maskedAadhaar + '\'' +
                   ", firstName='" + firstName + '\'' +
                   ", lastName='" + lastName + '\'' +
                   '}';
        }
    }

    /**
     * Placeholder for Offer entity.
     * In a real application, this would be a JPA entity.
     *
     * <p>
     * For Top-up offer deduplication, {@code equals()} and {@code hashCode()} should define
     * what makes two Top-up offers duplicates. The current implementation assumes that
     * a customer can only have one unique 'TOP_UP' offer at a time, identified by their customer ID.
     * </p>
     */
    public static class Offer {
        private String id;
        private String customerId;
        private String offerType; // e.g., "TOP_UP", "LOYALTY", "PREAPPROVED", "E_AGGREGATOR"
        private Double offerAmount;
        // Other offer attributes like validity, product details, etc.

        public Offer() {}

        public Offer(String id, String customerId, String offerType, Double offerAmount) {
            this.id = id;
            this.customerId = customerId;
            this.offerType = offerType;
            this.offerAmount = offerAmount;
        }

        // Getters and Setters
        public String getId() { return id; }
        public void setId(String id) { this.id = id; }
        public String getCustomerId() { return customerId; }
        public void setCustomerId(String customerId) { this.customerId = customerId; }
        public String getOfferType() { return offerType; }
        public void setOfferType(String offerType) { this.offerType = offerType; }
        public Double getOfferAmount() { return offerAmount; }
        public void setOfferAmount(Double offerAmount) { this.offerAmount = offerAmount; }

        /**
         * Defines equality for Offer objects, specifically for Top-up offers.
         * An Offer is considered equal (a duplicate for deduplication purposes) if:
         * 1. Both offers are of type "TOP_UP" (case-insensitive).
         * AND
         * 2. They are associated with the same customer ID.
         *
         * <p>
         * This implies a business rule that a single customer should only have one
         * unique Top-up offer within a given processing batch.
         * A more complex rule might involve offer validity dates, specific product codes, etc.
         * </p>
         *
         * @param o The object to compare with.
         * @return true if the objects are considered duplicate Top-up offers, false otherwise.
         */
        @Override
        public boolean equals(Object o) {
            if (this == o) return true;
            if (o == null || getClass() != o.getClass()) return false;
            Offer offer = (Offer) o;

            // Only apply this deduplication logic if both offers are of type "TOP_UP".
            // For other offer types, their uniqueness might be based on their own ID or other criteria,
            // which is not covered by this specific Top-up deduplication rule.
            boolean isThisTopUp = "TOP_UP".equalsIgnoreCase(this.offerType);
            boolean isOtherTopUp = "TOP_UP".equalsIgnoreCase(offer.offerType);

            if (isThisTopUp && isOtherTopUp) {
                // If both are Top-up offers, they are duplicates if they are for the same customer.
                return Objects.equals(customerId, offer.customerId);
            }

            // If they are not both Top-up offers, or if this logic doesn't apply,
            // fall back to comparing by their unique ID (assuming ID is unique for all offers).
            return Objects.equals(id, offer.id);
        }

        /**
         * Generates a hash code consistent with the {@code equals()} method for Offer objects.
         * For "TOP_UP" offers, the hash code is based on the customer ID and the "TOP_UP" type string.
         * For other offer types, it falls back to using the offer's unique ID.
         *
         * @return A hash code for this Offer object.
         */
        @Override
        public int hashCode() {
            // Consistent with equals: if it's a Top-up offer, hash based on customerId and offerType.
            if ("TOP_UP".equalsIgnoreCase(this.offerType)) {
                return Objects.hash(customerId, "TOP_UP"); // Use a constant string for the type to ensure consistency
            }
            // For other offer types, their uniqueness might be based on their own ID.
            return Objects.hash(id);
        }

        @Override
        public String toString() {
            return "Offer{" +
                   "id='" + id + '\'' +
                   ", customerId='" + customerId + '\'' +
                   ", offerType='" + offerType + '\'' +
                   ", offerAmount=" + offerAmount +
                   '}';
        }
    }

    /**
     * Placeholder for CustomerRepository interface.
     * In a real application, this would be a Spring Data JPA repository
     * extending JpaRepository, e.g., `public interface CustomerRepository extends JpaRepository<Customer, String>`.
     * It would interact with the PostgreSQL database.
     */
    public interface CustomerRepository {
        /**
         * Finds a customer by their PAN (Permanent Account Number).
         * @param panNumber The PAN to search for.
         * @return An Optional containing the Customer if found, otherwise empty.
         */
        Optional<Customer> findByPanNumber(String panNumber);

        /**
         * Finds a customer by their mobile number.
         * @param mobileNumber The mobile number to search for.
         * @return An Optional containing the Customer if found, otherwise empty.
         */
        Optional<Customer> findByMobileNumber(String mobileNumber);

        /**
         * Finds a customer by their Aadhaar number.
         * @param aadhaarNumber The Aadhaar number to search for.
         * @return An Optional containing the Customer if found, otherwise empty.
         */
        Optional<Customer> findByAadhaarNumber(String aadhaarNumber);

        /**
         * Finds customers by a combination of first name, last name, and date of birth.
         * This is typically used for less precise matching or as a fallback.
         * @param firstName The first name.
         * @param lastName The last name.
         * @param dateOfBirth The date of birth (as a String, matching the Customer entity's type).
         * @return A list of potential matching Customers.
         */
        List<Customer> findByFirstNameAndLastNameAndDateOfBirth(String firstName, String lastName, String dateOfBirth);

        // In a full implementation, you would also have methods like:
        // Customer save(Customer customer); // To persist new or updated customer profiles
        // Optional<Customer> findById(String id);
    }
}
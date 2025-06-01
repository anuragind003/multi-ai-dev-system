package com.ltfs.cdp.customer.service;

import com.ltfs.cdp.customer.model.Customer;
import com.ltfs.cdp.customer.model.Offer;
import com.ltfs.cdp.customer.repository.CustomerRepository;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collections;
import java.util.List;
import java.util.Objects;
import java.util.stream.Collectors;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.*;

/**
 * Unit and integration tests for the {@link DeduplicationEngine} class.
 * This test suite covers various scenarios for customer and offer deduplication,
 * including exact matches, partial matches, handling of empty/null inputs,
 * and specific rules like Top-up loan offer deduplication.
 *
 * <p>Note: For the purpose of making this test file self-contained and runnable,
 * simplified {@code Customer} and {@code Offer} model classes, along with a
 * mock {@code CustomerRepository} interface, are defined directly within this file.
 * In a real project, these would typically be imported from their respective
 * packages (e.g., {@code com.ltfs.cdp.customer.model}, {@code com.ltfs.cdp.customer.repository}).</p>
 */
@ExtendWith(MockitoExtension.class)
@DisplayName("DeduplicationEngine Test Suite")
public class DeduplicationEngineTest {

    /**
     * Mock of {@link CustomerRepository} to simulate database interactions
     * and control the 'live book' data for testing deduplication logic.
     */
    @Mock
    private CustomerRepository customerRepository;

    /**
     * The instance of {@link DeduplicationEngine} under test.
     * {@code @InjectMocks} automatically injects the mocked dependencies.
     */
    @InjectMocks
    private DeduplicationEngine deduplicationEngine;

    // Test data for Customer deduplication
    private Customer customer1;
    private Customer customer2;
    private Customer customer3; // Duplicate of customer1 by PAN
    private Customer customer4; // Partial match, but not a duplicate
    private Customer customer5; // For live book duplicate scenario

    // Test data for Offer deduplication
    private Offer offer1; // Top-up loan offer
    private Offer offer2; // Top-up loan offer, duplicate of offer1
    private Offer offer3; // Preapproved loan offer
    private Offer offer4; // Preapproved loan offer, duplicate of offer3
    private Offer offer5; // Top-up loan offer for a different customer
    private Offer offer6; // Preapproved loan offer for a different customer

    /**
     * Sets up common test data and resets mock interactions before each test method.
     */
    @BeforeEach
    void setUp() {
        // Initialize test customer data
        customer1 = new Customer("C001", "John", "Doe", "9876543210", "ABCDE1234F", "111122223333", "Consumer Loan");
        customer2 = new Customer("C002", "Jane", "Smith", "9988776655", "FGHIJ5678K", "444455556666", "Consumer Loan");
        // customer3 has the same PAN as customer1, making it a duplicate
        customer3 = new Customer("C003", "Jonathan", "Doe", "9123456789", "ABCDE1234F", "999988887777", "Consumer Loan");
        // customer4 has the same name as customer1 but different key identifiers (PAN/Aadhaar), so not a duplicate
        customer4 = new Customer("C004", "John", "Doe", "9876543211", "LMNOP9012Q", "000011112222", "Consumer Loan");
        // customer5 is used to simulate an existing customer in the 'live book'
        customer5 = new Customer("C005", "Live", "Book", "9000000000", "LIVEB1234L", "555566667777", "Consumer Loan");

        // Initialize test offer data
        offer1 = new Offer("O001", "C001", "Top-up Loan", "9876543210", "ABCDE1234F");
        // offer2 is a duplicate of offer1 based on mobile/PAN
        offer2 = new Offer("O002", "C001", "Top-up Loan", "9876543210", "ABCDE1234F");
        offer3 = new Offer("O003", "C002", "Preapproved Loan", "9988776655", "FGHIJ5678K");
        // offer4 is a duplicate of offer3 based on mobile/PAN
        offer4 = new Offer("O004", "C002", "Preapproved Loan", "9988776655", "FGHIJ5678K");
        // offer5 is a Top-up offer for a different customer, should not dedupe with offer1/2
        offer5 = new Offer("O005", "C005", "Top-up Loan", "9000000000", "LIVEB1234L");
        // offer6 is a Preapproved offer for a different customer, should not dedupe with offer3/4
        offer6 = new Offer("O006", "C006", "Preapproved Loan", "9111111111", "XYZAB5678C");

        // Reset mock interactions to ensure a clean state for each test
        reset(customerRepository);
    }

    // --- Customer Deduplication Tests ---

    @Test
    @DisplayName("Should return an empty list when incoming customer list is null")
    void testDeduplicateCustomers_nullIncomingList() {
        List<Customer> result = deduplicationEngine.deduplicateCustomers(null);
        assertNotNull(result, "Result list should not be null");
        assertTrue(result.isEmpty(), "Result list should be empty for null input");
        verifyNoInteractions(customerRepository); // No repository interaction expected for null input
    }

    @Test
    @DisplayName("Should return an empty list when incoming customer list is empty")
    void testDeduplicateCustomers_emptyIncomingList() {
        List<Customer> result = deduplicationEngine.deduplicateCustomers(Collections.emptyList());
        assertNotNull(result, "Result list should not be null");
        assertTrue(result.isEmpty(), "Result list should be empty for empty input");
        verifyNoInteractions(customerRepository); // No repository interaction expected for empty input
    }

    @Test
    @DisplayName("Should deduplicate customers within the incoming batch based on exact PAN match")
    void testDeduplicateCustomers_exactMatchPan() {
        // Mock live book to be empty to focus on deduplication within the incoming batch
        when(customerRepository.findAll()).thenReturn(Collections.emptyList());

        List<Customer> incomingCustomers = Arrays.asList(customer1, customer3); // customer3 has same PAN as customer1
        List<Customer> uniqueCustomers = deduplicationEngine.deduplicateCustomers(incomingCustomers);

        assertNotNull(uniqueCustomers, "Unique customers list should not be null");
        assertEquals(1, uniqueCustomers.size(), "Only one customer should remain after PAN deduplication");
        assertTrue(uniqueCustomers.contains(customer1), "customer1 should be present as the unique entry");
        assertFalse(uniqueCustomers.contains(customer3), "customer3 should be removed as a duplicate");
        verify(customerRepository, times(1)).findAll(); // Verify repository was called once
    }

    @Test
    @DisplayName("Should deduplicate customers within the incoming batch based on exact Aadhaar match")
    void testDeduplicateCustomers_exactMatchAadhaar() {
        // Create two customers with different PAN but same Aadhaar for this specific test
        Customer cAadhaar1 = new Customer("C006", "Alice", "Brown", "1111111111", "PAN1234A", "AADHAAR1", "CL");
        Customer cAadhaar2 = new Customer("C007", "Bob", "White", "2222222222", "PAN5678B", "AADHAAR1", "CL");

        when(customerRepository.findAll()).thenReturn(Collections.emptyList());

        List<Customer> incomingCustomers = Arrays.asList(cAadhaar1, cAadhaar2);
        List<Customer> uniqueCustomers = deduplicationEngine.deduplicateCustomers(incomingCustomers);

        assertNotNull(uniqueCustomers, "Unique customers list should not be null");
        assertEquals(1, uniqueCustomers.size(), "Only one customer should remain after Aadhaar deduplication");
        assertTrue(uniqueCustomers.contains(cAadhaar1), "cAadhaar1 should be present as the unique entry");
        assertFalse(uniqueCustomers.contains(cAadhaar2), "cAadhaar2 should be removed as a duplicate");
        verify(customerRepository, times(1)).findAll();
    }

    @Test
    @DisplayName("Should not deduplicate distinct customers with no matching key identifiers")
    void testDeduplicateCustomers_noMatch() {
        when(customerRepository.findAll()).thenReturn(Collections.emptyList());

        List<Customer> incomingCustomers = Arrays.asList(customer1, customer2);
        List<Customer> uniqueCustomers = deduplicationEngine.deduplicateCustomers(incomingCustomers);

        assertNotNull(uniqueCustomers, "Unique customers list should not be null");
        assertEquals(2, uniqueCustomers.size(), "Both distinct customers should remain");
        assertTrue(uniqueCustomers.containsAll(Arrays.asList(customer1, customer2)), "Both customers should be present");
        verify(customerRepository, times(1)).findAll();
    }

    @Test
    @DisplayName("Should not deduplicate customers with partial matches (e.g., same name) but no key identifier match")
    void testDeduplicateCustomers_partialMatchNotDuplicate() {
        when(customerRepository.findAll()).thenReturn(Collections.emptyList());

        List<Customer> incomingCustomers = Arrays.asList(customer1, customer4); // customer1 and customer4 have same name, different PAN/Aadhaar
        List<Customer> uniqueCustomers = deduplicationEngine.deduplicateCustomers(incomingCustomers);

        assertNotNull(uniqueCustomers, "Unique customers list should not be null");
        assertEquals(2, uniqueCustomers.size(), "Both customers should remain as they are not duplicates by key identifiers");
        assertTrue(uniqueCustomers.containsAll(Arrays.asList(customer1, customer4)), "Both customers should be present");
        verify(customerRepository, times(1)).findAll();
    }

    @Test
    @DisplayName("Should deduplicate an incoming customer against an existing customer in the 'live book'")
    void testDeduplicateCustomers_againstLiveBook() {
        // Create a live book customer that is a duplicate of customer1 by PAN
        Customer liveBookCustomer = new Customer("C_LB_001", "Live", "Book", "9000000000", "ABCDE1234F", "555566667777", "Consumer Loan");
        when(customerRepository.findAll()).thenReturn(Arrays.asList(liveBookCustomer, customer2)); // Live book contains a duplicate and a distinct customer

        List<Customer> incomingCustomers = Arrays.asList(customer1); // customer1 has same PAN as liveBookCustomer
        List<Customer> uniqueCustomers = deduplicationEngine.deduplicateCustomers(incomingCustomers);

        assertNotNull(uniqueCustomers, "Unique customers list should not be null");
        assertEquals(0, uniqueCustomers.size(), "Incoming customer should be removed as it's a duplicate of a live book entry");
        assertFalse(uniqueCustomers.contains(customer1), "customer1 should not be present");
        verify(customerRepository, times(1)).findAll();
    }

    @Test
    @DisplayName("Should keep an incoming customer if no duplicate is found in the 'live book'")
    void testDeduplicateCustomers_noDuplicateInLiveBook() {
        when(customerRepository.findAll()).thenReturn(Arrays.asList(customer2)); // Live book has only customer2

        List<Customer> incomingCustomers = Arrays.asList(customer1); // customer1 is distinct from customer2
        List<Customer> uniqueCustomers = deduplicationEngine.deduplicateCustomers(incomingCustomers);

        assertNotNull(uniqueCustomers, "Unique customers list should not be null");
        assertEquals(1, uniqueCustomers.size(), "Incoming customer should be kept as no duplicate exists");
        assertTrue(uniqueCustomers.contains(customer1), "customer1 should be present");
        verify(customerRepository, times(1)).findAll();
    }

    @Test
    @DisplayName("Should correctly handle multiple incoming customers with mixed deduplication scenarios")
    void testDeduplicateCustomers_mixedDuplicates() {
        // Setup:
        // customer1 (PAN: ABCDE1234F)
        // customer3 (PAN: ABCDE1234F) - duplicate of customer1
        // customer2 (distinct)
        // customer5 (PAN: LIVEB1234L) - will be in live book
        Customer liveBookCustomer = new Customer("C_LB_001", "Live", "Book", "9000000000", "LIVEB1234L", "555566667777", "Consumer Loan");
        when(customerRepository.findAll()).thenReturn(Arrays.asList(liveBookCustomer));

        List<Customer> incomingCustomers = Arrays.asList(customer1, customer3, customer2, customer5);
        // Expected unique customers:
        // - One of customer1/customer3 (due to batch deduplication)
        // - customer2 (distinct)
        // - customer5 should be removed (duplicate of liveBookCustomer)
        List<Customer> uniqueCustomers = deduplicationEngine.deduplicateCustomers(incomingCustomers);

        assertNotNull(uniqueCustomers, "Unique customers list should not be null");
        assertEquals(2, uniqueCustomers.size(), "Expected 2 unique customers after mixed deduplication");
        // Verify that one of the PAN-duplicates (customer1 or customer3) is present
        assertTrue(uniqueCustomers.contains(customer1) || uniqueCustomers.contains(customer3), "One of customer1/customer3 should be present");
        assertTrue(uniqueCustomers.contains(customer2), "customer2 should be present");
        assertFalse(uniqueCustomers.contains(customer5), "customer5 should be deduped against liveBookCustomer");
        verify(customerRepository, times(1)).findAll();
    }

    // --- Offer Deduplication Tests ---

    @Test
    @DisplayName("Should return an empty list when incoming offer list is null")
    void testDeduplicateOffers_nullIncomingList() {
        List<Offer> result = deduplicationEngine.deduplicateOffers(null);
        assertNotNull(result, "Result list should not be null");
        assertTrue(result.isEmpty(), "Result list should be empty for null input");
        verifyNoInteractions(customerRepository); // No repository interaction expected for null input
    }

    @Test
    @DisplayName("Should return an empty list when incoming offer list is empty")
    void testDeduplicateOffers_emptyIncomingList() {
        List<Offer> result = deduplicationEngine.deduplicateOffers(Collections.emptyList());
        assertNotNull(result, "Result list should not be null");
        assertTrue(result.isEmpty(), "Result list should be empty for empty input");
        verifyNoInteractions(customerRepository); // No repository interaction expected for empty input
    }

    @Test
    @DisplayName("Should deduplicate Top-up loan offers only among themselves within the incoming batch")
    void testDeduplicateOffers_topUpLoanSpecificDedupeBatch() {
        when(customerRepository.findAllOffers()).thenReturn(Collections.emptyList()); // No existing offers

        List<Offer> incomingOffers = Arrays.asList(offer1, offer2, offer3); // offer1, offer2 are Top-up duplicates; offer3 is Preapproved
        List<Offer> uniqueOffers = deduplicationEngine.deduplicateOffers(incomingOffers);

        assertNotNull(uniqueOffers, "Unique offers list should not be null");
        assertEquals(2, uniqueOffers.size(), "Expected one unique Top-up and one unique Preapproved offer");
        assertTrue(uniqueOffers.contains(offer1) || uniqueOffers.contains(offer2), "One of the Top-up offers should be present");
        assertTrue(uniqueOffers.contains(offer3), "The Preapproved offer should be present");
        verify(customerRepository, times(1)).findAllOffers();
    }

    @Test
    @DisplayName("Should deduplicate Top-up loan offers against existing Top-up offers in the 'live book'")
    void testDeduplicateOffers_topUpLoanSpecificDedupeLiveBook() {
        Offer existingTopUp = new Offer("O_LB_001", "C_LB_001", "Top-up Loan", "9876543210", "ABCDE1234F");
        Offer existingPreapproved = new Offer("O_LB_002", "C_LB_002", "Preapproved Loan", "9999999999", "XYZXYZXYZX");

        when(customerRepository.findAllOffers()).thenReturn(Arrays.asList(existingTopUp, existingPreapproved));

        List<Offer> incomingOffers = Arrays.asList(offer1, offer3); // offer1 is Top-up duplicate of existingTopUp; offer3 is Preapproved
        List<Offer> uniqueOffers = deduplicationEngine.deduplicateOffers(incomingOffers);

        assertNotNull(uniqueOffers, "Unique offers list should not be null");
        assertEquals(1, uniqueOffers.size(), "offer1 should be deduped, offer3 should remain");
        assertTrue(uniqueOffers.contains(offer3), "offer3 should be present");
        assertFalse(uniqueOffers.contains(offer1), "offer1 should be removed as it's a duplicate of an existing Top-up offer");
        verify(customerRepository, times(1)).findAllOffers();
    }

    @Test
    @DisplayName("Should NOT deduplicate a Top-up loan offer against a non-Top-up existing offer, even if customer details match")
    void testDeduplicateOffers_topUpLoanNotDedupedAgainstOtherTypes() {
        // existingPreapproved has same customer details (mobile/PAN) as offer1, but is a different offer type
        Offer existingPreapproved = new Offer("O_LB_001", "C001", "Preapproved Loan", "9876543210", "ABCDE1234F");
        when(customerRepository.findAllOffers()).thenReturn(Arrays.asList(existingPreapproved));

        List<Offer> incomingOffers = Arrays.asList(offer1); // offer1 is Top-up
        List<Offer> uniqueOffers = deduplicationEngine.deduplicateOffers(incomingOffers);

        assertNotNull(uniqueOffers, "Unique offers list should not be null");
        assertEquals(1, uniqueOffers.size(), "offer1 should NOT be deduped by existingPreapproved due to type mismatch");
        assertTrue(uniqueOffers.contains(offer1), "offer1 should be present");
        verify(customerRepository, times(1)).findAllOffers();
    }

    @Test
    @DisplayName("Should deduplicate non-Top-up offers against any matching existing offer (general deduplication)")
    void testDeduplicateOffers_otherOfferTypesDedupedGenerally() {
        Offer existingPreapproved = new Offer("O_LB_001", "C002", "Preapproved Loan", "9988776655", "FGHIJ5678K");
        // This existing Top-up offer should not affect the deduplication of offer3 (Preapproved)
        Offer existingTopUp = new Offer("O_LB_002", "C001", "Top-up Loan", "9876543210", "ABCDE1234F");

        when(customerRepository.findAllOffers()).thenReturn(Arrays.asList(existingPreapproved, existingTopUp));

        List<Offer> incomingOffers = Arrays.asList(offer3); // offer3 is Preapproved, duplicate of existingPreapproved
        List<Offer> uniqueOffers = deduplicationEngine.deduplicateOffers(incomingOffers);

        assertNotNull(uniqueOffers, "Unique offers list should not be null");
        assertEquals(0, uniqueOffers.size(), "offer3 should be deduped against existingPreapproved");
        assertFalse(uniqueOffers.contains(offer3), "offer3 should not be present");
        verify(customerRepository, times(1)).findAllOffers();
    }

    @Test
    @DisplayName("Should correctly handle mixed incoming offers with various deduplication scenarios")
    void testDeduplicateOffers_mixedScenarios() {
        // Existing offers in live book
        Offer existingTopUp1 = new Offer("O_LB_TU1", "C_LB_TU1", "Top-up Loan", "1111111111", "PAN1111");
        Offer existingPreapproved1 = new Offer("O_LB_PA1", "C_LB_PA1", "Preapproved Loan", "2222222222", "PAN2222");
        when(customerRepository.findAllOffers()).thenReturn(Arrays.asList(existingTopUp1, existingPreapproved1));

        // Incoming offers for testing
        Offer incomingTopUpDuplicateOfExisting = new Offer("O_INC_TU1", "C_INC_TU1", "Top-up Loan", "1111111111", "PAN1111"); // Duplicate of existingTopUp1
        Offer incomingTopUpNew = new Offer("O_INC_TU2", "C_INC_TU2", "Top-up Loan", "3333333333", "PAN3333"); // New Top-up
        Offer incomingPreapprovedDuplicateOfExisting = new Offer("O_INC_PA1", "C_INC_PA1", "Preapproved Loan", "2222222222", "PAN2222"); // Duplicate of existingPreapproved1
        Offer incomingPreapprovedNew = new Offer("O_INC_PA2", "C_INC_PA2", "Preapproved Loan", "4444444444", "PAN4444"); // New Preapproved
        Offer incomingTopUpBatchDuplicate = new Offer("O_INC_TU3", "C_INC_TU1", "Top-up Loan", "1111111111", "PAN1111"); // Batch duplicate of incomingTopUpDuplicateOfExisting

        List<Offer> incomingOffers = Arrays.asList(
                incomingTopUpDuplicateOfExisting,
                incomingTopUpNew,
                incomingPreapprovedDuplicateOfExisting,
                incomingPreapprovedNew,
                incomingTopUpBatchDuplicate
        );

        List<Offer> uniqueOffers = deduplicationEngine.deduplicateOffers(incomingOffers);

        assertNotNull(uniqueOffers, "Unique offers list should not be null");
        assertEquals(2, uniqueOffers.size(), "Expected 2 unique offers after mixed deduplication");

        // Verify that duplicates are removed
        assertFalse(uniqueOffers.contains(incomingTopUpDuplicateOfExisting), "incomingTopUpDuplicateOfExisting should be deduped");
        assertFalse(uniqueOffers.contains(incomingTopUpBatchDuplicate), "incomingTopUpBatchDuplicate should be deduped");
        assertFalse(uniqueOffers.contains(incomingPreapprovedDuplicateOfExisting), "incomingPreapprovedDuplicateOfExisting should be deduped");

        // Verify that new, unique offers are present
        assertTrue(uniqueOffers.contains(incomingTopUpNew), "incomingTopUpNew should be present");
        assertTrue(uniqueOffers.contains(incomingPreapprovedNew), "incomingPreapprovedNew should be present");

        verify(customerRepository, times(1)).findAllOffers();
    }
}

// --- Start of assumed model definitions for test context ---
// These classes are defined here to make the test file self-contained and directly runnable.
// In a real project, these would typically be imported from 'com.ltfs.cdp.customer.model' package.

/**
 * Simplified Customer model for testing purposes.
 * Represents a customer entity with key identifiers for deduplication.
 */
class Customer {
    private String customerId;
    private String firstName;
    private String lastName;
    private String mobileNumber;
    private String pan;
    private String aadhaar;
    private String productType; // e.g., "Consumer Loan", "Top-up Loan"

    public Customer(String customerId, String firstName, String lastName, String mobileNumber, String pan, String aadhaar, String productType) {
        this.customerId = customerId;
        this.firstName = firstName;
        this.lastName = lastName;
        this.mobileNumber = mobileNumber;
        this.pan = pan;
        this.aadhaar = aadhaar;
        this.productType = productType;
    }

    // Getters
    public String getCustomerId() { return customerId; }
    public String getFirstName() { return firstName; }
    public String getLastName() { return lastName; }
    public String getMobileNumber() { return mobileNumber; }
    public String getPan() { return pan; }
    public String getAadhaar() { return aadhaar; }
    public String getProductType() { return productType; }

    // Setters (optional for test, but good practice for POJOs)
    public void setCustomerId(String customerId) { this.customerId = customerId; }
    public void setFirstName(String firstName) { this.firstName = firstName; }
    public void setLastName(String lastName) { this.lastName = lastName; }
    public void setMobileNumber(String mobileNumber) { this.mobileNumber = mobileNumber; }
    public void setPan(String pan) { this.pan = pan; }
    public void setAadhaar(String aadhaar) { this.aadhaar = aadhaar; }
    public void setProductType(String productType) { this.productType = productType; }

    /**
     * Overrides equals for object comparison, crucial for deduplication logic.
     * Compares all fields for equality.
     */
    @Override
    public boolean equals(Object o) {
        if (this == o) return true;
        if (o == null || getClass() != o.getClass()) return false;
        Customer customer = (Customer) o;
        return Objects.equals(customerId, customer.customerId) &&
               Objects.equals(firstName, customer.firstName) &&
               Objects.equals(lastName, customer.lastName) &&
               Objects.equals(mobileNumber, customer.mobileNumber) &&
               Objects.equals(pan, customer.pan) &&
               Objects.equals(aadhaar, customer.aadhaar) &&
               Objects.equals(productType, customer.productType);
    }

    /**
     * Overrides hashCode, consistent with equals.
     */
    @Override
    public int hashCode() {
        return Objects.hash(customerId, firstName, lastName, mobileNumber, pan, aadhaar, productType);
    }

    /**
     * Provides a string representation for debugging.
     */
    @Override
    public String toString() {
        return "Customer{" +
               "customerId='" + customerId + '\'' +
               ", firstName='" + firstName + '\'' +
               ", mobileNumber='" + mobileNumber + '\'' +
               ", pan='" + pan + '\'' +
               ", aadhaar='" + aadhaar + '\'' +
               ", productType='" + productType + '\'' +
               '}';
    }
}

/**
 * Simplified Offer model for testing purposes.
 * Represents an offer entity, linked to a customer and having an offer type.
 */
class Offer {
    private String offerId;
    private String customerId; // Link to customer
    private String offerType; // e.g., "Top-up Loan", "Preapproved Loan"
    private String mobileNumber; // For offer-level dedupe, often derived from customer
    private String pan; // For offer-level dedupe, often derived from customer

    public Offer(String offerId, String customerId, String offerType, String mobileNumber, String pan) {
        this.offerId = offerId;
        this.customerId = customerId;
        this.offerType = offerType;
        this.mobileNumber = mobileNumber;
        this.pan = pan;
    }

    // Getters
    public String getOfferId() { return offerId; }
    public String getCustomerId() { return customerId; }
    public String getOfferType() { return offerType; }
    public String getMobileNumber() { return mobileNumber; }
    public String getPan() { return pan; }

    // Setters (optional for test)
    public void setOfferId(String offerId) { this.offerId = offerId; }
    public void setCustomerId(String customerId) { this.customerId = customerId; }
    public void setOfferType(String offerType) { this.offerType = offerType; }
    public void setMobileNumber(String mobileNumber) { this.mobileNumber = mobileNumber; }
    public void setPan(String pan) { this.pan = pan; }

    /**
     * Overrides equals for object comparison, crucial for deduplication logic.
     * Compares all fields for equality.
     */
    @Override
    public boolean equals(Object o) {
        if (this == o) return true;
        if (o == null || getClass() != o.getClass()) return false;
        Offer offer = (Offer) o;
        return Objects.equals(offerId, offer.offerId) &&
               Objects.equals(customerId, offer.customerId) &&
               Objects.equals(offerType, offer.offerType) &&
               Objects.equals(mobileNumber, offer.mobileNumber) &&
               Objects.equals(pan, offer.pan);
    }

    /**
     * Overrides hashCode, consistent with equals.
     */
    @Override
    public int hashCode() {
        return Objects.hash(offerId, customerId, offerType, mobileNumber, pan);
    }

    /**
     * Provides a string representation for debugging.
     */
    @Override
    public String toString() {
        return "Offer{" +
               "offerId='" + offerId + '\'' +
               ", customerId='" + customerId + '\'' +
               ", offerType='" + offerType + '\'' +
               ", mobileNumber='" + mobileNumber + '\'' +
               ", pan='" + pan + '\'' +
               '}';
    }
}

/**
 * Mock interface for CustomerRepository.
 * In a real application, this would be a Spring Data JPA repository.
 * Defined here for test self-containment.
 */
interface CustomerRepository {
    /**
     * Simulates fetching all existing customers from the 'live book'.
     * @return A list of all customers.
     */
    List<Customer> findAll();

    /**
     * Simulates fetching all existing offers from the 'live book'.
     * @return A list of all offers.
     */
    List<Offer> findAllOffers();
}
// --- End of assumed model definitions for test context ---

// --- Start of assumed DeduplicationEngine implementation for test context ---
// This class is defined here to make the test file self-contained and directly runnable.
// In a real project, this would typically be in 'com.ltfs.cdp.customer.service' package.

/**
 * A simplified DeduplicationEngine implementation for testing purposes.
 * This class encapsulates the core deduplication logic for customers and offers.
 * It interacts with a {@link CustomerRepository} to fetch existing data from the 'live book'.
 *
 * <p>Deduplication Rules (simplified for this test context):</p>
 * <ul>
 *     <li>Customers are considered duplicates if they have the same PAN or Aadhaar number.</li>
 *     <li>Offers are considered duplicates if they have the same PAN or Mobile Number.</li>
 *     <li>Special Rule for Offers: Top-up loan offers are only deduped against other Top-up loan offers.
 *         Other offer types are deduped generally against all non-Top-up existing offers.</li>
 * </ul>
 */
class DeduplicationEngine {

    private final CustomerRepository customerRepository;

    /**
     * Constructs a DeduplicationEngine with a CustomerRepository dependency.
     * @param customerRepository The repository to access customer and offer data.
     */
    public DeduplicationEngine(CustomerRepository customerRepository) {
        this.customerRepository = customerRepository;
    }

    /**
     * Deduplicates a list of incoming customers against the existing customer base (live book)
     * and against other customers within the incoming batch.
     * Customers are considered duplicates if they have the same PAN or Aadhaar number.
     *
     * @param incomingCustomers The list of new customers to be deduplicated.
     * @return A list of unique customers after deduplication.
     */
    public List<Customer> deduplicateCustomers(List<Customer> incomingCustomers) {
        if (incomingCustomers == null || incomingCustomers.isEmpty()) {
            return new ArrayList<>();
        }

        List<Customer> uniqueCustomers = new ArrayList<>();
        // Fetch all existing customers from the live book for comparison
        List<Customer> existingCustomers = customerRepository.findAll();

        for (Customer newCustomer : incomingCustomers) {
            boolean isDuplicate = false;

            // 1. Check for duplicates within the already processed unique customers in the current batch
            // This ensures that if multiple duplicates come in the same batch, only the first one is kept.
            for (Customer processedUnique : uniqueCustomers) {
                if (isCustomerDuplicate(newCustomer, processedUnique)) {
                    isDuplicate = true;
                    break;
                }
            }

            if (!isDuplicate) {
                // 2. If not a duplicate within the batch, check against existing customers in the live book
                for (Customer existingCustomer : existingCustomers) {
                    if (isCustomerDuplicate(newCustomer, existingCustomer)) {
                        isDuplicate = true;
                        break;
                    }
                }
            }

            // If no duplicate found, add the new customer to the unique list
            if (!isDuplicate) {
                uniqueCustomers.add(newCustomer);
            }
        }
        return uniqueCustomers;
    }

    /**
     * Deduplicates a list of incoming offers based on specific rules.
     * Special rule: Top-up loan offers are only deduped against other Top-up loan offers.
     * Other offer types are deduped based on customer PAN/Mobile Number.
     *
     * @param incomingOffers The list of new offers to be deduplicated.
     * @return A list of unique offers after deduplication.
     */
    public List<Offer> deduplicateOffers(List<Offer> incomingOffers) {
        if (incomingOffers == null || incomingOffers.isEmpty()) {
            return new ArrayList<>();
        }

        List<Offer> uniqueOffers = new ArrayList<>();
        // Fetch all existing offers from the live book
        List<Offer> existingOffers = customerRepository.findAllOffers();

        // Separate incoming offers by type for specific deduplication logic
        List<Offer> incomingTopUpOffers = incomingOffers.stream()
                .filter(offer -> "Top-up Loan".equalsIgnoreCase(offer.getOfferType()))
                .collect(Collectors.toList());

        List<Offer> incomingOtherOffers = incomingOffers.stream()
                .filter(offer -> !"Top-up Loan".equalsIgnoreCase(offer.getOfferType()))
                .collect(Collectors.toList());

        // Separate existing offers by type
        List<Offer> existingTopUpOffers = existingOffers.stream()
                .filter(offer -> "Top-up Loan".equalsIgnoreCase(offer.getOfferType()))
                .collect(Collectors.toList());

        List<Offer> existingOtherOffers = existingOffers.stream()
                .filter(offer -> !"Top-up Loan".equalsIgnoreCase(offer.getOfferType()))
                .collect(Collectors.toList());

        // 1. Deduplicate Top-up offers: only against other Top-up offers (both incoming batch and live book)
        for (Offer newOffer : incomingTopUpOffers) {
            boolean isDuplicate = false;
            // Check against already processed unique Top-up offers in the current batch
            for (Offer processedUnique : uniqueOffers) {
                if ("Top-up Loan".equalsIgnoreCase(processedUnique.getOfferType()) && isOfferDuplicate(newOffer, processedUnique)) {
                    isDuplicate = true;
                    break;
                }
            }

            if (!isDuplicate) {
                // Check against existing Top-up offers in the live book
                for (Offer existingTopUpOffer : existingTopUpOffers) {
                    if (isOfferDuplicate(newOffer, existingTopUpOffer)) {
                        isDuplicate = true;
                        break;
                    }
                }
            }

            if (!isDuplicate) {
                uniqueOffers.add(newOffer);
            }
        }

        // 2. Deduplicate other offers: against any matching offer (both incoming batch and live book)
        for (Offer newOffer : incomingOtherOffers) {
            boolean isDuplicate = false;
            // Check against already processed unique offers (including Top-up if they match general criteria)
            for (Offer processedUnique : uniqueOffers) {
                if (isOfferDuplicate(newOffer, processedUnique)) { // General offer dedupe logic
                    isDuplicate = true;
                    break;
                }
            }

            if (!isDuplicate) {
                // Check against existing other offers in the live book
                for (Offer existingOtherOffer : existingOtherOffers) {
                    if (isOfferDuplicate(newOffer, existingOtherOffer)) {
                        isDuplicate = true;
                        break;
                    }
                }
            }

            if (!isDuplicate) {
                uniqueOffers.add(newOffer);
            }
        }

        return uniqueOffers;
    }

    /**
     * Helper method to determine if two customers are duplicates based on key identifiers.
     * Criteria: Same PAN or same Aadhaar number.
     *
     * @param c1 Customer 1
     * @param c2 Customer 2
     * @return true if duplicates, false otherwise.
     */
    private boolean isCustomerDuplicate(Customer c1, Customer c2) {
        if (c1 == null || c2 == null) {
            return false;
        }
        // Check for PAN match (case-insensitive and non-null)
        if (c1.getPan() != null && c2.getPan() != null && c1.getPan().equalsIgnoreCase(c2.getPan())) {
            return true;
        }
        // Check for Aadhaar match (case-insensitive and non-null)
        if (c1.getAadhaar() != null && c2.getAadhaar() != null && c1.getAadhaar().equalsIgnoreCase(c2.getAadhaar())) {
            return true;
        }
        return false;
    }

    /**
     * Helper method to determine if two offers are duplicates based on associated customer identifiers.
     * Criteria: Same PAN or same Mobile Number.
     *
     * @param o1 Offer 1
     * @param o2 Offer 2
     * @return true if duplicates, false otherwise.
     */
    private boolean isOfferDuplicate(Offer o1, Offer o2) {
        if (o1 == null || o2 == null) {
            return false;
        }
        // Check for PAN match (case-insensitive and non-null)
        if (o1.getPan() != null && o2.getPan() != null && o1.getPan().equalsIgnoreCase(o2.getPan())) {
            return true;
        }
        // Check for Mobile Number match (case-insensitive and non-null)
        if (o1.getMobileNumber() != null && o2.getMobileNumber() != null && o1.getMobileNumber().equalsIgnoreCase(o2.getMobileNumber())) {
            return true;
        }
        return false;
    }
}
// --- End of assumed DeduplicationEngine implementation for test context ---
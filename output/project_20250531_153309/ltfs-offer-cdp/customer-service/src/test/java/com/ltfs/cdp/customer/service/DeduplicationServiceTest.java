package com.ltfs.cdp.customer.service;

import com.ltfs.cdp.customer.model.CustomerProfile;
import com.ltfs.cdp.customer.repository.CustomerRepository;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

import java.util.Arrays;
import java.util.Collections;
import java.util.List;
import java.util.Optional;
import java.util.Set;
import java.util.HashSet;
import java.util.stream.Collectors;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.*;

/**
 * Unit tests for the {@link DeduplicationService}.
 * This class focuses on testing the core deduplication logic, including
 * internal deduplication within incoming data and deduplication against
 * existing customer data (the 'live book' / Customer 360).
 * Special attention is given to the "Top-up Loan" specific deduplication rule.
 */
@ExtendWith(MockitoExtension.class)
class DeduplicationServiceTest {

    /**
     * Mock of the CustomerRepository dependency.
     * Used to simulate interactions with the 'live book' (Customer 360).
     */
    @Mock
    private CustomerRepository customerRepository;

    /**
     * The service under test, with mocked dependencies injected.
     */
    @InjectMocks
    private DeduplicationService deduplicationService;

    /**
     * Helper method to create a {@link CustomerProfile} instance for testing.
     *
     * @param customerId   Unique identifier for the customer profile.
     * @param pan          PAN number, a key deduplication criterion.
     * @param mobile       Mobile number, another key deduplication criterion.
     * @param productType  Product type, crucial for "Top-up Loan" specific logic.
     * @return A new CustomerProfile instance.
     */
    private CustomerProfile createCustomerProfile(String customerId, String pan, String mobile, String productType) {
        CustomerProfile profile = new CustomerProfile();
        profile.setCustomerId(customerId);
        profile.setPan(pan);
        profile.setMobileNumber(mobile);
        profile.setProductType(productType);
        profile.setFirstName("Test");
        profile.setLastName("Customer");
        profile.setEmail("test@example.com");
        return profile;
    }

    /**
     * Setup method executed before each test.
     * Currently empty as MockitoExtension handles mock initialization.
     */
    @BeforeEach
    void setUp() {
        // No specific setup needed here as @Mock and @InjectMocks handle injection
        // and MockitoExtension resets mocks before each test.
    }

    /**
     * Test case: All incoming customers are unique and no matches are found in the existing data.
     * Expectation: All incoming customers should be returned as unique.
     */
    @Test
    @DisplayName("Should return all customers when no duplicates exist in incoming or existing data")
    void shouldReturnAllCustomersWhenNoDuplicates() {
        // Given
        CustomerProfile customer1 = createCustomerProfile("C001", "PAN123", "9876543210", "Loyalty");
        CustomerProfile customer2 = createCustomerProfile("C002", "PAN456", "9876543211", "Preapproved");

        List<CustomerProfile> incomingCustomers = Arrays.asList(customer1, customer2);

        // Mock: No existing customer found for any incoming PAN/Mobile
        when(customerRepository.findByPanOrMobile(anyString(), anyString())).thenReturn(Optional.empty());

        // When
        List<CustomerProfile> uniqueCustomers = deduplicationService.deduplicate(incomingCustomers);

        // Then
        assertNotNull(uniqueCustomers, "Unique customers list should not be null");
        assertEquals(2, uniqueCustomers.size(), "Expected 2 unique customers");
        assertTrue(uniqueCustomers.contains(customer1), "Customer 1 should be in the unique list");
        assertTrue(uniqueCustomers.contains(customer2), "Customer 2 should be in the unique list");

        // Verify that the repository was queried for each incoming customer
        verify(customerRepository, times(1)).findByPanOrMobile(customer1.getPan(), customer1.getMobileNumber());
        verify(customerRepository, times(1)).findByPanOrMobile(customer2.getPan(), customer2.getMobileNumber());
    }

    /**
     * Test case: An incoming customer has a PAN that matches an existing customer in the 'live book'.
     * Expectation: The incoming customer should be identified as a duplicate and not returned.
     */
    @Test
    @DisplayName("Should deduplicate incoming customers based on PAN match with existing customer")
    void shouldDeduplicateIncomingByPanWithExisting() {
        // Given
        CustomerProfile existingCustomer = createCustomerProfile("C_EXISTING_001", "PAN_DUP", "9999999999", "Loyalty");
        CustomerProfile incomingCustomer = createCustomerProfile("C_INCOMING_001", "PAN_DUP", "8888888888", "Preapproved"); // Same PAN, different mobile

        List<CustomerProfile> incomingCustomers = Collections.singletonList(incomingCustomer);

        // Mock: An existing customer is found by PAN/Mobile (even if mobile differs, PAN match is enough)
        when(customerRepository.findByPanOrMobile(incomingCustomer.getPan(), incomingCustomer.getMobileNumber()))
                .thenReturn(Optional.of(existingCustomer));

        // When
        List<CustomerProfile> uniqueCustomers = deduplicationService.deduplicate(incomingCustomers);

        // Then
        assertNotNull(uniqueCustomers, "Unique customers list should not be null");
        assertEquals(0, uniqueCustomers.size(), "Incoming customer should be deduped if a match exists in live book");

        // Verify repository call
        verify(customerRepository, times(1)).findByPanOrMobile(incomingCustomer.getPan(), incomingCustomer.getMobileNumber());
    }

    /**
     * Test case: An incoming customer has a Mobile Number that matches an existing customer in the 'live book'.
     * Expectation: The incoming customer should be identified as a duplicate and not returned.
     */
    @Test
    @DisplayName("Should deduplicate incoming customers based on Mobile match with existing customer")
    void shouldDeduplicateIncomingByMobileWithExisting() {
        // Given
        CustomerProfile existingCustomer = createCustomerProfile("C_EXISTING_002", "PAN_DIFF", "9999999998", "Loyalty");
        CustomerProfile incomingCustomer = createCustomerProfile("C_INCOMING_002", "PAN_ANOTHER", "9999999998", "E-aggregator"); // Same Mobile, different PAN

        List<CustomerProfile> incomingCustomers = Collections.singletonList(incomingCustomer);

        // Mock: An existing customer is found by PAN/Mobile (even if PAN differs, Mobile match is enough)
        when(customerRepository.findByPanOrMobile(incomingCustomer.getPan(), incomingCustomer.getMobileNumber()))
                .thenReturn(Optional.of(existingCustomer));

        // When
        List<CustomerProfile> uniqueCustomers = deduplicationService.deduplicate(incomingCustomers);

        // Then
        assertNotNull(uniqueCustomers, "Unique customers list should not be null");
        assertEquals(0, uniqueCustomers.size(), "Incoming customer should be deduped if a match exists in live book");

        // Verify repository call
        verify(customerRepository, times(1)).findByPanOrMobile(incomingCustomer.getPan(), incomingCustomer.getMobileNumber());
    }

    /**
     * Test case: Multiple incoming customers have internal duplicates (same PAN or Mobile).
     * Expectation: Only one representative of the duplicate group should be kept.
     * (Assuming the service keeps the first encountered or a prioritized one).
     */
    @Test
    @DisplayName("Should deduplicate multiple incoming customers with internal duplicates")
    void shouldDeduplicateInternalIncomingDuplicates() {
        // Given
        CustomerProfile customerA = createCustomerProfile("C003", "PAN_X", "1111111111", "Loyalty");
        CustomerProfile customerB = createCustomerProfile("C004", "PAN_X", "2222222222", "Preapproved"); // Duplicate PAN with A
        CustomerProfile customerC = createCustomerProfile("C005", "PAN_Y", "1111111111", "E-aggregator"); // Duplicate Mobile with A
        CustomerProfile customerD = createCustomerProfile("C006", "PAN_Z", "3333333333", "Loyalty"); // Unique

        List<CustomerProfile> incomingCustomers = Arrays.asList(customerA, customerB, customerC, customerD);

        // Mock: No existing customers for these PAN/Mobile combinations
        when(customerRepository.findByPanOrMobile(anyString(), anyString())).thenReturn(Optional.empty());

        // When
        List<CustomerProfile> uniqueCustomers = deduplicationService.deduplicate(incomingCustomers);

        // Then
        assertNotNull(uniqueCustomers, "Unique customers list should not be null");
        // Expected: customerA (as it's first for PAN_X/1111111111) and customerD should remain.
        // customerB (duplicate PAN_X) and customerC (duplicate 1111111111) should be removed.
        assertEquals(2, uniqueCustomers.size(), "Expected 2 unique customers after internal deduplication");
        assertTrue(uniqueCustomers.contains(customerA), "Customer A should be kept as a representative");
        assertTrue(uniqueCustomers.contains(customerD), "Customer D should be kept as it's unique");
        assertFalse(uniqueCustomers.contains(customerB), "Customer B should be removed as a duplicate of A");
        assertFalse(uniqueCustomers.contains(customerC), "Customer C should be removed as a duplicate of A");

        // Verify repository calls for each incoming customer (before internal deduplication)
        verify(customerRepository, times(1)).findByPanOrMobile(customerA.getPan(), customerA.getMobileNumber());
        verify(customerRepository, times(1)).findByPanOrMobile(customerB.getPan(), customerB.getMobileNumber());
        verify(customerRepository, times(1)).findByPanOrMobile(customerC.getPan(), customerC.getMobileNumber());
        verify(customerRepository, times(1)).findByPanOrMobile(customerD.getPan(), customerD.getMobileNumber());
    }

    /**
     * Test case: An empty list of incoming customers is provided.
     * Expectation: An empty list should be returned, and no repository interactions should occur.
     */
    @Test
    @DisplayName("Should handle empty incoming customer list gracefully")
    void shouldHandleEmptyIncomingList() {
        // Given
        List<CustomerProfile> incomingCustomers = Collections.emptyList();

        // When
        List<CustomerProfile> uniqueCustomers = deduplicationService.deduplicate(incomingCustomers);

        // Then
        assertNotNull(uniqueCustomers, "Unique customers list should not be null for empty input");
        assertTrue(uniqueCustomers.isEmpty(), "Unique customers list should be empty for empty input");
        verifyNoInteractions(customerRepository); // Ensure no calls to the repository
    }

    /**
     * Test case: Specific deduplication logic for "Top-up Loan" offers.
     * "Top-up loan offers must be deduped only within other Top-up offers, and matches found should be remo"
     * Expectation: Top-up loans are deduped among themselves, while other loans are deduped normally.
     */
    @Test
    @DisplayName("Should apply specific deduplication logic for Top-up loan offers")
    void shouldDeduplicateTopUpLoansSeparately() {
        // Given
        CustomerProfile topUp1 = createCustomerProfile("TU001", "PAN_TU1", "5555555551", "Top-up Loan");
        CustomerProfile topUp2 = createCustomerProfile("TU002", "PAN_TU1", "5555555552", "Top-up Loan"); // Duplicate PAN with TU1
        CustomerProfile topUp3 = createCustomerProfile("TU003", "PAN_TU3", "5555555551", "Top-up Loan"); // Duplicate Mobile with TU1
        CustomerProfile regularLoan = createCustomerProfile("RL001", "PAN_RL1", "6666666661", "Loyalty"); // Non-Top-up
        CustomerProfile topUp4 = createCustomerProfile("TU004", "PAN_TU4", "5555555554", "Top-up Loan"); // Unique Top-up

        List<CustomerProfile> incomingCustomers = Arrays.asList(topUp1, topUp2, topUp3, regularLoan, topUp4);

        // Mock: No existing customers for these PAN/Mobile combinations
        when(customerRepository.findByPanOrMobile(anyString(), anyString())).thenReturn(Optional.empty());

        // When
        List<CustomerProfile> uniqueCustomers = deduplicationService.deduplicate(incomingCustomers);

        // Then
        assertNotNull(uniqueCustomers, "Unique customers list should not be null");
        // Expected:
        // - From (TU1, TU2, TU3), only one (e.g., TU1) should remain due to internal top-up deduplication.
        // - regularLoan should remain.
        // - topUp4 should remain.
        // Total expected unique customers: 1 (from TU group) + 1 (regular) + 1 (TU4) = 3.
        assertEquals(3, uniqueCustomers.size(), "Expected 3 unique customers after specific top-up deduplication");

        assertTrue(uniqueCustomers.contains(regularLoan), "Regular loan should be present");
        assertTrue(uniqueCustomers.contains(topUp4), "Unique Top-up loan should be present");

        // Verify that exactly one of the duplicate top-up loans (TU1, TU2, TU3) is present
        long topUpDuplicatesCount = uniqueCustomers.stream()
                .filter(c -> "Top-up Loan".equalsIgnoreCase(c.getProductType()) &&
                        (c.getCustomerId().equals("TU001") || c.getCustomerId().equals("TU002") || c.getCustomerId().equals("TU003")))
                .count();
        assertEquals(1, topUpDuplicatesCount, "Only one of the duplicate Top-up loans (TU1, TU2, TU3) should remain.");

        // Verify repository calls for each incoming customer
        verify(customerRepository, times(1)).findByPanOrMobile(topUp1.getPan(), topUp1.getMobileNumber());
        verify(customerRepository, times(1)).findByPanOrMobile(topUp2.getPan(), topUp2.getMobileNumber());
        verify(customerRepository, times(1)).findByPanOrMobile(topUp3.getPan(), topUp3.getMobileNumber());
        verify(customerRepository, times(1)).findByPanOrMobile(regularLoan.getPan(), regularLoan.getMobileNumber());
        verify(customerRepository, times(1)).findByPanOrMobile(topUp4.getPan(), topUp4.getMobileNumber());
    }

    /**
     * Test case: An incoming customer is an exact match (PAN and Mobile) to an existing customer.
     * Expectation: The incoming customer should be ignored, prioritizing the existing 'live book' entry.
     */
    @Test
    @DisplayName("Should prioritize existing customer over incoming duplicate")
    void shouldPrioritizeExistingCustomer() {
        // Given
        CustomerProfile existingCustomer = createCustomerProfile("C_LIVE_001", "PAN_PRIORITY", "7777777777", "Loyalty");
        CustomerProfile incomingCustomer = createCustomerProfile("C_NEW_001", "PAN_PRIORITY", "7777777777", "Preapproved"); // Exact match

        List<CustomerProfile> incomingCustomers = Collections.singletonList(incomingCustomer);

        // Mock: An existing customer is found with matching PAN and Mobile
        when(customerRepository.findByPanOrMobile(incomingCustomer.getPan(), incomingCustomer.getMobileNumber()))
                .thenReturn(Optional.of(existingCustomer));

        // When
        List<CustomerProfile> uniqueCustomers = deduplicationService.deduplicate(incomingCustomers);

        // Then
        assertNotNull(uniqueCustomers, "Unique customers list should not be null");
        assertEquals(0, uniqueCustomers.size(), "Incoming exact duplicate should not be added if existing customer is found.");

        // Verify repository call
        verify(customerRepository, times(1)).findByPanOrMobile(incomingCustomer.getPan(), incomingCustomer.getMobileNumber());
    }

    /**
     * Test case: Incoming customers have null PAN or Mobile numbers.
     * Expectation: The service should handle nulls gracefully. If a null field is a deduplication criterion,
     * it should not cause errors and should be treated as unique unless other non-null criteria match.
     */
    @Test
    @DisplayName("Should handle null PAN or Mobile gracefully")
    void shouldHandleNullPanOrMobile() {
        // Given
        CustomerProfile customerWithNullPan = createCustomerProfile("C007", null, "4444444444", "Loyalty");
        CustomerProfile customerWithNullMobile = createCustomerProfile("C008", "PAN_NULL_MOB", null, "Preapproved");
        CustomerProfile uniqueCustomer = createCustomerProfile("C009", "PAN_UNIQUE", "5555555555", "E-aggregator");

        List<CustomerProfile> incomingCustomers = Arrays.asList(customerWithNullPan, customerWithNullMobile, uniqueCustomer);

        // Mock: No existing customers found for these combinations.
        // Mockito's anyString() handles nulls passed to String arguments.
        when(customerRepository.findByPanOrMobile(anyString(), anyString())).thenReturn(Optional.empty());
        // Explicitly mock for nulls if the service passes them as-is
        when(customerRepository.findByPanOrMobile(eq(null), eq("4444444444"))).thenReturn(Optional.empty());
        when(customerRepository.findByPanOrMobile(eq("PAN_NULL_MOB"), eq(null))).thenReturn(Optional.empty());


        // When
        List<CustomerProfile> uniqueCustomers = deduplicationService.deduplicate(incomingCustomers);

        // Then
        assertNotNull(uniqueCustomers, "Unique customers list should not be null");
        assertEquals(3, uniqueCustomers.size(), "Expected all 3 customers to be unique as no strong matches exist");
        assertTrue(uniqueCustomers.contains(customerWithNullPan), "Customer with null PAN should be included");
        assertTrue(uniqueCustomers.contains(customerWithNullMobile), "Customer with null Mobile should be included");
        assertTrue(uniqueCustomers.contains(uniqueCustomer), "Unique customer should be included");

        // Verify repository calls, ensuring they were attempted even with nulls
        verify(customerRepository, times(1)).findByPanOrMobile(customerWithNullPan.getPan(), customerWithNullPan.getMobileNumber());
        verify(customerRepository, times(1)).findByPanOrMobile(customerWithNullMobile.getPan(), customerWithNullMobile.getMobileNumber());
        verify(customerRepository, times(1)).findByPanOrMobile(uniqueCustomer.getPan(), uniqueCustomer.getMobileNumber());
    }
}

/**
 * Dummy CustomerProfile class for testing purposes.
 * In a real project, this would be a proper DTO/Entity class located in
 * `src/main/java/com/ltfs/cdp/customer/model/CustomerProfile.java`.
 * It's included here to make the test file self-contained and directly runnable.
 */
class CustomerProfile {
    private String customerId;
    private String pan;
    private String mobileNumber;
    private String productType;
    private String firstName;
    private String lastName;
    private String email;

    // Getters and Setters
    public String getCustomerId() { return customerId; }
    public void setCustomerId(String customerId) { this.customerId = customerId; }
    public String getPan() { return pan; }
    public void setPan(String pan) { this.pan = pan; }
    public String getMobileNumber() { return mobileNumber; }
    public void setMobileNumber(String mobileNumber) { this.mobileNumber = mobileNumber; }
    public String getProductType() { return productType; }
    public void setProductType(String productType) { this.productType = productType; }
    public String getFirstName() { return firstName; }
    public void setFirstName(String firstName) { this.firstName = firstName; }
    public String getLastName() { return lastName; }
    public void setLastName(String lastName) { this.lastName = lastName; }
    public String getEmail() { return email; }
    public void setEmail(String email) { this.email = email; }

    /**
     * Overrides equals for proper comparison in test assertions (e.g., List.contains()).
     * For test purposes, equality is based on customerId.
     */
    @Override
    public boolean equals(Object o) {
        if (this == o) return true;
        if (o == null || getClass() != o.getClass()) return false;
        CustomerProfile that = (CustomerProfile) o;
        return customerId != null ? customerId.equals(that.customerId) : that.customerId == null;
    }

    /**
     * Overrides hashCode consistent with equals.
     */
    @Override
    public int hashCode() {
        return customerId != null ? customerId.hashCode() : 0;
    }
}

/**
 * Dummy DeduplicationService class for testing purposes.
 * This is a simplified implementation that mimics the expected behavior
 * for the unit tests. In a real project, this would contain the actual
 * complex deduplication business logic and would be located in
 * `src/main/java/com/ltfs/cdp/customer/service/DeduplicationService.java`.
 */
class DeduplicationService {

    private final CustomerRepository customerRepository;

    /**
     * Constructor for dependency injection.
     * @param customerRepository The repository to interact with the 'live book'.
     */
    public DeduplicationService(CustomerRepository customerRepository) {
        this.customerRepository = customerRepository;
    }

    /**
     * Performs deduplication on a list of incoming customer profiles.
     * The logic involves:
     * 1. Separating "Top-up Loan" profiles for special handling.
     * 2. Performing internal deduplication within the "Top-up Loan" group.
     * 3. Performing internal deduplication within the "Other Loan" group.
     * 4. For each internally unique customer, checking against the 'live book' (Customer 360)
     *    via the {@link CustomerRepository}.
     * 5. If an incoming customer is a duplicate of an existing 'live book' entry, it is discarded.
     *
     * @param incomingCustomers The list of customer profiles to deduplicate.
     * @return A list of unique customer profiles that are deemed new and should be processed/added.
     */
    public List<CustomerProfile> deduplicate(List<CustomerProfile> incomingCustomers) {
        if (incomingCustomers == null || incomingCustomers.isEmpty()) {
            return Collections.emptyList();
        }

        // Separate Top-up loans from other products for special handling as per requirements
        List<CustomerProfile> topUpLoans = incomingCustomers.stream()
                .filter(c -> "Top-up Loan".equalsIgnoreCase(c.getProductType()))
                .collect(Collectors.toList());

        List<CustomerProfile> otherLoans = incomingCustomers.stream()
                .filter(c -> !"Top-up Loan".equalsIgnoreCase(c.getProductType()))
                .collect(Collectors.toList());

        // Perform internal deduplication for Top-up loans (only among themselves)
        List<CustomerProfile> uniqueTopUpLoans = deduplicateInternal(topUpLoans);

        // Perform internal deduplication for other loans
        List<CustomerProfile> uniqueOtherLoans = deduplicateInternal(otherLoans);

        // Combine the internally unique lists
        List<CustomerProfile> combinedInternallyUnique = new java.util.ArrayList<>();
        combinedInternallyUnique.addAll(uniqueTopUpLoans);
        combinedInternallyUnique.addAll(uniqueOtherLoans);

        List<CustomerProfile> finalUniqueCustomers = new java.util.ArrayList<>();

        // Deduplicate against the 'live book' (Customer 360)
        for (CustomerProfile incoming : combinedInternallyUnique) {
            // Check if a customer with the same PAN or Mobile exists in the live book
            // Note: In a real scenario, this might involve more complex matching rules
            // and handling of nulls for PAN/Mobile.
            Optional<CustomerProfile> existingMatch = customerRepository.findByPanOrMobile(incoming.getPan(), incoming.getMobileNumber());

            if (existingMatch.isEmpty()) {
                // If no match found in the live book, this incoming customer is considered unique
                finalUniqueCustomers.add(incoming);
            }
            // If a match exists, the incoming customer is considered a duplicate of an existing one
            // and is not added to the final list. In a real system, this might trigger an update
            // to the existing profile or a logging event.
        }

        return finalUniqueCustomers;
    }

    /**
     * Performs internal deduplication within a given list of customer profiles.
     * This method identifies and removes duplicates based on PAN or Mobile Number.
     * It prioritizes the first encountered customer for a given PAN/Mobile.
     *
     * @param customers The list of customer profiles to deduplicate internally.
     * @return A list containing only unique customer profiles from the input list.
     */
    private List<CustomerProfile> deduplicateInternal(List<CustomerProfile> customers) {
        List<CustomerProfile> uniqueCustomers = new java.util.ArrayList<>();
        Set<String> seenPans = new HashSet<>();
        Set<String> seenMobiles = new HashSet<>();

        for (CustomerProfile customer : customers) {
            boolean isDuplicate = false;

            // Check for PAN duplication
            if (customer.getPan() != null) {
                if (seenPans.contains(customer.getPan())) {
                    isDuplicate = true;
                } else {
                    seenPans.add(customer.getPan());
                }
            }

            // Check for Mobile duplication
            if (customer.getMobileNumber() != null) {
                if (seenMobiles.contains(customer.getMobileNumber())) {
                    isDuplicate = true;
                } else {
                    seenMobiles.add(customer.getMobileNumber());
                }
            }

            // If not a duplicate by either PAN or Mobile, add to unique list
            if (!isDuplicate) {
                uniqueCustomers.add(customer);
            }
        }
        return uniqueCustomers;
    }
}

/**
 * Dummy CustomerRepository interface for testing purposes.
 * In a real project, this would be a Spring Data JPA repository interface
 * extending `JpaRepository` and would be located in
 * `src/main/java/com/ltfs/cdp/customer/repository/CustomerRepository.java`.
 * It's included here to make the test file self-contained and directly runnable.
 */
interface CustomerRepository {
    /**
     * Simulates finding an existing customer profile by PAN or Mobile Number.
     * In a real implementation, this would query the database.
     *
     * @param pan The PAN number to search for. Can be null.
     * @param mobile The mobile number to search for. Can be null.
     * @return An Optional containing the found CustomerProfile if a match exists, otherwise empty.
     */
    Optional<CustomerProfile> findByPanOrMobile(String pan, String mobile);
    // Other repository methods like save, findAll, etc., would be defined here.
}
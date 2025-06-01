package com.ltfs.cdp.customer.dedupe;

import com.ltfs.cdp.customer.model.Customer;
import com.ltfs.cdp.customer.repository.CustomerRepository;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

import java.time.LocalDate;
import java.util.Arrays;
import java.util.Collections;
import java.util.List;
import java.util.Optional;
import java.util.Set;
import java.util.stream.Collectors;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.lenient;
import static org.mockito.Mockito.when;

/**
 * Test class for {@link DeduplicationEngine}.
 * This class focuses on verifying the core deduplication logic and rules,
 * including matching criteria (PAN, Mobile+DOB, Email+DOB, Name+DOB+City),
 * handling of top-up loan specific rules, and integration with the 'live book' (Customer 360).
 */
@ExtendWith(MockitoExtension.class)
class DeduplicationEngineTest {

    @Mock
    private CustomerRepository customerRepository; // Mock for interacting with the 'live book'

    @InjectMocks
    private DeduplicationEngine deduplicationEngine; // The system under test

    // Sample Customer objects for various test scenarios
    private Customer customer1;
    private Customer customer2;
    private Customer customer3;
    private Customer customer4;
    private Customer customer5_liveBook; // Represents a customer already existing in the 'live book'

    /**
     * Sets up common test data and mock behaviors before each test method.
     */
    @BeforeEach
    void setUp() {
        // Initialize common test customers with distinct and overlapping data
        customer1 = new Customer(
                "CUST001", "John", "Doe", LocalDate.of(1990, 1, 15),
                "9876543210", "john.doe@example.com", "ABCDE1234F", "CONSUMER_LOAN",
                "123 Main St", "Mumbai", "Maharashtra", "400001"
        );

        customer2 = new Customer(
                "CUST002", "Jonathan", "Dough", LocalDate.of(1990, 1, 15),
                "9876543210", "jonathan.dough@example.com", "ABCDE5678G", "CONSUMER_LOAN", // Same Mobile+DOB as C1
                "456 Park Ave", "Mumbai", "Maharashtra", "400001"
        );

        customer3 = new Customer(
                "CUST003", "Jane", "Smith", LocalDate.of(1985, 5, 20),
                "9988776655", "jane.smith@example.com", "FGHIJ9876K", "CONSUMER_LOAN",
                "789 Oak Ln", "Delhi", "Delhi", "110001"
        );

        customer4 = new Customer(
                "CUST004", "John", "Doe", LocalDate.of(1990, 1, 15),
                "9999999999", "john.doe.new@example.com", "ABCDE1234F", "CONSUMER_LOAN", // Same PAN as C1
                "123 Main St", "Mumbai", "Maharashtra", "400001"
        );

        customer5_liveBook = new Customer(
                "CUST_LIVE_005", "Existing", "Customer", LocalDate.of(1980, 10, 10),
                "9123456789", "existing.customer@example.com", "LIVEB1234L", "CONSUMER_LOAN",
                "100 Live St", "Bangalore", "Karnataka", "560001"
        );

        // Configure lenient mocking for repository calls. This ensures that if a specific
        // `when` clause isn't hit in a test, Mockito doesn't throw an `UnnecessaryStubbingException`.
        // Specific `when` calls in individual tests will override these lenient stubs.
        lenient().when(customerRepository.findByPan(any(String.class))).thenReturn(Optional.empty());
        lenient().when(customerRepository.findByMobileNumberAndDob(any(String.class), any(LocalDate.class))).thenReturn(Optional.empty());
        lenient().when(customerRepository.findByEmailAndDob(any(String.class), any(LocalDate.class))).thenReturn(Optional.empty());
    }

    /**
     * Helper method to check if a list of {@link DeduplicationGroup} contains a specific group of customers.
     * The order of customers within a group or the order of groups in the list does not matter.
     *
     * @param groups The list of deduplication groups returned by the engine.
     * @param expectedCustomers The customers expected to be in one of the groups.
     * @return true if a group matching the expected customers (by content, not order) is found, false otherwise.
     */
    private boolean containsGroup(List<DeduplicationGroup> groups, Customer... expectedCustomers) {
        Set<Customer> expectedSet = Arrays.stream(expectedCustomers).collect(Collectors.toSet());
        for (DeduplicationGroup group : groups) {
            if (group.size() == expectedSet.size() && group.getCustomersInGroup().equals(expectedSet)) {
                return true;
            }
        }
        return false;
    }

    /**
     * Helper method to count the number of deduplication groups of a specific size.
     *
     * @param groups The list of deduplication groups.
     * @param size The expected size of the group.
     * @return The count of groups that have the specified size.
     */
    private long countGroupsOfSize(List<DeduplicationGroup> groups, int size) {
        return groups.stream().filter(g -> g.size() == size).count();
    }

    @Test
    @DisplayName("Should return empty list when no customers are provided for deduplication")
    void shouldReturnEmptyList_whenNoCustomersProvided() {
        List<DeduplicationGroup> result = deduplicationEngine.deduplicate(Collections.emptyList());
        assertTrue(result.isEmpty(), "Result should be empty for an empty input list.");

        result = deduplicationEngine.deduplicate(null);
        assertTrue(result.isEmpty(), "Result should be empty for a null input list.");
    }

    @Test
    @DisplayName("Should identify an exact match based on PAN (Permanent Account Number)")
    void shouldIdentifyExactMatchByPan() {
        // customer1 and customer4 share the same PAN
        List<Customer> incomingCustomers = Arrays.asList(customer1, customer4, customer3);

        List<DeduplicationGroup> result = deduplicationEngine.deduplicate(incomingCustomers);

        // Expect two groups: one containing (customer1, customer4) and another containing (customer3)
        assertEquals(2, result.size(), "Expected two deduplication groups.");
        assertTrue(containsGroup(result, customer1, customer4), "Group for PAN match (customer1, customer4) not found.");
        assertTrue(containsGroup(result, customer3), "Group for unique customer3 not found.");
        assertEquals(1, countGroupsOfSize(result, 2), "Expected one group of size 2.");
        assertEquals(1, countGroupsOfSize(result, 1), "Expected one group of size 1.");
    }

    @Test
    @DisplayName("Should identify a match based on Mobile Number and Date of Birth")
    void shouldIdentifyMatchByMobileAndDob() {
        // customer1 and customer2 share the same mobile number and DOB
        List<Customer> incomingCustomers = Arrays.asList(customer1, customer2, customer3);

        List<DeduplicationGroup> result = deduplicationEngine.deduplicate(incomingCustomers);

        // Expect two groups: one containing (customer1, customer2) and another containing (customer3)
        assertEquals(2, result.size(), "Expected two deduplication groups.");
        assertTrue(containsGroup(result, customer1, customer2), "Group for Mobile+DOB match (customer1, customer2) not found.");
        assertTrue(containsGroup(result, customer3), "Group for unique customer3 not found.");
        assertEquals(1, countGroupsOfSize(result, 2), "Expected one group of size 2.");
        assertEquals(1, countGroupsOfSize(result, 1), "Expected one group of size 1.");
    }

    @Test
    @DisplayName("Should identify a match based on Email and Date of Birth")
    void shouldIdentifyMatchByEmailAndDob() {
        Customer c1_emailMatch = new Customer(
                "CUST001A", "John", "Doe", LocalDate.of(1990, 1, 15),
                "9876543210", "common.email@example.com", "ABCDE1234F", "CONSUMER_LOAN",
                "123 Main St", "Mumbai", "Maharashtra", "400001"
        );
        Customer c2_emailMatch = new Customer(
                "CUST002A", "Jane", "Doe", LocalDate.of(1990, 1, 15),
                "1111111111", "common.email@example.com", "ABCDE5678G", "CONSUMER_LOAN", // Same Email+DOB as C1_emailMatch
                "456 Park Ave", "Mumbai", "Maharashtra", "400001"
        );

        List<Customer> incomingCustomers = Arrays.asList(c1_emailMatch, c2_emailMatch, customer3);

        List<DeduplicationGroup> result = deduplicationEngine.deduplicate(incomingCustomers);

        // Expect two groups: one containing (c1_emailMatch, c2_emailMatch) and another containing (customer3)
        assertEquals(2, result.size(), "Expected two deduplication groups.");
        assertTrue(containsGroup(result, c1_emailMatch, c2_emailMatch), "Group for Email+DOB match not found.");
        assertTrue(containsGroup(result, customer3), "Group for unique customer3 not found.");
        assertEquals(1, countGroupsOfSize(result, 2), "Expected one group of size 2.");
        assertEquals(1, countGroupsOfSize(result, 1), "Expected one group of size 1.");
    }

    @Test
    @DisplayName("Should identify a match based on Name, DOB, and City (assuming exact match for test purposes)")
    void shouldIdentifyMatchByNameDobCity() {
        Customer c1_nameDobCityMatch = new Customer(
                "CUST001B", "Alice", "Wonder", LocalDate.of(1995, 3, 10),
                "1234567890", "alice@example.com", "PAN1234A", "CONSUMER_LOAN",
                "101 Elm St", "Chennai", "Tamil Nadu", "600001"
        );
        Customer c2_nameDobCityMatch = new Customer(
                "CUST002B", "Alice", "Wonder", LocalDate.of(1995, 3, 10),
                "0987654321", "alice.w@example.com", "PAN5678B", "CONSUMER_LOAN", // Same Name+DOB+City as C1_nameDobCityMatch
                "102 Elm St", "Chennai", "Tamil Nadu", "600001"
        );

        List<Customer> incomingCustomers = Arrays.asList(c1_nameDobCityMatch, c2_nameDobCityMatch, customer3);

        List<DeduplicationGroup> result = deduplicationEngine.deduplicate(incomingCustomers);

        // Expect two groups: one containing (c1_nameDobCityMatch, c2_nameDobCityMatch) and another containing (customer3)
        assertEquals(2, result.size(), "Expected two deduplication groups.");
        assertTrue(containsGroup(result, c1_nameDobCityMatch, c2_nameDobCityMatch), "Group for Name+DOB+City match not found.");
        assertTrue(containsGroup(result, customer3), "Group for unique customer3 not found.");
        assertEquals(1, countGroupsOfSize(result, 2), "Expected one group of size 2.");
        assertEquals(1, countGroupsOfSize(result, 1), "Expected one group of size 1.");
    }

    @Test
    @DisplayName("Should not identify a match when no deduplication criteria are met")
    void shouldNotIdentifyMatch_whenNoCriteriaMet() {
        List<Customer> incomingCustomers = Arrays.asList(customer1, customer3); // No common criteria between C1 and C3

        List<DeduplicationGroup> result = deduplicationEngine.deduplicate(incomingCustomers);

        // Expect two separate groups, each with one customer, as no match criteria are met
        assertEquals(2, result.size(), "Expected two separate deduplication groups.");
        assertTrue(containsGroup(result, customer1), "Group for customer1 not found.");
        assertTrue(containsGroup(result, customer3), "Group for customer3 not found.");
        assertEquals(2, countGroupsOfSize(result, 1), "Expected two groups of size 1.");
    }

    @Test
    @DisplayName("Should handle null or empty fields gracefully and apply rules only when data is present")
    void shouldHandleNullOrEmptyFieldsGracefully() {
        Customer c_nullPan = new Customer(
                "CUST_NULL_PAN", "Test", "User", LocalDate.of(1990, 1, 1),
                "1111111111", "test@example.com", null, "CONSUMER_LOAN", // PAN is null
                "Addr", "City", "State", "Pin"
        );
        Customer c_emptyMobile = new Customer(
                "CUST_EMPTY_MOBILE", "Test", "User", LocalDate.of(1990, 1, 1),
                "", "test2@example.com", "PAN1234X", "CONSUMER_LOAN", // Mobile is empty
                "Addr", "City", "State", "Pin"
        );
        Customer c_matchingWithNulls = new Customer( // Matches c_nullPan by Mobile+DOB
                "CUST_MATCH_NULLS", "Test", "User", LocalDate.of(1990, 1, 1),
                "1111111111", "test@example.com", null, "CONSUMER_LOAN", // PAN is null, Mobile+DOB matches c_nullPan
                "Addr", "City", "State", "Pin"
        );

        List<Customer> incomingCustomers = Arrays.asList(c_nullPan, c_emptyMobile, c_matchingWithNulls);

        List<DeduplicationGroup> result = deduplicationEngine.deduplicate(incomingCustomers);

        // c_nullPan and c_matchingWithNulls should match by Mobile+DOB.
        // c_emptyMobile should not match anything by mobile, but could match by other criteria if present.
        // In this case, c_emptyMobile is unique.
        assertEquals(2, result.size(), "Expected two deduplication groups.");
        assertTrue(containsGroup(result, c_nullPan, c_matchingWithNulls), "Group for Mobile+DOB match with null PAN not found.");
        assertTrue(containsGroup(result, c_emptyMobile), "Group for unique customer with empty mobile not found.");
        assertEquals(1, countGroupsOfSize(result, 2), "Expected one group of size 2.");
        assertEquals(1, countGroupsOfSize(result, 1), "Expected one group of size 1.");
    }

    @Test
    @DisplayName("Should dedupe Top-up loan offers only within other Top-up offers, not with consumer loans")
    void shouldDedupeTopUpOffersSeparately() {
        Customer topUp1 = new Customer(
                "TOPUP001", "Topup", "User1", LocalDate.of(1990, 1, 1),
                "1234567890", "topup1@example.com", "TOPUP1PAN", "TOP_UP_LOAN",
                "Addr", "City", "State", "Pin"
        );
        Customer topUp2 = new Customer( // Matches topUp1 by mobile+dob
                "TOPUP002", "Topup", "User2", LocalDate.of(1990, 1, 1),
                "1234567890", "topup2@example.com", "TOPUP2PAN", "TOP_UP_LOAN",
                "Addr", "City", "State", "Pin"
        );
        Customer consumerLoanMatchingTopUp = new Customer( // Would match topUp1 by mobile+dob if not for loanType rule
                "CL001", "Topup", "User1", LocalDate.of(1990, 1, 1),
                "1234567890", "consumer@example.com", "CL1PAN", "CONSUMER_LOAN",
                "Addr", "City", "State", "Pin"
        );

        List<Customer> incomingCustomers = Arrays.asList(topUp1, topUp2, consumerLoanMatchingTopUp);

        List<DeduplicationGroup> result = deduplicationEngine.deduplicate(incomingCustomers);

        // Expect topUp1 and topUp2 to form a group (as they are both TOP_UP_LOAN and match),
        // and consumerLoanMatchingTopUp to be in a separate group (due to loan type mismatch).
        assertEquals(2, result.size(), "Expected two deduplication groups.");
        assertTrue(containsGroup(result, topUp1, topUp2), "Top-up loan group not found.");
        assertTrue(containsGroup(result, consumerLoanMatchingTopUp), "Consumer loan group not found.");
        assertEquals(1, countGroupsOfSize(result, 2), "Expected one group of size 2.");
        assertEquals(1, countGroupsOfSize(result, 1), "Expected one group of size 1.");
    }

    @Test
    @DisplayName("Should deduplicate an incoming customer against an existing customer in the 'live book' (Customer 360)")
    void shouldDeduplicateAgainstLiveBook() {
        Customer incomingCustomer = new Customer(
                "NEWCUST001", "New", "Arrival", LocalDate.of(1980, 10, 10),
                "9123456789", "new.arrival@example.com", "LIVEB1234L", "CONSUMER_LOAN", // Same PAN as customer5_liveBook
                "200 New St", "Bangalore", "Karnataka", "560001"
        );

        // Mock the repository to return the live book customer when queried by PAN
        when(customerRepository.findByPan(incomingCustomer.getPan())).thenReturn(Optional.of(customer5_liveBook));

        List<Customer> incomingCustomers = Collections.singletonList(incomingCustomer);
        List<DeduplicationGroup> result = deduplicationEngine.deduplicate(incomingCustomers);

        // Expect one group containing both the incoming customer and the live book customer
        assertEquals(1, result.size(), "Expected one deduplication group.");
        assertTrue(containsGroup(result, incomingCustomer, customer5_liveBook), "Group containing incoming and live book customer not found.");
        assertEquals(1, countGroupsOfSize(result, 2), "Expected one group of size 2.");
    }

    @Test
    @DisplayName("Should handle multiple incoming customers and their matches with each other and the live book")
    void shouldHandleMultipleIncomingAndLiveBookMatches() {
        Customer incoming1 = new Customer(
                "INC001", "Alice", "Smith", LocalDate.of(1992, 2, 20),
                "1112223333", "alice.s@example.com", "PANINC001", "CONSUMER_LOAN",
                "Addr1", "City1", "State1", "Pin1"
        );
        Customer incoming2 = new Customer( // Matches incoming1 by Mobile+DOB
                "INC002", "Alicia", "Smyth", LocalDate.of(1992, 2, 20),
                "1112223333", "alicia.s@example.com", "PANINC002", "CONSUMER_LOAN",
                "Addr2", "City1", "State1", "Pin1"
        );
        Customer incoming3 = new Customer( // Matches liveBookCustomer1 by PAN
                "INC003", "Bob", "Brown", LocalDate.of(1988, 8, 8),
                "4445556666", "bob.b@example.com", "PANLIVE001", "CONSUMER_LOAN",
                "Addr3", "City2", "State2", "Pin2"
        );
        Customer liveBookCustomer1 = new Customer(
                "LIVE001", "Robert", "Browne", LocalDate.of(1988, 8, 8),
                "7778889999", "robert.b@example.com", "PANLIVE001", "CONSUMER_LOAN",
                "LiveAddr1", "LiveCity1", "LiveState1", "LivePin1"
        );

        // Mock repository calls for live book matches
        when(customerRepository.findByPan(incoming3.getPan())).thenReturn(Optional.of(liveBookCustomer1));
        // Ensure other queries return empty to isolate the specific match scenarios
        when(customerRepository.findByPan(incoming1.getPan())).thenReturn(Optional.empty());
        when(customerRepository.findByPan(incoming2.getPan())).thenReturn(Optional.empty());
        when(customerRepository.findByMobileNumberAndDob(any(String.class), any(LocalDate.class)))
                .thenAnswer(invocation -> {
                    String mobile = invocation.getArgument(0);
                    LocalDate dob = invocation.getArgument(1);
                    // Only return liveBookCustomer1 if it matches the query criteria, otherwise empty
                    if (liveBookCustomer1.getMobileNumber().equals(mobile) && liveBookCustomer1.getDob().equals(dob)) {
                        return Optional.of(liveBookCustomer1);
                    }
                    return Optional.empty();
                });
        when(customerRepository.findByEmailAndDob(any(String.class), any(LocalDate.class))).thenReturn(Optional.empty());


        List<Customer> incomingCustomers = Arrays.asList(incoming1, incoming2, incoming3);
        List<DeduplicationGroup> result = deduplicationEngine.deduplicate(incomingCustomers);

        // Expected:
        // Group 1: incoming1, incoming2 (matched by Mobile+DOB among incoming customers)
        // Group 2: incoming3, liveBookCustomer1 (matched by PAN, incoming vs live book)
        assertEquals(2, result.size(), "Expected two deduplication groups.");
        assertTrue(containsGroup(result, incoming1, incoming2), "Group for incoming1 and incoming2 not found.");
        assertTrue(containsGroup(result, incoming3, liveBookCustomer1), "Group for incoming3 and liveBookCustomer1 not found.");
        assertEquals(2, countGroupsOfSize(result, 2), "Expected two groups of size 2.");
    }

    @Test
    @DisplayName("Should correctly group three customers that are transitively duplicates of each other")
    void shouldGroupThreeCustomersTransitively() {
        Customer c_master = new Customer(
                "CUST_M", "Master", "Customer", LocalDate.of(1980, 1, 1),
                "1112223333", "master@example.com", "PANMASTER", "CONSUMER_LOAN",
                "Addr", "City", "State", "Pin"
        );
        Customer c_dup1 = new Customer( // Matches master by mobile+dob
                "CUST_D1", "Duplicate", "One", LocalDate.of(1980, 1, 1),
                "1112223333", "dup1@example.com", "PANDUP1", "CONSUMER_LOAN",
                "Addr", "City", "State", "Pin"
        );
        Customer c_dup2 = new Customer( // Matches master by PAN
                "CUST_D2", "Duplicate", "Two", LocalDate.of(1990, 2, 2), // Different DOB
                "4445556666", "dup2@example.com", "PANMASTER", "CONSUMER_LOAN",
                "Addr", "City", "State", "Pin"
        );

        List<Customer> incomingCustomers = Arrays.asList(c_master, c_dup1, c_dup2);
        List<DeduplicationGroup> result = deduplicationEngine.deduplicate(incomingCustomers);

        // All three should be in one group because c_master links to c_dup1 (via mobile+dob)
        // and c_master links to c_dup2 (via PAN), effectively connecting all three into a single group.
        assertEquals(1, result.size(), "Expected one single deduplication group.");
        assertTrue(containsGroup(result, c_master, c_dup1, c_dup2), "All three customers should be in one group.");
        assertEquals(1, countGroupsOfSize(result, 3), "Expected one group of size 3.");
    }
}
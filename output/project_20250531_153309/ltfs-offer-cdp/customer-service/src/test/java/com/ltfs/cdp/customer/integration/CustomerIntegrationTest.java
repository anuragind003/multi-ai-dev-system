package com.ltfs.cdp.customer.integration;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.ltfs.cdp.customer.dto.CustomerEvent;
import com.ltfs.cdp.customer.model.Customer;
import com.ltfs.cdp.customer.repository.CustomerRepository;
import org.awaitility.Awaitility;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.kafka.core.KafkaTemplate;
import org.springframework.kafka.test.context.EmbeddedKafka;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.test.context.DynamicPropertyRegistry;
import org.springframework.test.context.DynamicPropertySource;
import org.springframework.test.web.servlet.MockMvc;
import org.testcontainers.containers.PostgreSQLContainer;
import org.testcontainers.junit.jupiter.Container;
import org.testcontainers.junit.jupiter.Testcontainers;

import java.time.LocalDate;
import java.util.List;
import java.util.concurrent.TimeUnit;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * End-to-end integration tests for customer data flow.
 * This class tests the entire pipeline from Kafka ingestion to database persistence,
 * including scenarios for new customer creation, updates, and basic deduplication.
 * It uses Testcontainers for a real PostgreSQL database and EmbeddedKafka for Kafka interactions,
 * ensuring a robust and isolated testing environment.
 */
@SpringBootTest(webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT)
@AutoConfigureMockMvc
@ActiveProfiles("test") // Ensures test-specific configurations are loaded
@Testcontainers // Enables Testcontainers for managing external services
@EmbeddedKafka(
        partitions = 1,
        brokerProperties = {
                "listeners=PLAINTEXT://localhost:9092",
                "port=9092"
        },
        topics = {"customer-events-topic"} // Define the Kafka topic used for customer events
)
@DisplayName("Customer Integration Tests")
class CustomerIntegrationTest {

    // Define the Kafka topic name as a constant
    private static final String CUSTOMER_EVENTS_TOPIC = "customer-events-topic";

    // Testcontainers for PostgreSQL database
    @Container
    public static PostgreSQLContainer<?> postgreSQLContainer = new PostgreSQLContainer<>("postgres:13.3")
            .withDatabaseName("cdp_customer_db")
            .withUsername("testuser")
            .withPassword("testpass");

    /**
     * Dynamically sets Spring properties to connect to the Testcontainers PostgreSQL instance.
     * This ensures the application context uses the ephemeral database for tests.
     * @param registry The dynamic property registry
     */
    @DynamicPropertySource
    static void setProperties(DynamicPropertyRegistry registry) {
        registry.add("spring.datasource.url", postgreSQLContainer::getJdbcUrl);
        registry.add("spring.datasource.username", postgreSQLContainer::getUsername);
        registry.add("spring.datasource.password", postgreSQLContainer::getPassword);
        registry.add("spring.kafka.bootstrap-servers", () -> "localhost:9092"); // Point to embedded Kafka
    }

    @Autowired
    private MockMvc mockMvc; // For potential REST endpoint testing, though Kafka is primary here

    @Autowired
    private KafkaTemplate<String, Object> kafkaTemplate; // To send messages to Kafka

    @Autowired
    private CustomerRepository customerRepository; // To interact with the database

    @Autowired
    private ObjectMapper objectMapper; // For JSON serialization/deserialization

    /**
     * Cleans up the database before each test to ensure test isolation.
     * This is crucial for integration tests to prevent data leakage between tests.
     */
    @BeforeEach
    void setUp() {
        customerRepository.deleteAll(); // Clear all customer data
    }

    /**
     * Test case: Verify successful ingestion of a new customer record via Kafka.
     * Steps:
     * 1. Create a new CustomerEvent DTO.
     * 2. Publish the event to the Kafka topic.
     * 3. Await for the message to be processed and persisted in the database.
     * 4. Verify that the customer exists in the database with the correct details.
     */
    @Test
    @DisplayName("Should ingest a new customer record from Kafka and persist to DB")
    void shouldIngestNewCustomerFromKafkaAndPersistToDb() throws Exception {
        // 1. Create a new CustomerEvent DTO with unique identifiers
        CustomerEvent newCustomerEvent = createCustomerEvent(
                "9876543210", "ABCDE1234F", "John", "Doe", LocalDate.of(1990, 1, 1), "john.doe@example.com"
        );

        // 2. Publish the event to the Kafka topic
        kafkaTemplate.send(CUSTOMER_EVENTS_TOPIC, newCustomerEvent);

        // 3. Await for the message to be processed and persisted in the database
        // Use Awaitility to wait for the asynchronous Kafka processing and DB write
        Awaitility.await()
                .atMost(10, TimeUnit.SECONDS) // Max wait time for processing
                .pollInterval(100, TimeUnit.MILLISECONDS) // Check every 100ms
                .until(() -> customerRepository.findByMobileNumber(newCustomerEvent.getMobileNumber()).isPresent());

        // 4. Verify that the customer exists in the database with the correct details
        Customer persistedCustomer = customerRepository.findByMobileNumber(newCustomerEvent.getMobileNumber()).orElseThrow(
                () -> new AssertionError("Customer not found in database after ingestion.")
        );

        assertThat(persistedCustomer).isNotNull();
        assertThat(persistedCustomer.getMobileNumber()).isEqualTo(newCustomerEvent.getMobileNumber());
        assertThat(persistedCustomer.getPan()).isEqualTo(newCustomerEvent.getPan());
        assertThat(persistedCustomer.getFirstName()).isEqualTo(newCustomerEvent.getFirstName());
        assertThat(persistedCustomer.getLastName()).isEqualTo(newCustomerEvent.getLastName());
        assertThat(persistedCustomer.getEmail()).isEqualTo(newCustomerEvent.getEmail());
        assertThat(persistedCustomer.getDateOfBirth()).isEqualTo(newCustomerEvent.getDateOfBirth());
        assertThat(persistedCustomer.getCreatedAt()).isNotNull();
        assertThat(persistedCustomer.getUpdatedAt()).isNotNull();
        // For a newly created record, created and updated timestamps should be very close or identical initially
        assertThat(persistedCustomer.getCreatedAt()).isEqualTo(persistedCustomer.getUpdatedAt());
    }

    /**
     * Test case: Verify successful update of an existing customer record via Kafka.
     * Steps:
     * 1. Ingest an initial customer record.
     * 2. Create an updated CustomerEvent DTO for the same customer identifier (e.g., mobile number).
     * 3. Publish the updated event to the Kafka topic.
     * 4. Await for the message to be processed and the database record to be updated.
     * 5. Verify that the customer record in the database reflects the updated details.
     */
    @Test
    @DisplayName("Should update an existing customer record from Kafka")
    void shouldUpdateExistingCustomerFromKafka() throws Exception {
        // 1. Ingest an initial customer record
        CustomerEvent initialCustomerEvent = createCustomerEvent(
                "1122334455", "PQRST6789J", "Jane", "Doe", LocalDate.of(1985, 5, 10), "jane.doe@example.com"
        );
        kafkaTemplate.send(CUSTOMER_EVENTS_TOPIC, initialCustomerEvent);

        // Wait for initial ingestion to complete
        Awaitility.await()
                .atMost(10, TimeUnit.SECONDS)
                .pollInterval(100, TimeUnit.MILLISECONDS)
                .until(() -> customerRepository.findByMobileNumber(initialCustomerEvent.getMobileNumber()).isPresent());

        Customer initialCustomer = customerRepository.findByMobileNumber(initialCustomerEvent.getMobileNumber()).orElseThrow();
        assertThat(initialCustomer.getFirstName()).isEqualTo("Jane");
        assertThat(initialCustomer.getCreatedAt()).isEqualTo(initialCustomer.getUpdatedAt()); // Should be same initially

        // 2. Create an updated CustomerEvent DTO for the same customer identifier
        CustomerEvent updatedCustomerEvent = createCustomerEvent(
                "1122334455", "PQRST6789J", "Janet", "Smith", LocalDate.of(1985, 5, 10), "janet.smith@example.com"
        );
        updatedCustomerEvent.setAddress("123 Main St, Apt 4B"); // Add a new field or update an existing one

        // 3. Publish the updated event to the Kafka topic
        kafkaTemplate.send(CUSTOMER_EVENTS_TOPIC, updatedCustomerEvent);

        // 4. Await for the message to be processed and the database record to be updated
        Awaitility.await()
                .atMost(10, TimeUnit.SECONDS)
                .pollInterval(100, TimeUnit.MILLISECONDS)
                .until(() -> {
                    Customer currentCustomer = customerRepository.findByMobileNumber(updatedCustomerEvent.getMobileNumber()).orElse(null);
                    // Check if the customer exists and the specific updated fields are reflected
                    return currentCustomer != null &&
                           "Janet".equals(currentCustomer.getFirstName()) &&
                           "123 Main St, Apt 4B".equals(currentCustomer.getAddress());
                });

        // 5. Verify that the customer record in the database reflects the updated details
        Customer updatedCustomer = customerRepository.findByMobileNumber(updatedCustomerEvent.getMobileNumber()).orElseThrow(
                () -> new AssertionError("Customer not found after update.")
        );
        assertThat(updatedCustomer.getFirstName()).isEqualTo("Janet");
        assertThat(updatedCustomer.getLastName()).isEqualTo("Smith");
        assertThat(updatedCustomer.getEmail()).isEqualTo("janet.smith@example.com");
        assertThat(updatedCustomer.getAddress()).isEqualTo("123 Main St, Apt 4B");
        // For an updated record, updated timestamp should be after created timestamp
        assertThat(updatedCustomer.getCreatedAt()).isBefore(updatedCustomer.getUpdatedAt());
    }

    /**
     * Test case: Verify deduplication logic for customer records based on a key identifier (e.g., mobile number).
     * This test assumes that the deduplication logic prioritizes the latest received data or merges intelligently.
     * Steps:
     * 1. Publish two CustomerEvent DTOs that are expected to deduplicate (same mobile number, different names).
     * 2. Await for processing.
     * 3. Verify that only one customer record exists in the database for that mobile number.
     * 4. Verify that the persisted record contains the data from the *latest* event (or the one prioritized by dedupe logic).
     */
    @Test
    @DisplayName("Should deduplicate customer records based on mobile number")
    void shouldDeduplicateCustomerRecords() throws Exception {
        // 1. Publish two CustomerEvent DTOs that are expected to deduplicate
        String commonMobileNumber = "5551234567";
        String commonPan = "DEDUP1234K";

        CustomerEvent firstEvent = createCustomerEvent(
                commonMobileNumber, commonPan, "Alice", "Smith", LocalDate.of(1992, 3, 15), "alice.s@example.com"
        );
        firstEvent.setAddress("101 Old St");

        CustomerEvent secondEvent = createCustomerEvent(
                commonMobileNumber, commonPan, "Alicia", "Jones", LocalDate.of(1992, 3, 15), "alicia.j@example.com"
        );
        secondEvent.setAddress("456 New Ave"); // Add a unique field to the second event

        kafkaTemplate.send(CUSTOMER_EVENTS_TOPIC, firstEvent);
        // Introduce a small delay to ensure the first message is processed or at least ordered before the second
        // In a real Kafka setup, ordering is guaranteed per partition, but processing time varies.
        // Awaitility below will handle the eventual consistency.
        Thread.sleep(500); // Simulate distinct events arriving sequentially
        kafkaTemplate.send(CUSTOMER_EVENTS_TOPIC, secondEvent);

        // 2. Await for processing and verify that only one customer record exists for the common mobile number
        Awaitility.await()
                .atMost(15, TimeUnit.SECONDS) // Give more time for two messages and dedupe logic
                .pollInterval(200, TimeUnit.MILLISECONDS)
                .until(() -> {
                    List<Customer> customers = customerRepository.findByMobileNumber(commonMobileNumber);
                    // Ensure exactly one record exists for this mobile number and it's present
                    return customers.size() == 1 && customers.get(0) != null;
                });

        // 3. Verify that the persisted record contains the data from the *latest* event (or the one prioritized)
        // Assuming the deduplication logic prioritizes the latest received data or merges intelligently.
        // For this test, we'll assume the latest (secondEvent) wins for conflicting fields.
        Customer dedupedCustomer = customerRepository.findByMobileNumber(commonMobileNumber).get(0); // Get the single record

        assertThat(dedupedCustomer).isNotNull();
        assertThat(dedupedCustomer.getMobileNumber()).isEqualTo(commonMobileNumber);
        assertThat(dedupedCustomer.getPan()).isEqualTo(commonPan);
        // Assuming the second event's data overwrites the first's for conflicting fields
        assertThat(dedupedCustomer.getFirstName()).isEqualTo(secondEvent.getFirstName()); // Alicia
        assertThat(dedupedCustomer.getLastName()).isEqualTo(secondEvent.getLastName());   // Jones
        assertThat(dedupedCustomer.getEmail()).isEqualTo(secondEvent.getEmail());         // alicia.j@example.com
        assertThat(dedupedCustomer.getAddress()).isEqualTo(secondEvent.getAddress());     // 456 New Ave
        assertThat(dedupedCustomer.getCreatedAt()).isBefore(dedupedCustomer.getUpdatedAt()); // Should be updated
    }

    /**
     * Test case: Verify that invalid customer data is not persisted.
     * This test assumes that the service layer performs validation and
     * either rejects invalid messages or logs them without persisting.
     * Steps:
     * 1. Create a CustomerEvent DTO with invalid data (e.g., missing required fields like mobile number).
     * 2. Publish the event to the Kafka topic.
     * 3. Await for a short period (to allow processing attempts).
     * 4. Verify that no customer record with the invalid data's identifier exists in the database.
     */
    @Test
    @DisplayName("Should not persist invalid customer data from Kafka")
    void shouldNotPersistInvalidCustomerData() throws Exception {
        // 1. Create a CustomerEvent DTO with invalid data (e.g., missing mobile number, which is a key identifier)
        CustomerEvent invalidCustomerEvent = new CustomerEvent();
        invalidCustomerEvent.setPan("INVALID1234X"); // A unique PAN for this invalid record
        invalidCustomerEvent.setFirstName("Invalid");
        invalidCustomerEvent.setLastName("Customer");
        invalidCustomerEvent.setEmail("invalid@example.com");
        // Mobile number is intentionally left null/empty, which should trigger validation failure in the service

        // 2. Publish the event to the Kafka topic
        kafkaTemplate.send(CUSTOMER_EVENTS_TOPIC, invalidCustomerEvent);

        // 3. Await for a short period to allow processing attempts.
        // We don't expect it to be found, so we wait to ensure it *doesn't* appear.
        Awaitility.await()
                .atMost(5, TimeUnit.SECONDS) // Wait for a reasonable time for processing to fail
                .pollInterval(100, TimeUnit.MILLISECONDS)
                .untilAsserted(() -> {
                    // 4. Verify that no customer record with the invalid data's identifier exists in the database.
                    // Since mobileNumber is null, we can't query by it. We'll check if any customer with the PAN exists.
                    // Assuming PAN is also a unique identifier or part of the validation.
                    List<Customer> customers = customerRepository.findByPan(invalidCustomerEvent.getPan());
                    assertThat(customers).isEmpty(); // Should not find a customer with this PAN
                });
    }

    /**
     * Helper method to create a CustomerEvent DTO for testing.
     * @param mobileNumber The mobile number of the customer.
     * @param pan The PAN of the customer.
     * @param firstName The first name of the customer.
     * @param lastName The last name of the customer.
     * @param dateOfBirth The date of birth of the customer.
     * @param email The email of the customer.
     * @return A new CustomerEvent instance.
     */
    private CustomerEvent createCustomerEvent(String mobileNumber, String pan, String firstName, String lastName,
                                              LocalDate dateOfBirth, String email) {
        CustomerEvent event = new CustomerEvent();
        event.setMobileNumber(mobileNumber);
        event.setPan(pan);
        event.setFirstName(firstName);
        event.setLastName(lastName);
        event.setDateOfBirth(dateOfBirth);
        event.setEmail(email);
        event.setAddress("Some Test Address"); // Default address for completeness
        event.setCity("Test City");
        event.setState("Test State");
        event.setPincode("123456");
        event.setGender("M");
        event.setOccupation("Software Engineer");
        return event;
    }
}
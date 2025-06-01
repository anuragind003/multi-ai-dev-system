package com.ltfs.cdp.customer.repository;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.jdbc.AutoConfigureTestDatabase;
import org.springframework.boot.test.autoconfigure.orm.jpa.DataJpaTest;
import org.springframework.dao.DataIntegrityViolationException;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;
import java.util.Optional;

import static org.assertj.core.api.Assertions.assertThat;
import static org.junit.jupiter.api.Assertions.assertThrows;

/**
 * Integration tests for {@link CustomerRepository}.
 * This class uses an in-memory H2 database to test the repository layer
 * in isolation from the rest of the application context.
 *
 * {@code @DataJpaTest} provides a convenient way to test JPA applications.
 * By default, it configures an in-memory database (H2 if available on classpath)
 * and scans for {@code @Entity} classes and Spring Data JPA repositories.
 * It also configures an in-memory database by default, replacing any
 * configured production database.
 *
 * {@code @AutoConfigureTestDatabase(replace = AutoConfigureTestDatabase.Replace.ANY)}
 * explicitly ensures that the default in-memory database is used, replacing any
 * configured production database. If Testcontainers were used, this would be set to NONE.
 */
@DataJpaTest
@AutoConfigureTestDatabase(replace = AutoConfigureTestDatabase.Replace.ANY)
class CustomerRepositoryTest {

    @Autowired
    private CustomerRepository customerRepository;

    private Customer customer1;
    private Customer customer2;

    /**
     * Set up test data before each test method.
     * This ensures a clean state for every test by clearing the repository
     * and initializing new customer entities.
     */
    @BeforeEach
    void setUp() {
        // Clear the repository before each test to ensure isolation
        customerRepository.deleteAll();

        // Initialize customer entities for testing
        customer1 = new Customer();
        customer1.setPanNumber("ABCDE1234F");
        customer1.setMobileNumber("9876543210");
        customer1.setFirstName("John");
        customer1.setLastName("Doe");
        customer1.setDeduplicationStatus("PENDING");

        customer2 = new Customer();
        customer2.setPanNumber("FGHIJ5678K");
        customer2.setMobileNumber("1234567890");
        customer2.setFirstName("Jane");
        customer2.setLastName("Smith");
        customer2.setDeduplicationStatus("DEDUPED");
    }

    /**
     * Test case for saving a new customer.
     * Verifies that a customer can be successfully persisted to the database
     * and its ID is generated.
     */
    @Test
    @DisplayName("Should save a new customer successfully")
    void saveCustomer_success() {
        Customer savedCustomer = customerRepository.save(customer1);

        // Assertions to verify the saved customer
        assertThat(savedCustomer).isNotNull();
        assertThat(savedCustomer.getId()).isNotNull(); // ID should be generated
        assertThat(savedCustomer.getPanNumber()).isEqualTo("ABCDE1234F");
        assertThat(savedCustomer.getMobileNumber()).isEqualTo("9876543210");
    }

    /**
     * Test case for finding a customer by its ID.
     * Verifies that an existing customer can be retrieved by its primary key.
     */
    @Test
    @DisplayName("Should find customer by ID when it exists")
    void findById_success() {
        Customer savedCustomer = customerRepository.save(customer1);

        Optional<Customer> foundCustomer = customerRepository.findById(savedCustomer.getId());

        // Assertions to verify the found customer
        assertThat(foundCustomer).isPresent();
        assertThat(foundCustomer.get().getPanNumber()).isEqualTo(customer1.getPanNumber());
        assertThat(foundCustomer.get().getFirstName()).isEqualTo(customer1.getFirstName());
    }

    /**
     * Test case for finding a customer by a non-existent ID.
     * Verifies that an empty Optional is returned when the ID does not exist.
     */
    @Test
    @DisplayName("Should return empty when finding customer by non-existent ID")
    void findById_notFound() {
        Optional<Customer> foundCustomer = customerRepository.findById(999L); // Use a non-existent ID

        // Assertions to verify that no customer is found
        assertThat(foundCustomer).isEmpty();
    }

    /**
     * Test case for retrieving all customers.
     * Verifies that all saved customers can be retrieved from the database.
     */
    @Test
    @DisplayName("Should retrieve all customers")
    void findAllCustomers_success() {
        customerRepository.save(customer1);
        customerRepository.save(customer2);

        List<Customer> customers = customerRepository.findAll();

        // Assertions to verify all customers are retrieved
        assertThat(customers).isNotNull();
        assertThat(customers).hasSize(2);
        assertThat(customers).extracting(Customer::getPanNumber)
                .containsExactlyInAnyOrder(customer1.getPanNumber(), customer2.getPanNumber());
    }

    /**
     * Test case for updating an existing customer.
     * Verifies that changes to a customer's attributes are persisted.
     */
    @Test
    @DisplayName("Should update an existing customer")
    void updateCustomer_success() {
        Customer savedCustomer = customerRepository.save(customer1);

        // Modify attributes of the retrieved customer
        savedCustomer.setFirstName("Johnny");
        savedCustomer.setDeduplicationStatus("DEDUPED");
        Customer updatedCustomer = customerRepository.save(savedCustomer); // Save the updated entity

        // Assertions to verify the update
        assertThat(updatedCustomer.getFirstName()).isEqualTo("Johnny");
        assertThat(updatedCustomer.getDeduplicationStatus()).isEqualTo("DEDUPED");
        assertThat(updatedCustomer.getId()).isEqualTo(savedCustomer.getId()); // ID should remain the same
    }

    /**
     * Test case for deleting a customer by its ID.
     * Verifies that a customer can be successfully removed from the database.
     */
    @Test
    @DisplayName("Should delete a customer by ID")
    void deleteCustomer_success() {
        Customer savedCustomer = customerRepository.save(customer1);

        customerRepository.deleteById(savedCustomer.getId());

        // Verify that the customer is no longer found
        Optional<Customer> foundCustomer = customerRepository.findById(savedCustomer.getId());
        assertThat(foundCustomer).isEmpty();
    }

    /**
     * Test case for finding a customer by PAN number.
     * Assumes a custom method `findByPanNumber` exists in `CustomerRepository`.
     */
    @Test
    @DisplayName("Should find customer by PAN number when it exists")
    void findByPanNumber_success() {
        customerRepository.save(customer1);

        Optional<Customer> foundCustomer = customerRepository.findByPanNumber(customer1.getPanNumber());

        // Assertions to verify the customer found by PAN
        assertThat(foundCustomer).isPresent();
        assertThat(foundCustomer.get().getFirstName()).isEqualTo(customer1.getFirstName());
        assertThat(foundCustomer.get().getMobileNumber()).isEqualTo(customer1.getMobileNumber());
    }

    /**
     * Test case for finding a customer by a non-existent PAN number.
     * Assumes a custom method `findByPanNumber` exists in `CustomerRepository`.
     */
    @Test
    @DisplayName("Should return empty when finding customer by non-existent PAN number")
    void findByPanNumber_notFound() {
        Optional<Customer> foundCustomer = customerRepository.findByPanNumber("NONEXISTENT");

        // Assertions to verify that no customer is found
        assertThat(foundCustomer).isEmpty();
    }

    /**
     * Test case for finding a customer by mobile number.
     * Assumes a custom method `findByMobileNumber` exists in `CustomerRepository`.
     */
    @Test
    @DisplayName("Should find customer by mobile number when it exists")
    void findByMobileNumber_success() {
        customerRepository.save(customer1);

        Optional<Customer> foundCustomer = customerRepository.findByMobileNumber(customer1.getMobileNumber());

        // Assertions to verify the customer found by mobile number
        assertThat(foundCustomer).isPresent();
        assertThat(foundCustomer.get().getPanNumber()).isEqualTo(customer1.getPanNumber());
        assertThat(foundCustomer.get().getFirstName()).isEqualTo(customer1.getFirstName());
    }

    /**
     * Test case for finding a customer by a non-existent mobile number.
     * Assumes a custom method `findByMobileNumber` exists in `CustomerRepository`.
     */
    @Test
    @DisplayName("Should return empty when finding customer by non-existent mobile number")
    void findByMobileNumber_notFound() {
        Optional<Customer> foundCustomer = customerRepository.findByMobileNumber("0000000000");

        // Assertions to verify that no customer is found
        assertThat(foundCustomer).isEmpty();
    }

    /**
     * Test case for ensuring PAN number uniqueness.
     * Verifies that saving two customers with the same PAN number throws a
     * {@link DataIntegrityViolationException}.
     * This assumes the PAN number column has a unique constraint in the Customer entity.
     */
    @Test
    @DisplayName("Should throw DataIntegrityViolationException when saving customer with duplicate PAN number")
    void saveCustomer_duplicatePanNumber_throwsException() {
        customerRepository.save(customer1); // Save the first customer successfully

        // Create a new customer with the same PAN number as customer1
        Customer duplicatePanCustomer = new Customer();
        duplicatePanCustomer.setPanNumber(customer1.getPanNumber()); // Duplicate PAN
        duplicatePanCustomer.setMobileNumber("9999999999"); // Different mobile
        duplicatePanCustomer.setFirstName("Duplicate");
        duplicatePanCustomer.setLastName("User");
        duplicatePanCustomer.setDeduplicationStatus("PENDING");

        // Expect DataIntegrityViolationException when trying to save with a duplicate unique key
        assertThrows(DataIntegrityViolationException.class, () -> {
            // Use saveAndFlush to force immediate database synchronization and trigger the exception
            customerRepository.saveAndFlush(duplicatePanCustomer);
        });
    }
}

// --- Mock Customer Entity and Repository for compilation purposes ---
// In a real project, these classes would reside in their respective source folders
// (e.g., com.ltfs.cdp.customer.model.Customer and com.ltfs.cdp.customer.repository.CustomerRepository).
// They are included here as minimal definitions to make this test file directly runnable
// without requiring external project structure setup for compilation.

/**
 * Mock Customer Entity for testing purposes.
 * This simplified version includes basic JPA annotations required for {@code @DataJpaTest} to function.
 * In a real project, this class would typically be in `src/main/java/com/ltfs/cdp/customer/model/Customer.java`
 * and might use Lombok annotations like {@code @Data}, {@code @NoArgsConstructor}, {@code @AllArgsConstructor}.
 */
@Entity
@Table(name = "customers") // Explicitly name the table for clarity
class Customer {
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY) // Auto-incrementing ID strategy
    private Long id;

    @Column(name = "pan_number", unique = true, nullable = false) // PAN should be unique and not null
    private String panNumber;

    @Column(name = "mobile_number", nullable = false) // Mobile number should not be null
    private String mobileNumber;

    @Column(name = "first_name")
    private String firstName;

    @Column(name = "last_name")
    private String lastName;

    @Column(name = "deduplication_status")
    private String deduplicationStatus; // e.g., PENDING, DEDUPED, REJECTED

    // Default constructor required by JPA
    public Customer() {}

    // All-args constructor (useful for testing, though not strictly required by JPA)
    public Customer(Long id, String panNumber, String mobileNumber, String firstName, String lastName, String deduplicationStatus) {
        this.id = id;
        this.panNumber = panNumber;
        this.mobileNumber = mobileNumber;
        this.firstName = firstName;
        this.lastName = lastName;
        this.deduplicationStatus = deduplicationStatus;
    }

    // Getters and Setters for all fields
    public Long getId() { return id; }
    public void setId(Long id) { this.id = id; }
    public String getPanNumber() { return panNumber; }
    public void setPanNumber(String panNumber) { this.panNumber = panNumber; }
    public String getMobileNumber() { return mobileNumber; }
    public void setMobileNumber(String mobileNumber) { this.mobileNumber = mobileNumber; }
    public String getFirstName() { return firstName; }
    public void setFirstName(String firstName) { this.firstName = firstName; }
    public String getLastName() { return lastName; }
    public void setLastName(String lastName) { this.lastName = lastName; }
    public String getDeduplicationStatus() { return deduplicationStatus; }
    public void setDeduplicationStatus(String deduplicationStatus) { this.deduplicationStatus = deduplicationStatus; }
}

/**
 * Mock Customer Repository interface for testing purposes.
 * This interface extends Spring Data JPA's {@link JpaRepository} and defines
 * custom query methods relevant to customer data (e.g., finding by PAN or mobile number).
 * In a real project, this interface would typically be in `src/main/java/com/ltfs/cdp/customer/repository/CustomerRepository.java`.
 */
interface CustomerRepository extends JpaRepository<Customer, Long> {
    /**
     * Finds a customer by their PAN number.
     * This method is crucial for deduplication logic.
     *
     * @param panNumber The PAN number to search for.
     * @return An {@link Optional} containing the customer if found, or empty otherwise.
     */
    Optional<Customer> findByPanNumber(String panNumber);

    /**
     * Finds a customer by their mobile number.
     * This method can also be used for customer identification or deduplication.
     *
     * @param mobileNumber The mobile number to search for.
     * @return An {@link Optional} containing the customer if found, or empty otherwise.
     */
    Optional<Customer> findByMobileNumber(String mobileNumber);
}
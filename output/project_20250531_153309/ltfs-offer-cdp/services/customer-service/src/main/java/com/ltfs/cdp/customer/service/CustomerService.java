package com.ltfs.cdp.customer.service;

import com.ltfs.cdp.customer.dto.CustomerDTO;
import com.ltfs.cdp.customer.entity.Customer;
import com.ltfs.cdp.customer.exception.CustomerNotFoundException;
import com.ltfs.cdp.customer.repository.CustomerRepository;
import com.ltfs.cdp.customer.service.dedupe.DeduplicationService;
import com.ltfs.cdp.customer.service.validation.ValidationService;
import lombok.extern.slf44j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;
import java.util.Optional;
import java.util.stream.Collectors;

/**
 * Service class orchestrating customer data operations.
 * This class handles business logic, interacts with the repository,
 * and integrates with deduplication and validation services.
 * It aims to provide a single profile view of the customer by managing
 * deduplication across various consumer loan products.
 */
@Service
@Slf4j
public class CustomerService {

    private final CustomerRepository customerRepository;
    private final DeduplicationService deduplicationService;
    private final ValidationService validationService;

    /**
     * Constructs a CustomerService with necessary dependencies.
     *
     * @param customerRepository The repository for customer data persistence.
     * @param deduplicationService The service responsible for applying deduplication logic.
     * @param validationService The service responsible for column-level data validation.
     */
    public CustomerService(CustomerRepository customerRepository,
                           DeduplicationService deduplicationService,
                           ValidationService validationService) {
        this.customerRepository = customerRepository;
        this.deduplicationService = deduplicationService;
        this.validationService = validationService;
    }

    /**
     * Creates a new customer profile in the system or links it to an existing master profile
     * if a duplicate is found.
     * This method performs basic column-level validation on the incoming data.
     * It then applies deduplication logic:
     * - If a matching master customer is found (based on dedupe rules like PAN + Mobile),
     *   the incoming customer is marked as a duplicate and its 'masterCustomerId' is set
     *   to the ID of the existing master. The DTO of the master customer is returned,
     *   providing a "single profile view".
     * - If no duplicate is found, the incoming customer becomes a new master profile,
     *   and its own DTO is returned.
     *
     * @param customerDTO The Customer Data Transfer Object containing new customer details.
     * @return The CustomerDTO representing the master profile (either newly created or existing).
     * @throws com.ltfs.cdp.customer.exception.ValidationException if input data fails validation.
     */
    @Transactional
    public CustomerDTO createCustomer(CustomerDTO customerDTO) {
        log.info("Attempting to create or deduplicate customer with external ID: {}", customerDTO.getCustomerId());

        // 1. Perform basic column-level validation on the incoming DTO
        validationService.validateCustomerDTO(customerDTO);

        // Convert DTO to Entity for internal processing and persistence
        Customer newCustomer = toEntity(customerDTO);

        // 2. Apply deduplication logic to find if an existing master customer matches
        Optional<Customer> masterCustomerOptional = deduplicationService.findMasterCustomer(newCustomer);

        if (masterCustomerOptional.isPresent()) {
            // A master customer (single profile view) already exists for this incoming data
            Customer masterCustomer = masterCustomerOptional.get();
            log.info("Duplicate customer found. Linking new customer (External ID: {}) to master customer (ID: {})",
                    newCustomer.getCustomerId(), masterCustomer.getId());

            // Mark the incoming customer as a duplicate and link it to the identified master
            newCustomer.setDeduplicated(true);
            newCustomer.setMasterCustomerId(masterCustomer.getId());
            customerRepository.save(newCustomer); // Persist the duplicate entry

            // Return the master customer's details as the single profile view
            return toDTO(masterCustomer);
        } else {
            // No duplicate found, this customer becomes a new master profile
            log.info("No duplicate found. Creating new master customer profile for external ID: {}", customerDTO.getCustomerId());
            newCustomer.setDeduplicated(false);
            newCustomer.setMasterCustomerId(null); // A master customer does not have a master
            Customer savedCustomer = customerRepository.save(newCustomer); // Persist the new master
            return toDTO(savedCustomer);
        }
    }

    /**
     * Retrieves a customer profile by its internal system ID.
     * To ensure a "single profile view", if the retrieved customer record is a duplicate
     * (i.e., it has a 'masterCustomerId' set), this method will fetch and return the
     * associated master customer's profile instead.
     *
     * @param id The internal ID of the customer to retrieve.
     * @return The CustomerDTO representing the master profile associated with the given ID.
     * @throws CustomerNotFoundException if no customer with the given ID is found.
     */
    @Transactional(readOnly = true)
    public CustomerDTO getCustomerById(String id) {
        log.debug("Fetching customer by ID: {}", id);
        Customer customer = customerRepository.findById(id)
                .orElseThrow(() -> {
                    log.warn("Customer not found with ID: {}", id);
                    return new CustomerNotFoundException("Customer not found with ID: " + id);
                });

        // If the found customer is a duplicate, return its master's profile to ensure single profile view
        if (customer.isDeduplicated() && customer.getMasterCustomerId() != null) {
            log.debug("Customer {} is a duplicate, fetching master customer with ID: {}", id, customer.getMasterCustomerId());
            return customerRepository.findById(customer.getMasterCustomerId())
                    .map(this::toDTO)
                    .orElseGet(() -> {
                        // Fallback: If master customer is somehow missing, return the duplicate's own profile
                        log.warn("Master customer (ID: {}) not found for duplicate ID: {}. Returning duplicate's own profile.",
                                customer.getMasterCustomerId(), id);
                        return toDTO(customer);
                    });
        }
        // If it's a master or not deduped, return its own profile
        return toDTO(customer);
    }

    /**
     * Updates an existing customer profile identified by its internal system ID.
     * This method performs column-level validation on the incoming DTO.
     * Note: This operation updates the specific customer record. Re-deduplication
     * is not automatically triggered upon update in this implementation to avoid
     * complex scenarios (e.g., a master becoming a duplicate of another master).
     *
     * @param id The internal ID of the customer to update.
     * @param customerDTO The Customer Data Transfer Object with updated details.
     * @return The updated CustomerDTO.
     * @throws CustomerNotFoundException if the customer to update is not found.
     * @throws com.ltfs.cdp.customer.exception.ValidationException if input data fails validation.
     */
    @Transactional
    public CustomerDTO updateCustomer(String id, CustomerDTO customerDTO) {
        log.info("Attempting to update customer with ID: {}", id);

        // 1. Perform basic column-level validation
        validationService.validateCustomerDTO(customerDTO);

        Customer existingCustomer = customerRepository.findById(id)
                .orElseThrow(() -> {
                    log.warn("Customer not found for update with ID: {}", id);
                    return new CustomerNotFoundException("Customer not found with ID: " + id);
                });

        // Update fields from DTO to the existing entity
        updateEntityFromDTO(existingCustomer, customerDTO);

        Customer updatedCustomer = customerRepository.save(existingCustomer);
        log.info("Customer with ID {} updated successfully.", id);
        return toDTO(updatedCustomer);
    }

    /**
     * Deletes a customer profile by its internal system ID.
     * Important Note: This operation deletes the specific customer record.
     * If the deleted customer was a master profile, any other customer records
     * that were marked as duplicates and linked to this master will become
     * "orphaned" (their 'masterCustomerId' will point to a non-existent ID).
     * A more robust production system might require additional logic here,
     * such as re-assigning a new master for linked duplicates or preventing
     * deletion of master profiles that still have active linked duplicates.
     *
     * @param id The internal ID of the customer to delete.
     * @throws CustomerNotFoundException if the customer to delete is not found.
     */
    @Transactional
    public void deleteCustomer(String id) {
        log.info("Attempting to delete customer with ID: {}", id);
        if (!customerRepository.existsById(id)) {
            log.warn("Customer not found for deletion with ID: {}", id);
            throw new CustomerNotFoundException("Customer not found with ID: " + id);
        }
        customerRepository.deleteById(id);
        log.info("Customer with ID {} deleted successfully.", id);
    }

    /**
     * Retrieves a list of all customer profiles stored in the system.
     * This method returns all records, including both master profiles and duplicate entries.
     * For a view that only shows master profiles (the single profile view),
     * a separate method or filtering logic would be required.
     *
     * @return A list of all CustomerDTOs representing all customer records.
     */
    @Transactional(readOnly = true)
    public List<CustomerDTO> getAllCustomers() {
        log.debug("Fetching all customers.");
        return customerRepository.findAll().stream()
                .map(this::toDTO)
                .collect(Collectors.toList());
    }

    /**
     * Converts a {@link CustomerDTO} object to a {@link Customer} entity.
     * This is a manual mapping function. For larger projects, a mapping library
     * like MapStruct or Orika could be used for cleaner and more efficient conversions.
     *
     * @param dto The CustomerDTO to convert.
     * @return The corresponding Customer entity.
     */
    private Customer toEntity(CustomerDTO dto) {
        Customer entity = new Customer();
        // ID is typically generated by the database for new entities.
        // If the DTO has an ID, it implies an update operation, so we set it.
        if (dto.getId() != null && !dto.getId().isEmpty()) {
            entity.setId(dto.getId());
        }
        entity.setCustomerId(dto.getCustomerId());
        entity.setFirstName(dto.getFirstName());
        entity.setLastName(dto.getLastName());
        entity.setPan(dto.getPan());
        entity.setMobileNumber(dto.getMobileNumber());
        entity.setEmail(dto.getEmail());
        entity.setAddress(dto.getAddress());
        entity.setProductType(dto.getProductType());
        entity.setSourceSystem(dto.getSourceSystem());
        // Deduplication status and masterCustomerId are managed by the service logic,
        // not directly mapped from the incoming DTO.
        return entity;
    }

    /**
     * Converts a {@link Customer} entity to a {@link CustomerDTO} object.
     * This is a manual mapping function.
     *
     * @param entity The Customer entity to convert.
     * @return The corresponding CustomerDTO.
     */
    private CustomerDTO toDTO(Customer entity) {
        CustomerDTO dto = new CustomerDTO();
        dto.setId(entity.getId());
        dto.setCustomerId(entity.getCustomerId());
        dto.setFirstName(entity.getFirstName());
        dto.setLastName(entity.getLastName());
        dto.setPan(entity.getPan());
        dto.setMobileNumber(entity.getMobileNumber());
        dto.setEmail(entity.getEmail());
        dto.setAddress(entity.getAddress());
        dto.setProductType(entity.getProductType());
        dto.setSourceSystem(entity.getSourceSystem());
        return dto;
    }

    /**
     * Updates an existing {@link Customer} entity with data from a {@link CustomerDTO}.
     * This method is used during update operations to transfer mutable fields from the DTO
     * to the persistent entity.
     *
     * @param entity The existing Customer entity to update.
     * @param dto The CustomerDTO containing the new data.
     */
    private void updateEntityFromDTO(Customer entity, CustomerDTO dto) {
        // Update only the fields that are intended to be mutable via an update operation.
        // CustomerId is often immutable after creation, but depends on business rules.
        entity.setFirstName(dto.getFirstName());
        entity.setLastName(dto.getLastName());
        entity.setPan(dto.getPan());
        entity.setMobileNumber(dto.getMobileNumber());
        entity.setEmail(dto.getEmail());
        entity.setAddress(dto.getAddress());
        entity.setProductType(dto.getProductType());
        entity.setSourceSystem(dto.getSourceSystem());
        // Deduplication status and masterCustomerId are not updated via DTO.
    }
}
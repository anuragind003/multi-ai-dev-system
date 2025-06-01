package com.ltfs.cdp.customer.service;

import com.ltfs.cdp.customer.dto.CustomerDTO;
import com.ltfs.cdp.customer.exception.CustomerNotFoundException;
import com.ltfs.cdp.customer.exception.DuplicateCustomerException;
import com.ltfs.cdp.customer.mapper.CustomerMapper;
import com.ltfs.cdp.customer.model.Customer;
import com.ltfs.cdp.customer.repository.CustomerRepository;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

import java.time.LocalDateTime;
import java.util.Arrays;
import java.util.Collections;
import java.util.List;
import java.util.Optional;
import java.util.UUID;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.*;

@ExtendWith(MockitoExtension.class)
class CustomerServiceTest {

    @Mock
    private CustomerRepository customerRepository;

    @Mock
    private CustomerMapper customerMapper;

    @Mock
    private DeduplicationService deduplicationService;

    @InjectMocks
    private CustomerService customerService;

    private Customer customer;
    private CustomerDTO customerDTO;
    private UUID customerId;

    @BeforeEach
    void setUp() {
        customerId = UUID.randomUUID();
        customer = new Customer(customerId, "John", "Doe", "9876543210", "ABCDE1234F", "john.doe@example.com", LocalDateTime.now(), LocalDateTime.now(), false, null);
        customerDTO = new CustomerDTO(null, "John", "Doe", "9876543210", "ABCDE1234F", "john.doe@example.com");
    }

    @Test
    void createCustomer_Success() {
        // Arrange
        CustomerDTO inputDto = new CustomerDTO(null, "Jane", "Smith", "9988776655", "FGHIJ5678K", "jane.smith@example.com");
        Customer newCustomer = new Customer(UUID.randomUUID(), "Jane", "Smith", "9988776655", "FGHIJ5678K", "jane.smith@example.com", LocalDateTime.now(), LocalDateTime.now(), false, null);
        CustomerDTO expectedDto = new CustomerDTO(newCustomer.getId(), "Jane", "Smith", "9988776655", "FGHIJ5678K", "jane.smith@example.com");

        when(customerRepository.findByMobileNumber(inputDto.getMobileNumber())).thenReturn(Optional.empty());
        when(customerRepository.findByPanNumber(inputDto.getPanNumber())).thenReturn(Optional.empty());
        when(customerMapper.toEntity(inputDto)).thenReturn(newCustomer);
        when(customerRepository.save(any(Customer.class))).thenReturn(newCustomer);
        when(customerMapper.toDto(newCustomer)).thenReturn(expectedDto);

        // Act
        CustomerDTO result = customerService.createCustomer(inputDto);

        // Assert
        assertNotNull(result);
        assertNotNull(result.getId());
        assertEquals(expectedDto.getMobileNumber(), result.getMobileNumber());
        verify(customerRepository, times(1)).findByMobileNumber(inputDto.getMobileNumber());
        verify(customerRepository, times(1)).findByPanNumber(inputDto.getPanNumber());
        verify(customerRepository, times(1)).save(any(Customer.class));
    }

    @Test
    void createCustomer_DuplicateMobileNumber_ThrowsException() {
        // Arrange
        when(customerRepository.findByMobileNumber(customerDTO.getMobileNumber())).thenReturn(Optional.of(customer));

        // Act & Assert
        DuplicateCustomerException thrown = assertThrows(DuplicateCustomerException.class, () -> {
            customerService.createCustomer(customerDTO);
        });
        assertTrue(thrown.getMessage().contains("mobile number"));
        verify(customerRepository, never()).save(any(Customer.class));
    }

    @Test
    void createCustomer_DuplicatePanNumber_ThrowsException() {
        // Arrange
        when(customerRepository.findByMobileNumber(customerDTO.getMobileNumber())).thenReturn(Optional.empty());
        when(customerRepository.findByPanNumber(customerDTO.getPanNumber())).thenReturn(Optional.of(customer));

        // Act & Assert
        DuplicateCustomerException thrown = assertThrows(DuplicateCustomerException.class, () -> {
            customerService.createCustomer(customerDTO);
        });
        assertTrue(thrown.getMessage().contains("PAN number"));
        verify(customerRepository, never()).save(any(Customer.class));
    }

    @Test
    void createCustomer_InvalidInput_MissingMobileNumber_ThrowsException() {
        // Arrange
        customerDTO.setMobileNumber(null);

        // Act & Assert
        IllegalArgumentException thrown = assertThrows(IllegalArgumentException.class, () -> {
            customerService.createCustomer(customerDTO);
        });
        assertTrue(thrown.getMessage().contains("Mobile number is required."));
        verify(customerRepository, never()).save(any(Customer.class));
    }

    @Test
    void getCustomerById_Success() {
        // Arrange
        when(customerRepository.findById(customerId)).thenReturn(Optional.of(customer));
        when(customerMapper.toDto(customer)).thenReturn(customerDTO);

        // Act
        CustomerDTO result = customerService.getCustomerById(customerId);

        // Assert
        assertNotNull(result);
        assertEquals(customerDTO.getFirstName(), result.getFirstName());
        verify(customerRepository, times(1)).findById(customerId);
        verify(customerMapper, times(1)).toDto(customer);
    }

    @Test
    void getCustomerById_NotFound_ThrowsException() {
        // Arrange
        when(customerRepository.findById(customerId)).thenReturn(Optional.empty());

        // Act & Assert
        CustomerNotFoundException thrown = assertThrows(CustomerNotFoundException.class, () -> {
            customerService.getCustomerById(customerId);
        });
        assertTrue(thrown.getMessage().contains("Customer not found with ID: " + customerId));
        verify(customerRepository, times(1)).findById(customerId);
        verify(customerMapper, never()).toDto(any(Customer.class));
    }

    @Test
    void updateCustomer_Success() {
        // Arrange
        CustomerDTO updateDto = new CustomerDTO(customerId, "Johnny", "Doe", "9876543210", "ABCDE1234F", "johnny.doe@example.com");
        Customer updatedCustomer = new Customer(customerId, "Johnny", "Doe", "9876543210", "ABCDE1234F", "johnny.doe@example.com", customer.getCreatedAt(), LocalDateTime.now(), false, null);
        CustomerDTO expectedDto = new CustomerDTO(customerId, "Johnny", "Doe", "9876543210", "ABCDE1234F", "johnny.doe@example.com");

        when(customerRepository.findById(customerId)).thenReturn(Optional.of(customer));
        when(customerRepository.save(any(Customer.class))).thenReturn(updatedCustomer);
        when(customerMapper.toDto(updatedCustomer)).thenReturn(expectedDto);
        doNothing().when(customerMapper).updateCustomerFromDto(updateDto, customer);

        // Act
        CustomerDTO result = customerService.updateCustomer(customerId, updateDto);

        // Assert
        assertNotNull(result);
        assertEquals(expectedDto.getFirstName(), result.getFirstName());
        verify(customerRepository, times(1)).findById(customerId);
        verify(customerMapper, times(1)).updateCustomerFromDto(updateDto, customer);
        verify(customerRepository, times(1)).save(any(Customer.class));
        verify(customerMapper, times(1)).toDto(updatedCustomer);
    }

    @Test
    void updateCustomer_NotFound_ThrowsException() {
        // Arrange
        when(customerRepository.findById(customerId)).thenReturn(Optional.empty());

        // Act & Assert
        CustomerNotFoundException thrown = assertThrows(CustomerNotFoundException.class, () -> {
            customerService.updateCustomer(customerId, customerDTO);
        });
        assertTrue(thrown.getMessage().contains("Customer not found with ID: " + customerId));
        verify(customerRepository, times(1)).findById(customerId);
        verify(customerRepository, never()).save(any(Customer.class));
    }

    @Test
    void updateCustomer_DuplicateMobileNumberForAnotherCustomer_ThrowsException() {
        // Arrange
        CustomerDTO updateDto = new CustomerDTO(customerId, "John", "Doe", "1112223333", "ABCDE1234F", "john.doe@example.com");
        Customer existingCustomerWithSameMobile = new Customer(UUID.randomUUID(), "Another", "Customer", "1112223333", "XYZAB9876C", "another@example.com", LocalDateTime.now(), LocalDateTime.now(), false, null);

        when(customerRepository.findById(customerId)).thenReturn(Optional.of(customer));
        when(customerRepository.findByMobileNumber(updateDto.getMobileNumber())).thenReturn(Optional.of(existingCustomerWithSameMobile));

        // Act & Assert
        DuplicateCustomerException thrown = assertThrows(DuplicateCustomerException.class, () -> {
            customerService.updateCustomer(customerId, updateDto);
        });
        assertTrue(thrown.getMessage().contains("Another customer with mobile number " + updateDto.getMobileNumber() + " already exists."));
        verify(customerRepository, never()).save(any(Customer.class));
    }

    @Test
    void updateCustomer_DuplicatePanNumberForAnotherCustomer_ThrowsException() {
        // Arrange
        CustomerDTO updateDto = new CustomerDTO(customerId, "John", "Doe", "9876543210", "PQRST5432L", "john.doe@example.com");
        Customer existingCustomerWithSamePan = new Customer(UUID.randomUUID(), "Another", "Customer", "1112223333", "PQRST5432L", "another@example.com", LocalDateTime.now(), LocalDateTime.now(), false, null);

        when(customerRepository.findById(customerId)).thenReturn(Optional.of(customer));
        when(customerRepository.findByMobileNumber(updateDto.getMobileNumber())).thenReturn(Optional.empty()); // No mobile conflict
        when(customerRepository.findByPanNumber(updateDto.getPanNumber())).thenReturn(Optional.of(existingCustomerWithSamePan));

        // Act & Assert
        DuplicateCustomerException thrown = assertThrows(DuplicateCustomerException.class, () -> {
            customerService.updateCustomer(customerId, updateDto);
        });
        assertTrue(thrown.getMessage().contains("Another customer with PAN number " + updateDto.getPanNumber() + " already exists."));
        verify(customerRepository, never()).save(any(Customer.class));
    }

    @Test
    void deleteCustomer_Success() {
        // Arrange
        when(customerRepository.existsById(customerId)).thenReturn(true);
        doNothing().when(customerRepository).deleteById(customerId);

        // Act
        customerService.deleteCustomer(customerId);

        // Assert
        verify(customerRepository, times(1)).existsById(customerId);
        verify(customerRepository, times(1)).deleteById(customerId);
    }

    @Test
    void deleteCustomer_NotFound_ThrowsException() {
        // Arrange
        when(customerRepository.existsById(customerId)).thenReturn(false);

        // Act & Assert
        CustomerNotFoundException thrown = assertThrows(CustomerNotFoundException.class, () -> {
            customerService.deleteCustomer(customerId);
        });
        assertTrue(thrown.getMessage().contains("Customer not found with ID: " + customerId));
        verify(customerRepository, times(1)).existsById(customerId);
        verify(customerRepository, never()).deleteById(any(UUID.class));
    }

    @Test
    void triggerDeduplication_Success_CustomersExist() {
        // Arrange
        Customer customer1 = new Customer(UUID.randomUUID(), "John", "Doe", "9876543210", "ABCDE1234F", "john.doe@example.com", LocalDateTime.now(), LocalDateTime.now(), false, null);
        Customer customer2 = new Customer(UUID.randomUUID(), "Jon", "Doh", "9876543210", "ABCDE1234F", "jon.doh@example.com", LocalDateTime.now(), LocalDateTime.now(), false, null);
        List<Customer> customersToDedupe = Arrays.asList(customer1, customer2);

        // Simulate deduplication service setting masterCustomerId and isDeduplicated
        Customer masterCustomer = customer1;
        masterCustomer.setMasterCustomerId(masterCustomer.getId());
        masterCustomer.setDeduplicated(true);

        Customer duplicateCustomer = customer2;
        duplicateCustomer.setMasterCustomerId(masterCustomer.getId());
        duplicateCustomer.setDeduplicated(true);

        List<Customer> dedupedCustomers = Arrays.asList(masterCustomer, duplicateCustomer);

        when(customerRepository.findByIsDeduplicatedFalse()).thenReturn(customersToDedupe);
        when(deduplicationService.performDeduplication(customersToDedupe)).thenReturn(dedupedCustomers);
        when(customerRepository.saveAll(anyList())).thenReturn(dedupedCustomers);

        // Act
        customerService.triggerDeduplication();

        // Assert
        verify(customerRepository, times(1)).findByIsDeduplicatedFalse();
        verify(deduplicationService, times(1)).performDeduplication(customersToDedupe);
        verify(customerRepository, times(1)).saveAll(dedupedCustomers);

        // Verify that customers are marked as deduped
        assertTrue(masterCustomer.isDeduplicated());
        assertTrue(duplicateCustomer.isDeduplicated());
        assertNotNull(masterCustomer.getMasterCustomerId());
        assertNotNull(duplicateCustomer.getMasterCustomerId());
    }

    @Test
    void triggerDeduplication_NoCustomersToDeduplicate() {
        // Arrange
        when(customerRepository.findByIsDeduplicatedFalse()).thenReturn(Collections.emptyList());

        // Act
        customerService.triggerDeduplication();

        // Assert
        verify(customerRepository, times(1)).findByIsDeduplicatedFalse();
        verify(deduplicationService, never()).performDeduplication(anyList());
        verify(customerRepository, never()).saveAll(anyList());
    }

    @Test
    void validateCustomerData_ValidDTO_ReturnsTrue() {
        // Arrange
        CustomerDTO validDto = new CustomerDTO(null, "Test", "User", "1234567890", "ABCDE1234F", "test.user@example.com");

        // Act
        boolean isValid = customerService.validateCustomerData(validDto);

        // Assert
        assertTrue(isValid);
    }

    @Test
    void validateCustomerData_InvalidFirstName_ReturnsFalse() {
        // Arrange
        customerDTO.setFirstName(""); // Empty first name

        // Act
        boolean isValid = customerService.validateCustomerData(customerDTO);

        // Assert
        assertFalse(isValid);
    }

    @Test
    void validateCustomerData_InvalidMobileNumber_ReturnsFalse() {
        // Arrange
        customerDTO.setMobileNumber("123"); // Too short
        // Act
        boolean isValid = customerService.validateCustomerData(customerDTO);
        // Assert
        assertFalse(isValid);

        // Arrange
        customerDTO.setMobileNumber("abcde12345"); // Non-numeric
        // Act
        isValid = customerService.validateCustomerData(customerDTO);
        // Assert
        assertFalse(isValid);
    }

    @Test
    void validateCustomerData_InvalidPanNumber_ReturnsFalse() {
        // Arrange
        customerDTO.setPanNumber("12345"); // Invalid format
        // Act
        boolean isValid = customerService.validateCustomerData(customerDTO);
        // Assert
        assertFalse(isValid);

        // Arrange
        customerDTO.setPanNumber("ABCDE12345"); // Correct length, but last char is digit
        // Act
        isValid = customerService.validateCustomerData(customerDTO);
        // Assert
        assertFalse(isValid);
    }

    @Test
    void validateCustomerData_InvalidEmail_ReturnsFalse() {
        // Arrange
        customerDTO.setEmail("invalid-email"); // Missing @ and domain
        // Act
        boolean isValid = customerService.validateCustomerData(customerDTO);
        // Assert
        assertFalse(isValid);

        // Arrange
        customerDTO.setEmail("user@.com"); // Invalid domain
        // Act
        isValid = customerService.validateCustomerData(customerDTO);
        // Assert
        assertFalse(isValid);
    }
}
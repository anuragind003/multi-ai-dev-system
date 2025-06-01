package com.ltfs.cdp.customer.controller;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.ltfs.cdp.customer.dto.CustomerRequestDTO;
import com.ltfs.cdp.customer.dto.CustomerResponseDTO;
import com.ltfs.cdp.customer.exception.CustomerAlreadyExistsException;
import com.ltfs.cdp.customer.exception.CustomerNotFoundException;
import com.ltfs.cdp.customer.service.CustomerService;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.WebMvcTest;
import org.springframework.boot.test.mock.mockito.MockBean;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.MockMvc;

import java.time.LocalDate;
import java.util.UUID;

import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.*;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.*;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;

/**
 * Unit tests for {@link CustomerController} using MockMvc.
 * This class focuses on testing the web layer, ensuring that the controller
 * handles HTTP requests correctly, maps URLs, and interacts with the service layer as expected.
 * The service layer is mocked to isolate the controller's behavior.
 */
@WebMvcTest(CustomerController.class)
class CustomerControllerTest {

    @Autowired
    private MockMvc mockMvc; // Used to simulate HTTP requests

    @MockBean
    private CustomerService customerService; // Mocked service layer dependency

    @Autowired
    private ObjectMapper objectMapper; // Used for JSON serialization/deserialization

    private CustomerRequestDTO customerRequestDTO;
    private CustomerResponseDTO customerResponseDTO;
    private UUID customerId;

    /**
     * Set up common test data before each test method.
     */
    @BeforeEach
    void setUp() {
        customerId = UUID.randomUUID();
        customerRequestDTO = CustomerRequestDTO.builder()
                .firstName("John")
                .lastName("Doe")
                .email("john.doe@example.com")
                .mobileNumber("9876543210")
                .dateOfBirth(LocalDate.of(1990, 1, 1))
                .panNumber("ABCDE1234F")
                .aadhaarNumber("123456789012")
                .build();

        customerResponseDTO = CustomerResponseDTO.builder()
                .customerId(customerId)
                .firstName("John")
                .lastName("Doe")
                .email("john.doe@example.com")
                .mobileNumber("9876543210")
                .dateOfBirth(LocalDate.of(1990, 1, 1))
                .panNumber("ABCDE1234F")
                .aadhaarNumber("123456789012")
                .build();
    }

    /**
     * Test case for successfully retrieving a customer profile by ID.
     * Expects HTTP 200 OK and the correct customer data in the response.
     */
    @Test
    @DisplayName("Should return customer profile by ID successfully")
    void getCustomerProfileById_Success() throws Exception {
        // Mock the service call to return a customer response DTO
        when(customerService.getCustomerById(customerId)).thenReturn(customerResponseDTO);

        // Perform GET request and assert the response
        mockMvc.perform(get("/api/v1/customers/{id}", customerId))
                .andExpect(status().isOk()) // Expect HTTP 200 OK
                .andExpect(content().contentType(MediaType.APPLICATION_JSON)) // Expect JSON content type
                .andExpect(jsonPath("$.customerId").value(customerId.toString())) // Assert customer ID
                .andExpect(jsonPath("$.firstName").value("John")) // Assert first name
                .andExpect(jsonPath("$.email").value("john.doe@example.com")); // Assert email

        // Verify that the service method was called exactly once with the correct ID
        verify(customerService, times(1)).getCustomerById(customerId);
    }

    /**
     * Test case for retrieving a customer profile when the customer is not found.
     * Expects HTTP 404 Not Found.
     */
    @Test
    @DisplayName("Should return 404 if customer profile not found by ID")
    void getCustomerProfileById_NotFound() throws Exception {
        // Mock the service call to throw CustomerNotFoundException
        when(customerService.getCustomerById(customerId)).thenThrow(new CustomerNotFoundException("Customer not found with ID: " + customerId));

        // Perform GET request and assert the response
        mockMvc.perform(get("/api/v1/customers/{id}", customerId))
                .andExpect(status().isNotFound()) // Expect HTTP 404 Not Found
                .andExpect(jsonPath("$.message").value("Customer not found with ID: " + customerId)); // Assert error message

        // Verify that the service method was called
        verify(customerService, times(1)).getCustomerById(customerId);
    }

    /**
     * Test case for successfully creating a new customer profile.
     * Expects HTTP 201 Created and the created customer data in the response.
     */
    @Test
    @DisplayName("Should create customer profile successfully")
    void createCustomerProfile_Success() throws Exception {
        // Mock the service call to return the created customer response DTO
        when(customerService.createCustomer(any(CustomerRequestDTO.class))).thenReturn(customerResponseDTO);

        // Perform POST request with the customer request DTO as JSON body
        mockMvc.perform(post("/api/v1/customers")
                .contentType(MediaType.APPLICATION_JSON)
                .content(objectMapper.writeValueAsString(customerRequestDTO))) // Convert DTO to JSON string
                .andExpect(status().isCreated()) // Expect HTTP 201 Created
                .andExpect(content().contentType(MediaType.APPLICATION_JSON))
                .andExpect(jsonPath("$.customerId").value(customerId.toString()))
                .andExpect(jsonPath("$.firstName").value("John"));

        // Verify that the service method was called exactly once
        verify(customerService, times(1)).createCustomer(any(CustomerRequestDTO.class));
    }

    /**
     * Test case for creating a customer profile with invalid input (e.g., missing required fields).
     * Expects HTTP 400 Bad Request.
     */
    @Test
    @DisplayName("Should return 400 if customer profile creation fails due to invalid input")
    void createCustomerProfile_InvalidInput() throws Exception {
        // Create an invalid DTO (e.g., missing first name)
        CustomerRequestDTO invalidRequestDTO = CustomerRequestDTO.builder()
                .lastName("Doe")
                .email("john.doe@example.com")
                .mobileNumber("9876543210")
                .build();

        // Perform POST request with the invalid DTO
        mockMvc.perform(post("/api/v1/customers")
                .contentType(MediaType.APPLICATION_JSON)
                .content(objectMapper.writeValueAsString(invalidRequestDTO)))
                .andExpect(status().isBadRequest()) // Expect HTTP 400 Bad Request
                .andExpect(jsonPath("$.errors").exists()); // Expect validation errors in the response

        // Verify that the service method was never called as validation should fail at controller level
        verify(customerService, never()).createCustomer(any(CustomerRequestDTO.class));
    }

    /**
     * Test case for creating a customer profile when a customer with the same unique identifier already exists.
     * Expects HTTP 409 Conflict.
     */
    @Test
    @DisplayName("Should return 409 if customer profile already exists")
    void createCustomerProfile_AlreadyExists() throws Exception {
        // Mock the service call to throw CustomerAlreadyExistsException
        when(customerService.createCustomer(any(CustomerRequestDTO.class)))
                .thenThrow(new CustomerAlreadyExistsException("Customer with PAN ABCDE1234F already exists."));

        // Perform POST request
        mockMvc.perform(post("/api/v1/customers")
                .contentType(MediaType.APPLICATION_JSON)
                .content(objectMapper.writeValueAsString(customerRequestDTO)))
                .andExpect(status().isConflict()) // Expect HTTP 409 Conflict
                .andExpect(jsonPath("$.message").value("Customer with PAN ABCDE1234F already exists."));

        // Verify that the service method was called
        verify(customerService, times(1)).createCustomer(any(CustomerRequestDTO.class));
    }

    /**
     * Test case for successfully updating an existing customer profile.
     * Expects HTTP 200 OK and the updated customer data in the response.
     */
    @Test
    @DisplayName("Should update customer profile successfully")
    void updateCustomerProfile_Success() throws Exception {
        // Create an updated DTO
        CustomerRequestDTO updatedRequestDTO = CustomerRequestDTO.builder()
                .firstName("Jane")
                .lastName("Doe")
                .email("jane.doe@example.com")
                .mobileNumber("9876543210")
                .dateOfBirth(LocalDate.of(1990, 1, 1))
                .panNumber("ABCDE1234F")
                .aadhaarNumber("123456789012")
                .build();

        // Create an updated response DTO
        CustomerResponseDTO updatedResponseDTO = CustomerResponseDTO.builder()
                .customerId(customerId)
                .firstName("Jane")
                .lastName("Doe")
                .email("jane.doe@example.com")
                .mobileNumber("9876543210")
                .dateOfBirth(LocalDate.of(1990, 1, 1))
                .panNumber("ABCDE1234F")
                .aadhaarNumber("123456789012")
                .build();

        // Mock the service call to return the updated customer response DTO
        when(customerService.updateCustomer(eq(customerId), any(CustomerRequestDTO.class))).thenReturn(updatedResponseDTO);

        // Perform PUT request
        mockMvc.perform(put("/api/v1/customers/{id}", customerId)
                .contentType(MediaType.APPLICATION_JSON)
                .content(objectMapper.writeValueAsString(updatedRequestDTO)))
                .andExpect(status().isOk()) // Expect HTTP 200 OK
                .andExpect(content().contentType(MediaType.APPLICATION_JSON))
                .andExpect(jsonPath("$.customerId").value(customerId.toString()))
                .andExpect(jsonPath("$.firstName").value("Jane")) // Assert updated first name
                .andExpect(jsonPath("$.email").value("jane.doe@example.com")); // Assert updated email

        // Verify that the service method was called
        verify(customerService, times(1)).updateCustomer(eq(customerId), any(CustomerRequestDTO.class));
    }

    /**
     * Test case for updating a customer profile when the customer is not found.
     * Expects HTTP 404 Not Found.
     */
    @Test
    @DisplayName("Should return 404 if customer profile not found during update")
    void updateCustomerProfile_NotFound() throws Exception {
        // Mock the service call to throw CustomerNotFoundException
        when(customerService.updateCustomer(eq(customerId), any(CustomerRequestDTO.class)))
                .thenThrow(new CustomerNotFoundException("Customer not found with ID: " + customerId));

        // Perform PUT request
        mockMvc.perform(put("/api/v1/customers/{id}", customerId)
                .contentType(MediaType.APPLICATION_JSON)
                .content(objectMapper.writeValueAsString(customerRequestDTO)))
                .andExpect(status().isNotFound()) // Expect HTTP 404 Not Found
                .andExpect(jsonPath("$.message").value("Customer not found with ID: " + customerId));

        // Verify that the service method was called
        verify(customerService, times(1)).updateCustomer(eq(customerId), any(CustomerRequestDTO.class));
    }

    /**
     * Test case for updating a customer profile with invalid input.
     * Expects HTTP 400 Bad Request.
     */
    @Test
    @DisplayName("Should return 400 if customer profile update fails due to invalid input")
    void updateCustomerProfile_InvalidInput() throws Exception {
        // Create an invalid DTO (e.g., missing first name)
        CustomerRequestDTO invalidRequestDTO = CustomerRequestDTO.builder()
                .lastName("Doe")
                .email("john.doe@example.com")
                .mobileNumber("9876543210")
                .build();

        // Perform PUT request with the invalid DTO
        mockMvc.perform(put("/api/v1/customers/{id}", customerId)
                .contentType(MediaType.APPLICATION_JSON)
                .content(objectMapper.writeValueAsString(invalidRequestDTO)))
                .andExpect(status().isBadRequest()) // Expect HTTP 400 Bad Request
                .andExpect(jsonPath("$.errors").exists()); // Expect validation errors

        // Verify that the service method was never called
        verify(customerService, never()).updateCustomer(eq(customerId), any(CustomerRequestDTO.class));
    }

    /**
     * Test case for successfully deleting a customer profile.
     * Expects HTTP 204 No Content.
     */
    @Test
    @DisplayName("Should delete customer profile successfully")
    void deleteCustomerProfile_Success() throws Exception {
        // Mock the service call to do nothing (void method)
        doNothing().when(customerService).deleteCustomer(customerId);

        // Perform DELETE request
        mockMvc.perform(delete("/api/v1/customers/{id}", customerId))
                .andExpect(status().isNoContent()); // Expect HTTP 204 No Content

        // Verify that the service method was called
        verify(customerService, times(1)).deleteCustomer(customerId);
    }

    /**
     * Test case for deleting a customer profile when the customer is not found.
     * Expects HTTP 404 Not Found.
     */
    @Test
    @DisplayName("Should return 404 if customer profile not found during deletion")
    void deleteCustomerProfile_NotFound() throws Exception {
        // Mock the service call to throw CustomerNotFoundException
        doThrow(new CustomerNotFoundException("Customer not found with ID: " + customerId))
                .when(customerService).deleteCustomer(customerId);

        // Perform DELETE request
        mockMvc.perform(delete("/api/v1/customers/{id}", customerId))
                .andExpect(status().isNotFound()) // Expect HTTP 404 Not Found
                .andExpect(jsonPath("$.message").value("Customer not found with ID: " + customerId));

        // Verify that the service method was called
        verify(customerService, times(1)).deleteCustomer(customerId);
    }
}
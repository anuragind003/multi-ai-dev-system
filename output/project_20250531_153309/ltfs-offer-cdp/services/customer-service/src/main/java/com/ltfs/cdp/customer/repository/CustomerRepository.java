package com.ltfs.cdp.customer.repository;

import com.ltfs.cdp.customer.model.Customer;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.Optional;

/**
 * Spring Data JPA repository for the {@link Customer} entity.
 * This interface provides standard CRUD operations and custom query methods
 * for managing customer data within the LTFS Offer CDP system.
 *
 * Key responsibilities include:
 * - Retrieving customer profiles for a single view.
 * - Supporting deduplication logic by finding customers based on unique identifiers
 *   such as PAN, mobile number, email ID, and Aadhaar number.
 */
@Repository
public interface CustomerRepository extends JpaRepository<Customer, Long> {

    /**
     * Finds a customer by their Permanent Account Number (PAN).
     * PAN is a crucial identifier for unique customer identification and deduplication.
     *
     * @param pan The PAN of the customer.
     * @return An {@link Optional} containing the found Customer, or empty if no customer with the given PAN is found.
     */
    Optional<Customer> findByPan(String pan);

    /**
     * Finds a customer by their mobile number.
     * This is a common identifier used for customer lookup and deduplication.
     *
     * @param mobileNumber The mobile number of the customer.
     * @return An {@link Optional} containing the found Customer, or empty if no customer with the given mobile number is found.
     */
    Optional<Customer> findByMobileNumber(String mobileNumber);

    /**
     * Finds a customer by their email ID.
     * This can be used as an alternative identifier for customer lookup and deduplication.
     *
     * @param emailId The email ID of the customer.
     * @return An {@link Optional} containing the found Customer, or empty if no customer with the given email ID is found.
     */
    Optional<Customer> findByEmailId(String emailId);

    /**
     * Finds a customer by their Aadhaar number.
     * Aadhaar is a significant unique identifier in India for customer identification.
     *
     * @param aadhaarNumber The Aadhaar number of the customer.
     * @return An {@link Optional} containing the found Customer, or empty if no customer with the given Aadhaar number is found.
     */
    Optional<Customer> findByAadhaarNumber(String aadhaarNumber);

    /**
     * Finds a list of customers by matching any of the provided unique identifiers:
     * PAN, mobile number, email ID, or Aadhaar number.
     * This method is critical for the deduplication process, allowing the system to identify
     * all potential existing customer profiles that might correspond to a new or incoming customer record.
     * The service layer will then apply specific deduplication rules based on the returned list.
     *
     * @param pan The PAN to search for. Can be null or empty if not available.
     * @param mobileNumber The mobile number to search for. Can be null or empty if not available.
     * @param emailId The email ID to search for. Can be null or empty if not available.
     * @param aadhaarNumber The Aadhaar number to search for. Can be null or empty if not available.
     * @return A {@link List} of {@link Customer} entities that match any of the provided criteria.
     *         Returns an empty list if no matches are found.
     */
    List<Customer> findByPanOrMobileNumberOrEmailIdOrAadhaarNumber(String pan, String mobileNumber, String emailId, String aadhaarNumber);

    /**
     * Finds a customer by a combination of PAN and mobile number.
     * This provides a more specific search for deduplication purposes, often used for
     * higher confidence matches.
     *
     * @param pan The PAN of the customer.
     * @param mobileNumber The mobile number of the customer.
     * @return An {@link Optional} containing the found Customer, or empty if no exact match is found.
     */
    Optional<Customer> findByPanAndMobileNumber(String pan, String mobileNumber);
}
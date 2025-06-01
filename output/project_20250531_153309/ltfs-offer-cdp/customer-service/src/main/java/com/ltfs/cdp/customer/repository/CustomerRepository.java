package com.ltfs.cdp.customer.repository;

import com.ltfs.cdp.customer.entity.Customer;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

/**
 * JPA Repository for the Customer entity.
 * This interface extends JpaRepository, providing standard CRUD operations
 * and pagination/sorting capabilities for Customer entities.
 *
 * The Customer entity is identified by a Long primary key.
 */
@Repository
public interface CustomerRepository extends JpaRepository<Customer, Long> {

    // Custom query methods can be added here if needed, for example:
    // Optional<Customer> findByCustomerId(String customerId);
    // List<Customer> findByMobileNumber(String mobileNumber);
    // List<Customer> findByPanNumber(String panNumber);
}
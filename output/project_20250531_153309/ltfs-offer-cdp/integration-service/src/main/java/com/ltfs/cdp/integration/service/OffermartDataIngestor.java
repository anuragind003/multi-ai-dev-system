package com.ltfs.cdp.integration.service;

import com.ltfs.cdp.integration.model.OffermartCustomerDTO;
import com.ltfs.cdp.integration.model.OffermartOfferDTO;
import com.ltfs.cdp.integration.entity.CustomerEntity;
import com.ltfs.cdp.integration.entity.OfferEntity;
import com.ltfs.cdp.integration.repository.CustomerRepository;
import com.ltfs.cdp.integration.repository.OfferRepository;
import com.ltfs.cdp.integration.util.OffermartDataMapper;
import com.ltfs.cdp.integration.validation.OffermartDataValidator;
import com.ltfs.cdp.integration.deduplication.DeduplicationService;
import com.ltfs.cdp.integration.exception.DataValidationException;
import com.ltfs.cdp.integration.model.IngestionResult;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.ArrayList;
import java.util.List;
import java.util.Objects;
import java.util.stream.Collectors;

/**
 * Service class responsible for batch ingestion of customer and offer data from Offermart.
 * This class orchestrates validation, deduplication, and persistence of incoming data
 * into the CDP system.
 */
@Service
public class OffermartDataIngestor {

    private static final Logger logger = LoggerFactory.getLogger(OffermartDataIngestor.class);

    private final OffermartDataValidator validator;
    private final DeduplicationService deduplicationService;
    private final OffermartDataMapper mapper;
    private final CustomerRepository customerRepository;
    private final OfferRepository offerRepository;

    /**
     * Constructs an OffermartDataIngestor with necessary dependencies.
     *
     * @param validator Service for performing column-level validation on Offermart data.
     * @param deduplicationService Service for applying deduplication logic.
     * @param mapper Utility for mapping Offermart DTOs to CDP entities.
     * @param customerRepository Repository for persisting Customer entities.
     * @param offerRepository Repository for persisting Offer entities.
     */
    @Autowired
    public OffermartDataIngestor(OffermartDataValidator validator,
                                 DeduplicationService deduplicationService,
                                 OffermartDataMapper mapper,
                                 CustomerRepository customerRepository,
                                 OfferRepository offerRepository) {
        this.validator = validator;
        this.deduplicationService = deduplicationService;
        this.mapper = mapper;
        this.customerRepository = customerRepository;
        this.offerRepository = offerRepository;
    }

    /**
     * Initiates the batch ingestion process for Offermart customer and offer data.
     * This method performs validation, deduplication, and persists valid, unique records.
     *
     * @param customerDataList A list of OffermartCustomerDTOs to be ingested.
     * @param offerDataList A list of OffermartOfferDTOs to be ingested.
     * @return An IngestionResult object summarizing the outcome of the ingestion process.
     */
    @Transactional
    public IngestionResult ingestOffermartData(List<OffermartCustomerDTO> customerDataList,
                                               List<OffermartOfferDTO> offerDataList) {
        logger.info("Starting Offermart data ingestion. Customers: {}, Offers: {}",
                customerDataList.size(), offerDataList.size());

        int totalCustomersProcessed = 0;
        int totalOffersProcessed = 0;
        int customersIngested = 0;
        int offersIngested = 0;
        int customersSkipped = 0;
        int offersSkipped = 0;

        List<CustomerEntity> validCustomerEntities = new ArrayList<>();
        List<OfferEntity> validOfferEntities = new ArrayList<>();

        // --- Step 1: Validate and Map Customer Data ---
        for (OffermartCustomerDTO dto : customerDataList) {
            totalCustomersProcessed++;
            try {
                validator.validateCustomerData(dto); // Perform basic column-level validation
                CustomerEntity customerEntity = mapper.toCustomerEntity(dto);
                validCustomerEntities.add(customerEntity);
            } catch (DataValidationException e) {
                logger.warn("Skipping invalid customer record (ID: {}): {}", dto.getCustomerId(), e.getMessage());
                customersSkipped++;
            } catch (Exception e) {
                logger.error("Error processing customer record (ID: {}): {}", dto.getCustomerId(), e.getMessage(), e);
                customersSkipped++;
            }
        }
        logger.info("Validated {} out of {} customer records. {} skipped.",
                validCustomerEntities.size(), totalCustomersProcessed, customersSkipped);

        // --- Step 2: Validate and Map Offer Data ---
        for (OffermartOfferDTO dto : offerDataList) {
            totalOffersProcessed++;
            try {
                validator.validateOfferData(dto); // Perform basic column-level validation
                OfferEntity offerEntity = mapper.toOfferEntity(dto);
                validOfferEntities.add(offerEntity);
            } catch (DataValidationException e) {
                logger.warn("Skipping invalid offer record (ID: {}): {}", dto.getOfferId(), e.getMessage());
                offersSkipped++;
            } catch (Exception e) {
                logger.error("Error processing offer record (ID: {}): {}", dto.getOfferId(), e.getMessage(), e);
                offersSkipped++;
            }
        }
        logger.info("Validated {} out of {} offer records. {} skipped.",
                validOfferEntities.size(), totalOffersProcessed, offersSkipped);

        // --- Step 3: Apply Deduplication Logic for Customers ---
        // Deduplication against the 'live book' (Customer 360) before offers are finalized.
        // This step assumes deduplicationService returns a list of unique customers to be persisted.
        List<CustomerEntity> dedupedCustomers = deduplicationService.deduplicateCustomers(validCustomerEntities);
        logger.info("After deduplication, {} unique customer records identified for persistence.", dedupedCustomers.size());

        // --- Step 4: Apply Deduplication Logic for Offers ---
        // Top-up loan offers must be deduped only within other Top-up offers, and matches found should be removed.
        // This step assumes deduplicationService returns a list of unique offers to be persisted.
        List<OfferEntity> dedupedOffers = deduplicationService.deduplicateOffers(validOfferEntities);
        logger.info("After deduplication, {} unique offer records identified for persistence.", dedupedOffers.size());

        // --- Step 5: Persist Valid and Deduped Data ---
        try {
            // Save customers
            if (!dedupedCustomers.isEmpty()) {
                customerRepository.saveAll(dedupedCustomers);
                customersIngested = dedupedCustomers.size();
                logger.info("Successfully ingested {} customer records.", customersIngested);
            }

            // Save offers
            if (!dedupedOffers.isEmpty()) {
                offerRepository.saveAll(dedupedOffers);
                offersIngested = dedupedOffers.size();
                logger.info("Successfully ingested {} offer records.", offersIngested);
            }
        } catch (Exception e) {
            logger.error("Error during data persistence: {}", e.getMessage(), e);
            // Re-throw or handle as per transaction management strategy
            throw new RuntimeException("Failed to persist data during ingestion.", e);
        }

        logger.info("Offermart data ingestion completed. Customers: Ingested={}, Skipped={}; Offers: Ingested={}, Skipped={}",
                customersIngested, customersSkipped + (totalCustomersProcessed - validCustomerEntities.size() - customersIngested),
                offersIngested, offersSkipped + (totalOffersProcessed - validOfferEntities.size() - offersIngested));

        return new IngestionResult(customersIngested, offersIngested,
                totalCustomersProcessed - customersIngested, totalOffersProcessed - offersIngested);
    }
}

// --- Placeholder DTOs, Entities, Repositories, and Services for compilation ---
// In a real project, these would be in their respective packages and files.

package com.ltfs.cdp.integration.model;

import java.time.LocalDate;
import java.util.Objects;

// Placeholder for OffermartCustomerDTO
class OffermartCustomerDTO {
    private String customerId;
    private String firstName;
    private String lastName;
    private String pan;
    private String mobileNumber;
    private String email;
    private LocalDate dob;

    // Getters and Setters
    public String getCustomerId() { return customerId; }
    public void setCustomerId(String customerId) { this.customerId = customerId; }
    public String getFirstName() { return firstName; }
    public void setFirstName(String firstName) { this.firstName = firstName; }
    public String getLastName() { return lastName; }
    public void setLastName(String lastName) { this.lastName = lastName; }
    public String getPan() { return pan; }
    public void setPan(String pan) { this.pan = pan; }
    public String getMobileNumber() { return mobileNumber; }
    public void setMobileNumber(String mobileNumber) { this.mobileNumber = mobileNumber; }
    public String getEmail() { return email; }
    public void setEmail(String email) { this.email = email; }
    public LocalDate getDob() { return dob; }
    public void setDob(LocalDate dob) { this.dob = dob; }

    @Override
    public boolean equals(Object o) {
        if (this == o) return true;
        if (o == null || getClass() != o.getClass()) return false;
        OffermartCustomerDTO that = (OffermartCustomerDTO) o;
        return Objects.equals(customerId, that.customerId);
    }

    @Override
    public int hashCode() {
        return Objects.hash(customerId);
    }
}

// Placeholder for OffermartOfferDTO
class OffermartOfferDTO {
    private String offerId;
    private String customerId;
    private String campaignId;
    private String productType;
    private Double offerAmount;
    private LocalDate offerExpiryDate;

    // Getters and Setters
    public String getOfferId() { return offerId; }
    public void setOfferId(String offerId) { this.offerId = offerId; }
    public String getCustomerId() { return customerId; }
    public void setCustomerId(String customerId) { this.customerId = customerId; }
    public String getCampaignId() { return campaignId; }
    public void setCampaignId(String campaignId) { this.campaignId = campaignId; }
    public String getProductType() { return productType; }
    public void setProductType(String productType) { this.productType = productType; }
    public Double getOfferAmount() { return offerAmount; }
    public void setOfferAmount(Double offerAmount) { this.offerAmount = offerAmount; }
    public LocalDate getOfferExpiryDate() { return offerExpiryDate; }
    public void setOfferExpiryDate(LocalDate offerExpiryDate) { this.offerExpiryDate = offerExpiryDate; }

    @Override
    public boolean equals(Object o) {
        if (this == o) return true;
        if (o == null || getClass() != o.getClass()) return false;
        OffermartOfferDTO that = (OffermartOfferDTO) o;
        return Objects.equals(offerId, that.offerId);
    }

    @Override
    public int hashCode() {
        return Objects.hash(offerId);
    }
}

// Placeholder for IngestionResult
class IngestionResult {
    private final int customersIngested;
    private final int offersIngested;
    private final int customersSkipped;
    private final int offersSkipped;

    public IngestionResult(int customersIngested, int offersIngested, int customersSkipped, int offersSkipped) {
        this.customersIngested = customersIngested;
        this.offersIngested = offersIngested;
        this.customersSkipped = customersSkipped;
        this.offersSkipped = offersSkipped;
    }

    public int getCustomersIngested() { return customersIngested; }
    public int getOffersIngested() { return offersIngested; }
    public int getCustomersSkipped() { return customersSkipped; }
    public int getOffersSkipped() { return offersSkipped; }

    @Override
    public String toString() {
        return "IngestionResult{" +
                "customersIngested=" + customersIngested +
                ", offersIngested=" + offersIngested +
                ", customersSkipped=" + customersSkipped +
                ", offersSkipped=" + offersSkipped +
                '}';
    }
}

package com.ltfs.cdp.integration.entity;

import javax.persistence.Entity;
import javax.persistence.Id;
import javax.persistence.Table;
import java.time.LocalDate;
import java.util.Objects;

// Placeholder for CustomerEntity
@Entity
@Table(name = "cdp_customer")
class CustomerEntity {
    @Id
    private String customerId; // Assuming Offermart customerId maps to CDP customerId
    private String firstName;
    private String lastName;
    private String pan;
    private String mobileNumber;
    private String email;
    private LocalDate dob;
    // Add other CDP specific customer attributes

    // Getters and Setters
    public String getCustomerId() { return customerId; }
    public void setCustomerId(String customerId) { this.customerId = customerId; }
    public String getFirstName() { return firstName; }
    public void setFirstName(String firstName) { this.firstName = firstName; }
    public String getLastName() { return lastName; }
    public void setLastName(String lastName) { this.lastName = lastName; }
    public String getPan() { return pan; }
    public void setPan(String pan) { this.pan = pan; }
    public String getMobileNumber() { return mobileNumber; }
    public void setMobileNumber(String mobileNumber) { this.mobileNumber = mobileNumber; }
    public String getEmail() { return email; }
    public void setEmail(String email) { this.email = email; }
    public LocalDate getDob() { return dob; }
    public void setDob(LocalDate dob) { this.dob = dob; }

    @Override
    public boolean equals(Object o) {
        if (this == o) return true;
        if (o == null || getClass() != o.getClass()) return false;
        CustomerEntity that = (CustomerEntity) o;
        return Objects.equals(customerId, that.customerId);
    }

    @Override
    public int hashCode() {
        return Objects.hash(customerId);
    }
}

// Placeholder for OfferEntity
@Entity
@Table(name = "cdp_offer")
class OfferEntity {
    @Id
    private String offerId; // Assuming Offermart offerId maps to CDP offerId
    private String customerId; // Foreign key to CustomerEntity
    private String campaignId;
    private String productType;
    private Double offerAmount;
    private LocalDate offerExpiryDate;
    // Add other CDP specific offer attributes

    // Getters and Setters
    public String getOfferId() { return offerId; }
    public void setOfferId(String offerId) { this.offerId = offerId; }
    public String getCustomerId() { return customerId; }
    public void setCustomerId(String customerId) { this.customerId = customerId; }
    public String getCampaignId() { return campaignId; }
    public void setCampaignId(String campaignId) { this.campaignId = campaignId; }
    public String getProductType() { return productType; }
    public void setProductType(String productType) { this.productType = productType; }
    public Double getOfferAmount() { return offerAmount; }
    public void setOfferAmount(Double offerAmount) { this.offerAmount = offerAmount; }
    public LocalDate getOfferExpiryDate() { return offerExpiryDate; }
    public void setOfferExpiryDate(LocalDate offerExpiryDate) { this.offerExpiryDate = offerExpiryDate; }

    @Override
    public boolean equals(Object o) {
        if (this == o) return true;
        if (o == null || getClass() != o.getClass()) return false;
        OfferEntity that = (OfferEntity) o;
        return Objects.equals(offerId, that.offerId);
    }

    @Override
    public int hashCode() {
        return Objects.hash(offerId);
    }
}

package com.ltfs.cdp.integration.repository;

import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

// Placeholder for CustomerRepository
@Repository
interface CustomerRepository extends JpaRepository<CustomerEntity, String> {
    // Custom query methods can be added here if needed
}

// Placeholder for OfferRepository
@Repository
interface OfferRepository extends JpaRepository<OfferEntity, String> {
    // Custom query methods can be added here if needed
}

package com.ltfs.cdp.integration.util;

import com.ltfs.cdp.integration.model.OffermartCustomerDTO;
import com.ltfs.cdp.integration.model.OffermartOfferDTO;
import com.ltfs.cdp.integration.entity.CustomerEntity;
import com.ltfs.cdp.integration.entity.OfferEntity;
import org.springframework.stereotype.Component;

// Placeholder for OffermartDataMapper
@Component
class OffermartDataMapper {

    public CustomerEntity toCustomerEntity(OffermartCustomerDTO dto) {
        if (dto == null) {
            return null;
        }
        CustomerEntity entity = new CustomerEntity();
        entity.setCustomerId(dto.getCustomerId());
        entity.setFirstName(dto.getFirstName());
        entity.setLastName(dto.getLastName());
        entity.setPan(dto.getPan());
        entity.setMobileNumber(dto.getMobileNumber());
        entity.setEmail(dto.getEmail());
        entity.setDob(dto.getDob());
        // Map other fields as necessary
        return entity;
    }

    public OffermartCustomerDTO toCustomerDTO(CustomerEntity entity) {
        if (entity == null) {
            return null;
        }
        OffermartCustomerDTO dto = new OffermartCustomerDTO();
        dto.setCustomerId(entity.getCustomerId());
        dto.setFirstName(entity.getFirstName());
        dto.setLastName(entity.getLastName());
        dto.setPan(entity.getPan());
        dto.setMobileNumber(entity.getMobileNumber());
        dto.setEmail(entity.getEmail());
        dto.setDob(entity.getDob());
        return dto;
    }

    public OfferEntity toOfferEntity(OffermartOfferDTO dto) {
        if (dto == null) {
            return null;
        }
        OfferEntity entity = new OfferEntity();
        entity.setOfferId(dto.getOfferId());
        entity.setCustomerId(dto.getCustomerId());
        entity.setCampaignId(dto.getCampaignId());
        entity.setProductType(dto.getProductType());
        entity.setOfferAmount(dto.getOfferAmount());
        entity.setOfferExpiryDate(dto.getOfferExpiryDate());
        // Map other fields as necessary
        return entity;
    }

    public OffermartOfferDTO toOfferDTO(OfferEntity entity) {
        if (entity == null) {
            return null;
        }
        OffermartOfferDTO dto = new OffermartOfferDTO();
        dto.setOfferId(entity.getOfferId());
        dto.setCustomerId(entity.getCustomerId());
        dto.setCampaignId(entity.getCampaignId());
        dto.setProductType(entity.getProductType());
        dto.setOfferAmount(entity.getOfferAmount());
        dto.setOfferExpiryDate(entity.getOfferExpiryDate());
        return dto;
    }
}

package com.ltfs.cdp.integration.validation;

import com.ltfs.cdp.integration.model.OffermartCustomerDTO;
import com.ltfs.cdp.integration.model.OffermartOfferDTO;
import com.ltfs.cdp.integration.exception.DataValidationException;
import org.springframework.stereotype.Component;
import org.springframework.util.StringUtils;

// Placeholder for OffermartDataValidator
@Component
class OffermartDataValidator {

    public void validateCustomerData(OffermartCustomerDTO dto) throws DataValidationException {
        if (dto == null) {
            throw new DataValidationException("Customer DTO cannot be null.");
        }
        if (!StringUtils.hasText(dto.getCustomerId())) {
            throw new DataValidationException("Customer ID cannot be empty.");
        }
        if (!StringUtils.hasText(dto.getPan())) {
            throw new DataValidationException("PAN cannot be empty for customer ID: " + dto.getCustomerId());
        }
        if (!StringUtils.hasText(dto.getMobileNumber())) {
            throw new DataValidationException("Mobile Number cannot be empty for customer ID: " + dto.getCustomerId());
        }
        // Add more validation rules as per functional requirements (e.g., format, length)
    }

    public void validateOfferData(OffermartOfferDTO dto) throws DataValidationException {
        if (dto == null) {
            throw new DataValidationException("Offer DTO cannot be null.");
        }
        if (!StringUtils.hasText(dto.getOfferId())) {
            throw new DataValidationException("Offer ID cannot be empty.");
        }
        if (!StringUtils.hasText(dto.getCustomerId())) {
            throw new DataValidationException("Customer ID cannot be empty for offer ID: " + dto.getOfferId());
        }
        if (dto.getOfferAmount() == null || dto.getOfferAmount() <= 0) {
            throw new DataValidationException("Offer amount must be positive for offer ID: " + dto.getOfferId());
        }
        if (dto.getOfferExpiryDate() == null || dto.getOfferExpiryDate().isBefore(java.time.LocalDate.now())) {
            throw new DataValidationException("Offer expiry date is invalid or in the past for offer ID: " + dto.getOfferId());
        }
        // Add more validation rules
    }
}

package com.ltfs.cdp.integration.deduplication;

import com.ltfs.cdp.integration.entity.CustomerEntity;
import com.ltfs.cdp.integration.entity.OfferEntity;
import com.ltfs.cdp.integration.repository.CustomerRepository;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import java.util.List;
import java.util.Set;
import java.util.stream.Collectors;

// Placeholder for DeduplicationService
@Service
class DeduplicationService {

    private static final Logger logger = LoggerFactory.getLogger(DeduplicationService.class);

    private final CustomerRepository customerRepository; // To check against 'live book'

    @Autowired
    public DeduplicationService(CustomerRepository customerRepository) {
        this.customerRepository = customerRepository;
    }

    /**
     * Performs deduplication for customer entities.
     * Deduplication against the 'live book' (Customer 360) is performed here.
     * For simplicity, this example assumes customerId is the primary deduplication key.
     * In a real scenario, complex matching logic (e.g., PAN, mobile, name combinations)
     * would be implemented, potentially involving a dedicated deduplication engine or rules.
     *
     * @param incomingCustomers List of customer entities to deduplicate.
     * @return A list of unique customer entities that should be persisted.
     */
    public List<CustomerEntity> deduplicateCustomers(List<CustomerEntity> incomingCustomers) {
        logger.debug("Starting customer deduplication for {} incoming records.", incomingCustomers.size());

        // Step 1: Remove duplicates within the incoming batch itself (based on customerId)
        List<CustomerEntity> uniqueIncoming = incomingCustomers.stream()
                .collect(Collectors.toMap(CustomerEntity::getCustomerId, c -> c, (existing, replacement) -> existing))
                .values().stream().collect(Collectors.toList());
        logger.debug("Batch internal deduplication reduced customers from {} to {}.", incomingCustomers.size(), uniqueIncoming.size());

        // Step 2: Deduplicate against the 'live book' (Customer 360)
        // Fetch existing customer IDs from the database
        Set<String> existingCustomerIds = customerRepository.findAllById(
                uniqueIncoming.stream().map(CustomerEntity::getCustomerId).collect(Collectors.toList()))
                .stream().map(CustomerEntity::getCustomerId).collect(Collectors.toSet());

        List<CustomerEntity> customersToPersist = uniqueIncoming.stream()
                .filter(customer -> {
                    boolean isNew = !existingCustomerIds.contains(customer.getCustomerId());
                    if (!isNew) {
                        logger.debug("Customer with ID {} already exists in live book, skipping.", customer.getCustomerId());
                    }
                    return isNew;
                })
                .collect(Collectors.toList());

        logger.info("Customer deduplication completed. {} new customers identified for persistence.", customersToPersist.size());
        return customersToPersist;
    }

    /**
     * Performs deduplication for offer entities.
     * Top-up loan offers must be deduped only within other Top-up offers, and matches found should be removed.
     * For simplicity, this example assumes offerId is the primary deduplication key.
     * In a real scenario, specific rules for 'Top-up' offers would be applied.
     *
     * @param incomingOffers List of offer entities to deduplicate.
     * @return A list of unique offer entities that should be persisted.
     */
    public List<OfferEntity> deduplicateOffers(List<OfferEntity> incomingOffers) {
        logger.debug("Starting offer deduplication for {} incoming records.", incomingOffers.size());

        // Example: Separate Top-up offers for specific deduplication logic
        List<OfferEntity> topUpOffers = incomingOffers.stream()
                .filter(offer -> "TOP_UP_LOAN".equalsIgnoreCase(offer.getProductType()))
                .collect(Collectors.toList());

        List<OfferEntity> otherOffers = incomingOffers.stream()
                .filter(offer -> !"TOP_UP_LOAN".equalsIgnoreCase(offer.getProductType()))
                .collect(Collectors.toList());

        // Deduplicate Top-up offers: matches found should be removed (i.e., only unique ones remain)
        // For simplicity, assuming offerId is the unique key for top-up offers within the batch
        List<OfferEntity> dedupedTopUpOffers = topUpOffers.stream()
                .collect(Collectors.toMap(OfferEntity::getOfferId, o -> o, (existing, replacement) -> existing))
                .values().stream().collect(Collectors.toList());
        logger.debug("Top-up offer deduplication reduced from {} to {}.", topUpOffers.size(), dedupedTopUpOffers.size());


        // Deduplicate other offers (standard batch deduplication)
        List<OfferEntity> dedupedOtherOffers = otherOffers.stream()
                .collect(Collectors.toMap(OfferEntity::getOfferId, o -> o, (existing, replacement) -> existing))
                .values().stream().collect(Collectors.toList());
        logger.debug("Other offer deduplication reduced from {} to {}.", otherOffers.size(), dedupedOtherOffers.size());

        // Combine and return
        List<OfferEntity> dedupedOffers = new ArrayList<>();
        dedupedOffers.addAll(dedupedTopUpOffers);
        dedupedOffers.addAll(dedupedOtherOffers);

        logger.info("Offer deduplication completed. {} unique offers identified for persistence.", dedupedOffers.size());
        return dedupedOffers;
    }
}

package com.ltfs.cdp.integration.exception;

// Placeholder for DataValidationException
class DataValidationException extends RuntimeException {
    public DataValidationException(String message) {
        super(message);
    }
}
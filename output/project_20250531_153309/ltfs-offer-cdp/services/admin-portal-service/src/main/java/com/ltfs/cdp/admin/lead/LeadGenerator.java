package com.ltfs.cdp.admin.lead;

import com.ltfs.cdp.admin.customer.CustomerService;
import com.ltfs.cdp.admin.customer.model.Customer;
import com.ltfs.cdp.admin.lead.event.LeadGeneratedEvent;
import com.ltfs.cdp.admin.lead.model.Lead;
import com.ltfs.cdp.admin.lead.model.LeadGenerationRequest;
import com.ltfs.cdp.admin.lead.model.LeadGenerationResponse;
import com.ltfs.cdp.admin.offer.OfferService;
import com.ltfs.cdp.admin.offer.model.Offer;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.context.ApplicationEventPublisher;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;
import java.util.stream.Collectors;

/**
 * Service component responsible for generating leads based on specified criteria
 * provided via the admin portal. This class orchestrates the process of identifying
 * eligible customers, creating lead records, and publishing events for further
 * processing within the CDP system.
 *
 * This service interacts with CustomerService to fetch customer data and
 * OfferService to retrieve offer details. It leverages Spring's ApplicationEventPublisher
 * to emit LeadGeneratedEvent for each successfully created lead, enabling
 * an event-driven architecture for downstream lead processing.
 */
@Service
public class LeadGenerator {

    private static final Logger log = LoggerFactory.getLogger(LeadGenerator.class);

    private final CustomerService customerService;
    private final OfferService offerService;
    private final ApplicationEventPublisher eventPublisher;

    /**
     * Constructs a new LeadGenerator with necessary service dependencies.
     *
     * @param customerService    Service for retrieving customer data.
     * @param offerService       Service for retrieving offer data.
     * @param eventPublisher     Spring's ApplicationEventPublisher for publishing lead generation events.
     */
    public LeadGenerator(CustomerService customerService, OfferService offerService, ApplicationEventPublisher eventPublisher) {
        this.customerService = customerService;
        this.offerService = offerService;
        this.eventPublisher = eventPublisher;
    }

    /**
     * Generates leads based on the provided lead generation request.
     * This method performs the following steps:
     * 1. Validates the input request to ensure all necessary criteria are present.
     * 2. Fetches eligible customers from the CustomerService based on the dynamic criteria.
     * 3. Retrieves the associated offer details from the OfferService, if an offer ID is provided.
     * 4. Iterates through eligible customers, creating a new {@link Lead} entity for each.
     * 5. Publishes a {@link LeadGeneratedEvent} for each created lead. This event can be consumed
     *    by other services or components for further processing (e.g., lead scoring, offer assignment,
     *    CRM integration, or persistence).
     *
     * The method is transactional, ensuring that if direct database operations were added,
     * they would be atomic. For event publishing, it ensures the method completes successfully
     * before events are committed (if using transactional event listeners).
     *
     * @param request The {@link LeadGenerationRequest} containing criteria for lead generation,
     *                including campaign ID, optional offer ID, and customer filtering criteria.
     * @return A {@link LeadGenerationResponse} indicating the outcome, including the count of
     *         successfully generated and event-published leads.
     * @throws IllegalArgumentException if the request is invalid, null, or essential criteria are missing.
     * @throws RuntimeException if an unexpected error occurs during the process, such as a critical
     *                          dependency failure or an invalid offer ID.
     */
    @Transactional
    public LeadGenerationResponse generateLeads(LeadGenerationRequest request) {
        log.info("Initiating lead generation process for request: {}", request);

        // 1. Validate input request
        validateRequest(request);

        // 2. Fetch eligible customers based on criteria
        List<Customer> eligibleCustomers = customerService.findCustomersByCriteria(request.getCriteria());

        if (eligibleCustomers.isEmpty()) {
            log.warn("No eligible customers found for the given criteria: {}. Lead generation aborted.", request.getCriteria());
            return new LeadGenerationResponse(0, "No eligible customers found matching the criteria.");
        }
        log.info("Found {} eligible customers for lead generation.", eligibleCustomers.size());

        // 3. Fetch offer details if an offer ID is provided in the request
        Offer offer = null;
        if (request.getOfferId() != null && !request.getOfferId().trim().isEmpty()) {
            Optional<Offer> optionalOffer = offerService.getOfferById(request.getOfferId());
            if (optionalOffer.isPresent()) {
                offer = optionalOffer.get();
                log.debug("Found offer details for offer ID: {}", request.getOfferId());
            } else {
                // If a specific offer ID is provided but not found, it's a critical error for this request.
                log.error("Specified Offer with ID '{}' not found. Aborting lead generation.", request.getOfferId());
                throw new IllegalArgumentException("Offer with ID " + request.getOfferId() + " not found. Cannot generate leads.");
            }
        } else {
            log.info("No specific offer ID provided in the request. Leads will be generated without a direct offer link.");
        }

        int leadsCount = 0;
        List<String> generatedLeadIds = new ArrayList<>();

        // 4. Create Lead entities and publish events for each eligible customer
        for (Customer customer : eligibleCustomers) {
            try {
                Lead lead = createLeadFromCustomer(customer, request, offer);
                generatedLeadIds.add(lead.getLeadId());
                leadsCount++;

                // 5. Publish LeadGeneratedEvent for asynchronous processing
                // This decouples the lead generation from the actual persistence or further processing of leads.
                eventPublisher.publishEvent(new LeadGeneratedEvent(this, lead));
                log.debug("Published LeadGeneratedEvent for customer ID: {} with Lead ID: {}", customer.getCustomerId(), lead.getLeadId());

            } catch (Exception e) {
                // Log the error but continue processing other customers to maximize lead generation.
                log.error("Failed to generate lead for customer ID: {}. Error: {}", customer.getCustomerId(), e.getMessage(), e);
            }
        }

        log.info("Lead generation process completed. Successfully generated and published events for {} leads.", leadsCount);
        return new LeadGenerationResponse(leadsCount, "Lead generation completed successfully. " + leadsCount + " leads generated.");
    }

    /**
     * Validates the incoming {@link LeadGenerationRequest}.
     * Ensures that the request is not null and contains valid criteria for customer selection.
     *
     * @param request The request to validate.
     * @throws IllegalArgumentException if validation fails.
     */
    private void validateRequest(LeadGenerationRequest request) {
        if (request == null) {
            throw new IllegalArgumentException("Lead generation request cannot be null.");
        }
        if (request.getCriteria() == null || request.getCriteria().isEmpty()) {
            throw new IllegalArgumentException("Lead generation criteria cannot be null or empty. Please specify customer filtering criteria.");
        }
        if (request.getCampaignId() == null || request.getCampaignId().trim().isEmpty()) {
            log.warn("Campaign ID is not provided in the lead generation request. Leads will not be linked to a specific campaign.");
            // Depending on business rules, this could be an IllegalArgumentException
            // throw new IllegalArgumentException("Campaign ID is required for lead generation.");
        }
    }

    /**
     * Creates a {@link Lead} entity from a {@link Customer} and the lead generation request details.
     * Assigns a unique ID, sets timestamps, and links to campaign/offer information.
     *
     * @param customer The customer for whom the lead is being generated.
     * @param request  The original lead generation request, providing campaign and offer type details.
     * @param offer    The specific {@link Offer} object associated with this lead, if found; can be null.
     * @return A newly constructed {@link Lead} instance.
     */
    private Lead createLeadFromCustomer(Customer customer, LeadGenerationRequest request, Offer offer) {
        Lead lead = new Lead();
        lead.setLeadId(UUID.randomUUID().toString()); // Generate a unique ID for the lead
        lead.setCustomerId(customer.getCustomerId());
        lead.setGenerationTimestamp(LocalDateTime.now());
        lead.setStatus("GENERATED"); // Initial status of the lead

        // Link to campaign and offer if available
        lead.setCampaignId(request.getCampaignId());
        if (offer != null) {
            lead.setOfferId(offer.getOfferId());
            lead.setOfferType(offer.getOfferType()); // Assuming Offer has offerType
        } else {
            // If no specific offer was found/provided, use the general offer type from the request
            lead.setOfferType(request.getOfferType());
        }

        // Additional customer details or request parameters can be mapped to the lead entity here
        // For example: lead.setCustomerName(customer.getFullName());
        // lead.setGeneratedBy("AdminPortalUser"); // Or actual user context

        return lead;
    }
}

// --- Placeholder DTOs, Models, and Services for direct runnability ---
// In a real project, these classes would reside in their respective packages and files.

// Placeholder for com.ltfs.cdp.admin.lead.model.LeadGenerationRequest
class LeadGenerationRequest {
    private String campaignId;
    private String offerId; // Specific offer ID
    private String offerType; // General offer type if specific ID not available
    private Map<String, String> criteria; // Key-value pairs for customer filtering (e.g., "age": ">=30", "city": "Mumbai")

    public LeadGenerationRequest() {}

    public LeadGenerationRequest(String campaignId, String offerId, String offerType, Map<String, String> criteria) {
        this.campaignId = campaignId;
        this.offerId = offerId;
        this.offerType = offerType;
        this.criteria = criteria;
    }

    public String getCampaignId() { return campaignId; }
    public void setCampaignId(String campaignId) { this.campaignId = campaignId; }
    public String getOfferId() { return offerId; }
    public void setOfferId(String offerId) { this.offerId = offerId; }
    public String getOfferType() { return offerType; }
    public void setOfferType(String offerType) { this.offerType = offerType; }
    public Map<String, String> getCriteria() { return criteria; }
    public void setCriteria(Map<String, String> criteria) { this.criteria = criteria; }

    @Override
    public String toString() {
        return "LeadGenerationRequest{" +
               "campaignId='" + campaignId + '\'' +
               ", offerId='" + offerId + '\'' +
               ", offerType='" + offerType + '\'' +
               ", criteria=" + criteria +
               '}';
    }
}

// Placeholder for com.ltfs.cdp.admin.lead.model.LeadGenerationResponse
class LeadGenerationResponse {
    private int generatedLeadsCount;
    private String message;
    private boolean success;

    public LeadGenerationResponse(int generatedLeadsCount, String message) {
        this.generatedLeadsCount = generatedLeadsCount;
        this.message = message;
        this.success = generatedLeadsCount > 0;
    }

    public int getGeneratedLeadsCount() { return generatedLeadsCount; }
    public void setGeneratedLeadsCount(int generatedLeadsCount) { this.generatedLeadsCount = generatedLeadsCount; }
    public String getMessage() { return message; }
    public void setMessage(String message) { this.message = message; }
    public boolean isSuccess() { return success; }
    public void setSuccess(boolean success) { this.success = success; }
}

// Placeholder for com.ltfs.cdp.admin.lead.model.Lead
class Lead {
    private String leadId;
    private String customerId;
    private String campaignId;
    private String offerId;
    private String offerType;
    private String status; // e.g., GENERATED, QUALIFIED, DISQUALIFIED
    private LocalDateTime generationTimestamp;

    public Lead() {}

    public String getLeadId() { return leadId; }
    public void setLeadId(String leadId) { this.leadId = leadId; }
    public String getCustomerId() { return customerId; }
    public void setCustomerId(String customerId) { this.customerId = customerId; }
    public String getCampaignId() { return campaignId; }
    public void setCampaignId(String campaignId) { this.campaignId = campaignId; }
    public String getOfferId() { return offerId; }
    public void setOfferId(String offerId) { this.offerId = offerId; }
    public String getOfferType() { return offerType; }
    public void setOfferType(String offerType) { this.offerType = offerType; }
    public String getStatus() { return status; }
    public void setStatus(String status) { this.status = status; }
    public LocalDateTime getGenerationTimestamp() { return generationTimestamp; }
    public void setGenerationTimestamp(LocalDateTime generationTimestamp) { this.generationTimestamp = generationTimestamp; }
}

// Placeholder for com.ltfs.cdp.admin.customer.model.Customer
class Customer {
    private String customerId;
    private String pan;
    private String aadhar;
    private String mobile;
    private String email;
    private int age;
    private double income;
    private String city;

    public Customer() {}

    public Customer(String customerId, String pan, String mobile, int age, double income, String city) {
        this.customerId = customerId;
        this.pan = pan;
        this.mobile = mobile;
        this.age = age;
        this.income = income;
        this.city = city;
    }

    public String getCustomerId() { return customerId; }
    public void setCustomerId(String customerId) { this.customerId = customerId; }
    public String getPan() { return pan; }
    public void setPan(String pan) { this.pan = pan; }
    public String getAadhar() { return aadhar; }
    public void setAadhar(String aadhar) { this.aadhar = aadhar; }
    public String getMobile() { return mobile; }
    public void setMobile(String mobile) { this.mobile = mobile; }
    public String getEmail() { return email; }
    public void setEmail(String email) { this.email = email; }
    public int getAge() { return age; }
    public void setAge(int age) { this.age = age; }
    public double getIncome() { return income; }
    public void setIncome(double income) { this.income = income; }
    public String getCity() { return city; }
    public void setCity(String city) { this.city = city; }
}

// Placeholder for com.ltfs.cdp.admin.offer.model.Offer
class Offer {
    private String offerId;
    private String offerName;
    private String offerType; // e.g., "Top-up Loan", "Pre-approved Loan"
    private String campaignId;
    private double interestRate;
    private double maxAmount;
    private LocalDateTime validFrom;
    private LocalDateTime validTo;

    public Offer() {}

    public Offer(String offerId, String offerName, String offerType, String campaignId) {
        this.offerId = offerId;
        this.offerName = offerName;
        this.offerType = offerType;
        this.campaignId = campaignId;
    }

    public String getOfferId() { return offerId; }
    public void setOfferId(String offerId) { this.offerId = offerId; }
    public String getOfferName() { return offerName; }
    public void setOfferName(String offerName) { this.offerName = offerName; }
    public String getOfferType() { return offerType; }
    public void setOfferType(String offerType) { this.offerType = offerType; }
    public String getCampaignId() { return campaignId; }
    public void setCampaignId(String campaignId) { this.campaignId = campaignId; }
    public double getInterestRate() { return interestRate; }
    public void setInterestRate(double interestRate) { this.interestRate = interestRate; }
    public double getMaxAmount() { return maxAmount; }
    public void setMaxAmount(double maxAmount) { this.maxAmount = maxAmount; }
    public LocalDateTime getValidFrom() { return validFrom; }
    public void setValidFrom(LocalDateTime validFrom) { this.validFrom = validFrom; }
    public LocalDateTime getValidTo() { return validTo; }
    public void setValidTo(LocalDateTime validTo) { this.validTo = validTo; }
}

// Placeholder for com.ltfs.cdp.admin.customer.CustomerService
// In a real application, this would interact with a database repository or another microservice.
class CustomerService {
    private static final Logger log = LoggerFactory.getLogger(CustomerService.class);

    /**
     * Simulates finding customers based on criteria.
     * This mock implementation returns a hardcoded list of customers and applies
     * basic filtering based on 'city' and 'age' criteria.
     *
     * @param criteria A map of criteria (e.g., "city": "Mumbai", "age": ">=30").
     * @return A list of matching customers.
     */
    public List<Customer> findCustomersByCriteria(Map<String, String> criteria) {
        log.debug("Simulating customer search with criteria: {}", criteria);
        List<Customer> allCustomers = new ArrayList<>();
        allCustomers.add(new Customer("CUST001", "ABCDE1234F", "9876543210", 35, 50000.0, "Mumbai"));
        allCustomers.add(new Customer("CUST002", "FGHIJ5678K", "9988776655", 40, 75000.0, "Delhi"));
        allCustomers.add(new Customer("CUST003", "KLMNO9012L", "9123456789", 28, 40000.0, "Mumbai"));
        allCustomers.add(new Customer("CUST004", "PQRST3456M", "9000011111", 50, 100000.0, "Bangalore"));
        allCustomers.add(new Customer("CUST005", "UVWXY7890N", "9222233333", 32, 60000.0, "Mumbai"));

        return allCustomers.stream()
                .filter(customer -> {
                    boolean matches = true;
                    if (criteria.containsKey("city")) {
                        matches = matches && customer.getCity().equalsIgnoreCase(criteria.get("city"));
                    }
                    if (criteria.containsKey("age")) {
                        String ageCriteria = criteria.get("age");
                        try {
                            if (ageCriteria.startsWith(">=")) {
                                int minAge = Integer.parseInt(ageCriteria.substring(2));
                                matches = matches && customer.getAge() >= minAge;
                            } else if (ageCriteria.startsWith("<=")) {
                                int maxAge = Integer.parseInt(ageCriteria.substring(2));
                                matches = matches && customer.getAge() <= maxAge;
                            } else if (ageCriteria.startsWith(">")) {
                                int minAge = Integer.parseInt(ageCriteria.substring(1));
                                matches = matches && customer.getAge() > minAge;
                            } else if (ageCriteria.startsWith("<")) {
                                int maxAge = Integer.parseInt(ageCriteria.substring(1));
                                matches = matches && customer.getAge() < maxAge;
                            } else {
                                int exactAge = Integer.parseInt(ageCriteria);
                                matches = matches && customer.getAge() == exactAge;
                            }
                        } catch (NumberFormatException e) {
                            log.warn("Invalid age criteria format: {}. Skipping age filter for this customer.", ageCriteria);
                            // If criteria is malformed, it might be better to throw an exception or ignore the filter.
                            // For this example, we'll just log and continue without applying this specific filter.
                        }
                    }
                    // Add more criteria filtering logic as needed (e.g., income, PAN, etc.)
                    return matches;
                })
                .collect(Collectors.toList());
    }
}

// Placeholder for com.ltfs.cdp.admin.offer.OfferService
// In a real application, this would interact with a database repository or another microservice.
class OfferService {
    private static final Logger log = LoggerFactory.getLogger(OfferService.class);
    private final List<Offer> offers = new ArrayList<>();

    public OfferService() {
        // Simulate some dummy offers
        offers.add(new Offer("OFFER001", "Pre-approved Personal Loan", "Pre-approved", "CAMP001"));
        offers.add(new Offer("OFFER002", "Top-up Home Loan", "Top-up", "CAMP002"));
        offers.add(new Offer("OFFER003", "Loyalty Personal Loan", "Loyalty", "CAMP001"));
        offers.add(new Offer("OFFER004", "E-aggregator Loan", "E-aggregator", "CAMP003"));
    }

    /**
     * Simulates retrieving an offer by its ID.
     *
     * @param offerId The ID of the offer to retrieve.
     * @return An Optional containing the Offer if found, otherwise empty.
     */
    public Optional<Offer> getOfferById(String offerId) {
        log.debug("Simulating offer search for ID: {}", offerId);
        return offers.stream()
                .filter(offer -> offer.getOfferId().equals(offerId))
                .findFirst();
    }
}

// Placeholder for com.ltfs.cdp.admin.lead.event.LeadGeneratedEvent
// This is a custom Spring ApplicationEvent that carries the generated Lead object.
class LeadGeneratedEvent extends org.springframework.context.ApplicationEvent {
    private final Lead lead;

    /**
     * Create a new ApplicationEvent.
     *
     * @param source the object on which the event initially occurred (never {@code null})
     * @param lead   The lead object that was generated and is the subject of this event.
     */
    public LeadGeneratedEvent(Object source, Lead lead) {
        super(source);
        this.lead = lead;
    }

    public Lead getLead() {
        return lead;
    }
}
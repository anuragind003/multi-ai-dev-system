package com.ltfs.cdp.adminportal.service;

import com.ltfs.cdp.adminportal.dto.LeadGenerationRequestDTO;
import com.ltfs.cdp.adminportal.dto.LeadGenerationResponseDTO;
import com.ltfs.cdp.adminportal.event.LeadGeneratedEvent;
import com.ltfs.cdp.adminportal.exception.LeadGenerationException;
import com.ltfs.cdp.adminportal.model.Campaign;
import com.ltfs.cdp.adminportal.model.Customer;
import com.ltfs.cdp.adminportal.model.Lead;
import com.ltfs.cdp.adminportal.repository.CampaignRepository;
import com.ltfs.cdp.adminportal.repository.CustomerRepository;
import com.ltfs.cdp.adminportal.repository.LeadRepository;
import com.ltfs.cdp.adminportal.service.dedupe.DeduplicationService;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.context.ApplicationEventPublisher;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;
import java.util.List;
import java.util.Objects;
import java.util.Set;
import java.util.stream.Collectors;

/**
 * Service class responsible for generating leads based on administrative inputs and predefined business rules.
 * This class orchestrates the process of identifying eligible customers, applying deduplication logic,
 * persisting new lead records, and publishing events for downstream processing.
 *
 * <p>Assumed dependencies (DTOs, Models, Repositories, Services, Exceptions, Events) are expected
 * to be defined in their respective packages within the `admin-portal-service` module.
 * For example:</p>
 * <ul>
 *     <li>{@code com.ltfs.cdp.adminportal.dto.LeadGenerationRequestDTO}</li>
 *     <li>{@code com.ltfs.cdp.adminportal.dto.LeadGenerationResponseDTO}</li>
 *     <li>{@code com.ltfs.cdp.adminportal.model.Customer}</li>
 *     <li>{@code com.ltfs.cdp.adminportal.model.Lead}</li>
 *     <li>{@code com.ltfs.cdp.adminportal.model.Campaign}</li>
 *     <li>{@code com.ltfs.cdp.adminportal.repository.CustomerRepository} (with a custom method like `findByEligibilityCriteria`)</li>
 *     <li>{@code com.ltfs.cdp.adminportal.repository.LeadRepository}</li>
 *     <li>{@code com.ltfs.cdp.adminportal.repository.CampaignRepository}</li>
 *     <li>{@code com.ltfs.cdp.adminportal.service.dedupe.DeduplicationService}</li>
 *     <li>{@code com.ltfs.cdp.adminportal.exception.LeadGenerationException}</li>
 *     <li>{@code com.ltfs.cdp.adminportal.event.LeadGeneratedEvent}</li>
 * </ul>
 */
@Service
public class LeadGenerator {

    private static final Logger log = LoggerFactory.getLogger(LeadGenerator.class);

    private final CustomerRepository customerRepository;
    private final LeadRepository leadRepository;
    private final CampaignRepository campaignRepository;
    private final DeduplicationService deduplicationService;
    private final ApplicationEventPublisher eventPublisher;

    /**
     * Constructs a new LeadGenerator with necessary dependencies.
     *
     * @param customerRepository   Repository for accessing customer data.
     * @param leadRepository       Repository for persisting lead data.
     * @param campaignRepository   Repository for accessing campaign data.
     * @param deduplicationService Service for applying deduplication rules.
     * @param eventPublisher       Spring's application event publisher for event-driven architecture.
     */
    public LeadGenerator(CustomerRepository customerRepository,
                         LeadRepository leadRepository,
                         CampaignRepository campaignRepository,
                         DeduplicationService deduplicationService,
                         ApplicationEventPublisher eventPublisher) {
        this.customerRepository = customerRepository;
        this.leadRepository = leadRepository;
        this.campaignRepository = campaignRepository;
        this.deduplicationService = deduplicationService;
        this.eventPublisher = eventPublisher;
    }

    /**
     * Generates leads based on the provided admin inputs and business rules.
     * This method performs the following steps:
     * <ol>
     *     <li>Validates the input request and retrieves the associated campaign.</li>
     *     <li>Identifies potential customers based on eligibility criteria specified in the request.</li>
     *     <li>Applies deduplication logic using the {@link DeduplicationService} to filter out
     *         customers who already have existing offers, match the 'live book' (Customer 360),
     *         or fall under specific top-up loan deduplication rules.</li>
     *     <li>Creates and persists new {@link Lead} records for the remaining eligible customers.</li>
     *     <li>Publishes a {@link LeadGeneratedEvent} for each successfully generated lead,
     *         enabling other services to react to new leads (e.g., offer finalization, notifications).</li>
     * </ol>
     *
     * @param request The DTO containing criteria for lead generation, such as campaign ID,
     *                customer segments, offer types, and eligibility rules.
     * @return A {@link LeadGenerationResponseDTO} indicating the outcome, including the count of
     *         successfully generated leads and a status message.
     * @throws LeadGenerationException if a business rule violation or an unexpected error occurs
     *                                 during the lead generation process.
     */
    @Transactional
    public LeadGenerationResponseDTO generateLeads(LeadGenerationRequestDTO request) {
        log.info("Starting lead generation process for request: {}", request);

        // Input validation
        if (request == null || request.getCampaignId() == null) {
            log.error("Lead generation request or campaign ID is null.");
            throw new LeadGenerationException("Lead generation request and campaign ID cannot be null.");
        }

        // Retrieve campaign details to ensure it exists and is active
        Campaign campaign = campaignRepository.findById(request.getCampaignId())
                .orElseThrow(() -> {
                    log.error("Campaign not found with ID: {}", request.getCampaignId());
                    return new LeadGenerationException("Campaign not found with ID: " + request.getCampaignId());
                });

        long leadsGeneratedCount = 0;
        try {
            // 1. Identify potential customers based on request criteria
            // This method (findByEligibilityCriteria) is assumed to exist in CustomerRepository
            // and implement complex querying based on various customer attributes (e.g., segment, credit score, product eligibility).
            // Example signature in CustomerRepository:
            // List<Customer> findByEligibilityCriteria(String customerSegment, Integer minCreditScore, Integer maxCreditScore, String loanProductType);
            List<Customer> potentialCustomers = customerRepository.findByEligibilityCriteria(
                    request.getCustomerSegment(),
                    request.getMinCreditScore(),
                    request.getMaxCreditScore(),
                    request.getLoanProductType()
            );
            log.debug("Found {} potential customers for campaign ID: {}", potentialCustomers.size(), request.getCampaignId());

            if (potentialCustomers.isEmpty()) {
                log.warn("No potential customers found for the given criteria for campaign ID: {}. No leads will be generated.", request.getCampaignId());
                return new LeadGenerationResponseDTO(0, "No potential customers found for the given criteria.");
            }

            // 2. Apply deduplication logic
            // The deduplication service determines which customers should be excluded based on
            // existing offers, 'live book' matches (Customer 360), and specific rules for offer types
            // (e.g., "Top-up loan offers must be deduped only within other Top-up offers").
            Set<String> dedupedCustomerIds = deduplicationService.deduplicateCustomers(
                    potentialCustomers.stream()
                            .map(Customer::getCustomerId)
                            .filter(Objects::nonNull) // Ensure customerId is not null before collecting
                            .collect(Collectors.toSet()),
                    request.getOfferType() // Pass offer type for specific dedupe rules (e.g., Top-up)
            );
            log.debug("Identified {} customers to be excluded due to deduplication for campaign ID: {}.", dedupedCustomerIds.size(), request.getCampaignId());

            // Filter out deduped customers to get the final list of eligible customers
            List<Customer> eligibleCustomers = potentialCustomers.stream()
                    .filter(customer -> customer.getCustomerId() != null && !dedupedCustomerIds.contains(customer.getCustomerId()))
                    .collect(Collectors.toList());

            log.info("After deduplication, {} eligible customers remain for lead generation for campaign ID: {}.", eligibleCustomers.size(), request.getCampaignId());

            if (eligibleCustomers.isEmpty()) {
                log.warn("All potential customers were deduped for campaign ID: {}. No leads will be generated.", request.getCampaignId());
                return new LeadGenerationResponseDTO(0, "All potential customers were deduped.");
            }

            // 3. Generate and persist leads for each eligible customer
            for (Customer customer : eligibleCustomers) {
                try {
                    Lead newLead = createLead(customer, campaign, request);
                    leadRepository.save(newLead);
                    leadsGeneratedCount++;
                    log.debug("Generated and saved lead for customer ID: {} and campaign ID: {}. Lead ID: {}", customer.getCustomerId(), campaign.getId(), newLead.getId());

                    // 4. Publish event for downstream services
                    // This event can trigger further processes like offer finalization, sending notifications, etc.,
                    // adhering to the microservices and event-driven architecture.
                    eventPublisher.publishEvent(new LeadGeneratedEvent(this, newLead.getId(), newLead.getCustomerId(), newLead.getCampaignId(), newLead.getOfferType()));

                } catch (Exception e) {
                    // Log the error for a specific customer but continue processing other customers
                    log.error("Failed to generate or save lead for customer ID: {} in campaign ID: {}. Error: {}",
                            customer.getCustomerId(), campaign.getId(), e.getMessage(), e);
                }
            }

            log.info("Successfully completed lead generation. Total {} leads generated for campaign ID: {}.", leadsGeneratedCount, request.getCampaignId());
            return new LeadGenerationResponseDTO(leadsGeneratedCount, "Lead generation completed successfully.");

        } catch (LeadGenerationException e) {
            // Re-throw specific business exceptions to be handled by a global exception handler or controller advice
            log.error("Business rule violation or configuration error during lead generation for request {}: {}", request, e.getMessage(), e);
            throw e;
        } catch (Exception e) {
            // Catch any unexpected runtime exceptions and wrap them in a custom exception
            log.error("An unexpected error occurred during lead generation for request: {}. Error: {}", request, e.getMessage(), e);
            throw new LeadGenerationException("An unexpected error occurred during lead generation.", e);
        }
    }

    /**
     * Creates a new {@link Lead} entity by mapping data from the {@link Customer}, {@link Campaign},
     * and {@link LeadGenerationRequestDTO}.
     * This method encapsulates the logic for initializing a new lead record with default values
     * and data from the source entities.
     *
     * @param customer The customer for whom the lead is being generated.
     * @param campaign The campaign associated with this lead.
     * @param request  The original lead generation request DTO, containing additional lead attributes.
     * @return A newly constructed {@link Lead} entity, ready for persistence.
     */
    private Lead createLead(Customer customer, Campaign campaign, LeadGenerationRequestDTO request) {
        Lead lead = new Lead();
        lead.setCustomerId(customer.getCustomerId());
        lead.setCampaignId(campaign.getId());
        lead.setOfferType(request.getOfferType());
        lead.setLoanProductType(request.getLoanProductType());
        lead.setGeneratedDate(LocalDateTime.now());
        lead.setStatus("GENERATED"); // Initial status of the lead
        lead.setGeneratedBy("ADMIN_PORTAL_SERVICE"); // Indicates the source of lead generation
        // Additional fields can be set here based on business requirements,
        // e.g., lead.setCustomerName(customer.getFullName());
        // e.g., lead.setCampaignName(campaign.getName());
        return lead;
    }
}
package com.ltfs.cdp.bre.service;

import org.kie.api.KieServices;
import org.kie.api.builder.KieBuilder;
import org.kie.api.builder.KieFileSystem;
import org.kie.api.builder.Message;
import org.kie.api.builder.Results;
import org.kie.api.runtime.KieContainer;
import org.kie.api.runtime.KieSession;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.core.io.Resource;
import org.springframework.core.io.support.PathMatchingResourcePatternResolver;
import org.springframework.stereotype.Service;

import javax.annotation.PostConstruct;
import java.io.IOException;
import java.util.List;
import java.util.stream.Collectors;

/**
 * Service responsible for loading and executing business rules using Drools.
 * It manages the KieContainer and KieSession lifecycle for rule execution.
 * Rules are loaded from DRL files located in the 'src/main/resources/rules/' directory
 * at application startup. This service is central to applying business logic
 * for customer deduplication, offer validation, and other data processing tasks
 * within the LTFS Offer CDP system.
 */
@Service
public class RuleEngineService {

    private static final Logger log = LoggerFactory.getLogger(RuleEngineService.class);

    // Defines the classpath location where DRL rule files are expected.
    // All files ending with .drl within this path and its subdirectories will be loaded.
    private static final String RULES_DRL_PATH = "rules/";

    // The KieContainer holds all the compiled knowledge bases and sessions.
    // It is thread-safe and should be initialized once at application startup.
    private KieContainer kieContainer;

    /**
     * Initializes the Drools KieContainer by loading DRL files from the classpath.
     * This method is annotated with @PostConstruct, ensuring it runs automatically
     * after the RuleEngineService bean has been constructed by Spring.
     * It scans for DRL files, compiles them, and sets up the KieContainer.
     *
     * @throws IOException if there is an error reading DRL files from the classpath.
     * @throws IllegalStateException if the Drools rule compilation fails, indicating
     *                               syntax errors or other issues in the DRL files.
     */
    @PostConstruct
    public void init() throws IOException {
        log.info("Starting Drools KieContainer initialization...");
        KieServices kieServices = KieServices.Factory.get();
        KieFileSystem kieFileSystem = kieServices.newKieFileSystem();

        // Use Spring's PathMatchingResourcePatternResolver to find DRL files
        // across all classpath locations (e.g., within JARs or the file system).
        PathMatchingResourcePatternResolver resolver = new PathMatchingResourcePatternResolver();
        Resource[] drlResources = resolver.getResources("classpath*:" + RULES_DRL_PATH + "**/*.drl");

        if (drlResources.length == 0) {
            log.warn("No DRL files found in the specified path: 'classpath*:{}**/*.drl'. " +
                     "Please ensure your DRL files are placed in 'src/main/resources/rules/' or its subdirectories.", RULES_DRL_PATH);
        } else {
            log.info("Found {} DRL files. Loading them into KieFileSystem...", drlResources.length);
            for (Resource resource : drlResources) {
                // Write each DRL resource into the virtual KieFileSystem.
                // The source path is important for Drools to correctly identify the rules.
                kieFileSystem.write(kieServices.getResources().newInputStreamResource(resource.getInputStream(), "UTF-8")
                                    .setSourcePath(RULES_DRL_PATH + resource.getFilename()));
                log.debug("Loaded DRL file: {}", resource.getFilename());
            }
        }

        // Build the KieModule, which compiles the DRL files.
        KieBuilder kieBuilder = kieServices.newKieBuilder(kieFileSystem);
        kieBuilder.buildAll(); // This performs the actual compilation.

        // Check for compilation errors. If errors exist, log them and throw an exception
        // to prevent the application from starting with faulty rules.
        Results results = kieBuilder.getResults();
        if (results.hasMessages(Message.Level.ERROR)) {
            List<String> errors = results.getMessages(Message.Level.ERROR).stream()
                                    .map(Message::toString)
                                    .collect(Collectors.toList());
            log.error("Errors detected during Drools rule compilation:\n{}", String.join("\n", errors));
            throw new IllegalStateException("Drools rule compilation failed. Please check DRL syntax errors.");
        }

        // Get the KieContainer from the KieRepository.
        // The default release ID is used when no specific GAV (GroupId, ArtifactId, Version) is set.
        this.kieContainer = kieServices.newKieContainer(kieServices.getRepository().getDefaultReleaseId());
        log.info("Drools KieContainer initialized successfully. Ready for rule execution.");
    }

    /**
     * Executes the loaded business rules against a provided list of facts.
     * A new KieSession is created for each execution to ensure thread safety
     * and isolation between rule invocations. This is crucial for concurrent
     * processing of customer and offer data.
     *
     * @param facts The list of objects (facts) to be evaluated by the rules.
     *              These objects can be instances of Customer, Offer, or any other
     *              data entity relevant to the rules. Rules will operate on these
     *              objects, potentially modifying their state (e.g., setting deduplication flags,
     *              validating offer status).
     * @return The same list of facts that was passed in, potentially modified
     *         by the rules. Drools modifies facts in place within the working memory.
     * @throws IllegalStateException if the KieContainer has not been initialized,
     *                               meaning rules cannot be executed. This typically indicates
     *                               a startup failure.
     * @throws RuntimeException if an unexpected error occurs during the rule execution process.
     */
    public List<Object> executeRules(List<Object> facts) {
        if (kieContainer == null) {
            log.error("KieContainer is not initialized. Cannot execute rules.");
            throw new IllegalStateException("KieContainer is not initialized. Rules cannot be executed.");
        }

        KieSession kieSession = null;
        try {
            // Create a new KieSession from the KieContainer.
            // Each KieSession represents a separate working memory for rule execution.
            kieSession = kieContainer.newKieSession();
            log.debug("New KieSession created for rule execution. Session ID: {}", kieSession.getIdentifier());

            // Insert all provided facts into the KieSession's working memory.
            // These facts become available for rules to match against.
            for (Object fact : facts) {
                kieSession.insert(fact);
                log.trace("Inserted fact into KieSession: {}", fact.getClass().getSimpleName());
            }

            // Fire all rules that match the inserted facts.
            // This is where the business logic defined in DRLs is applied.
            int rulesFired = kieSession.fireAllRules();
            log.info("{} rules fired successfully for {} facts.", rulesFired, facts.size());

            // Facts are modified in place by the rules. The original list reference
            // can be returned as it now contains the updated state.
            return facts;

        } catch (Exception e) {
            log.error("An error occurred during Drools rule execution: {}", e.getMessage(), e);
            // Wrap the exception in a RuntimeException to propagate it up the call stack.
            throw new RuntimeException("Failed to execute business rules", e);
        } finally {
            // Always dispose the KieSession to release resources and prevent memory leaks.
            // This is critical for performance and stability in a production environment.
            if (kieSession != null) {
                kieSession.dispose();
                log.debug("KieSession disposed.");
            }
        }
    }

    /**
     * Placeholder for Customer entity/DTO.
     * In a real application, this class would typically reside in a dedicated
     * 'com.ltfs.cdp.bre.model' package or similar, and would be more comprehensive
     * with proper validation, JPA annotations (if persisted), etc.
     * Included here as a static inner class for self-containment and demonstration purposes
     * within this single file, as per instructions.
     */
    public static class Customer {
        private String customerId;
        private String name;
        private String pan;
        private String aadhar;
        private boolean isDeduplicated; // Example field: set by deduplication rules
        private String dedupeReason;    // Example field: reason for deduplication

        public Customer() {}

        public Customer(String customerId, String name, String pan, String aadhar) {
            this.customerId = customerId;
            this.name = name;
            this.pan = pan;
            this.aadhar = aadhar;
            this.isDeduplicated = false; // Default state
        }

        // Getters and Setters
        public String getCustomerId() { return customerId; }
        public void setCustomerId(String customerId) { this.customerId = customerId; }
        public String getName() { return name; }
        public void setName(String name) { this.name = name; }
        public String getPan() { return pan; }
        public void setPan(String pan) { this.pan = pan; }
        public String getAadhar() { return aadhar; }
        public void setAadhar(String aadhar) { this.aadhar = aadhar; }
        public boolean isDeduplicated() { return isDeduplicated; }
        public void setDeduplicated(boolean deduplicated) { isDeduplicated = deduplicated; }
        public String getDedupeReason() { return dedupeReason; }
        public void setDedupeReason(String dedupeReason) { this.dedupeReason = dedupeReason; }

        @Override
        public String toString() {
            // Mask sensitive information for logging purposes
            String maskedPan = (pan != null && pan.length() > 4) ? pan.substring(0, 2) + "****" + pan.substring(pan.length() - 2) : "N/A";
            String maskedAadhar = (aadhar != null && aadhar.length() > 8) ? aadhar.substring(0, 4) + "********" : "N/A";

            return "Customer{" +
                   "customerId='" + customerId + '\'' +
                   ", name='" + name + '\'' +
                   ", pan='" + maskedPan + '\'' +
                   ", aadhar='" + maskedAadhar + '\'' +
                   ", isDeduplicated=" + isDeduplicated +
                   ", dedupeReason='" + dedupeReason + '\'' +
                   '}';
        }
    }

    /**
     * Placeholder for Offer entity/DTO.
     * In a real application, this class would typically reside in a dedicated
     * 'com.ltfs.cdp.bre.model' package or similar, and would be more comprehensive.
     * Included here as a static inner class for self-containment and demonstration purposes
     * within this single file, as per instructions.
     */
    public static class Offer {
        private String offerId;
        private String customerId; // Link to Customer
        private String offerType; // e.g., "Loyalty", "Preapproved", "E-aggregator", "Top-up"
        private double amount;
        private String status; // e.g., "PENDING", "VALID", "INVALID", "REMOVED"
        private String validationReason; // Reason for status change

        public Offer() {}

        public Offer(String offerId, String customerId, String offerType, double amount) {
            this.offerId = offerId;
            this.customerId = customerId;
            this.offerType = offerType;
            this.amount = amount;
            this.status = "PENDING"; // Default status
        }

        // Getters and Setters
        public String getOfferId() { return offerId; }
        public void setOfferId(String offerId) { this.offerId = offerId; }
        public String getCustomerId() { return customerId; }
        public void setCustomerId(String customerId) { this.customerId = customerId; }
        public String getOfferType() { return offerType; }
        public void setOfferType(String offerType) { this.offerType = offerType; }
        public double getAmount() { return amount; }
        public void setAmount(double amount) { this.amount = amount; }
        public String getStatus() { return status; }
        public void setStatus(String status) { this.status = status; }
        public String getValidationReason() { return validationReason; }
        public void setValidationReason(String validationReason) { this.validationReason = validationReason; }

        // Helper methods for common status checks, useful in DRLs
        public boolean isValid() { return "VALID".equals(status); }
        public boolean isRemoved() { return "REMOVED".equals(status); }
        public boolean isTopUp() { return "Top-up".equalsIgnoreCase(offerType); }


        @Override
        public String toString() {
            return "Offer{" +
                   "offerId='" + offerId + '\'' +
                   ", customerId='" + customerId + '\'' +
                   ", offerType='" + offerType + '\'' +
                   ", amount=" + amount +
                   ", status='" + status + '\'' +
                   ", validationReason='" + validationReason + '\'' +
                   '}';
        }
    }
}
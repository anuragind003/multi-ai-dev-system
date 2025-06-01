package com.ltfs.cdp.bre.service;

import lombok.extern.slf4j.Slf4j;
import org.kie.api.runtime.KieContainer;
import org.kie.api.runtime.KieSession;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import java.util.ArrayList;
import java.util.List;
import java.util.Objects;
import java.util.stream.Collectors;

/**
 * Service responsible for interacting with the Drools engine to execute business rules
 * based on input facts. This service orchestrates the rule execution process,
 * inserting facts, firing rules, and collecting results.
 *
 * <p>It leverages Spring's dependency injection for {@link KieContainer}
 * and SLF4J for logging.</p>
 */
@Service
@Slf4j
public class RuleExecutionService {

    private final KieContainer kieContainer;

    /**
     * Constructs a RuleExecutionService with the provided KieContainer.
     * The KieContainer is essential for obtaining KieSessions, which are
     * the runtime environments for executing Drools rules.
     *
     * @param kieContainer The KieContainer instance, typically autowired by Spring,
     *                     containing the compiled Drools knowledge base.
     */
    @Autowired
    public RuleExecutionService(KieContainer kieContainer) {
        this.kieContainer = kieContainer;
    }

    /**
     * Executes business rules against a given list of facts using the default KieSession
     * named "ksession-rules".
     * This method obtains a new KieSession, inserts all provided facts,
     * fires all applicable rules, and then collects any objects that were
     * asserted into the working memory by the rules.
     *
     * <p>It's crucial to dispose of the KieSession after use to release resources.</p>
     *
     * @param facts A {@link List} of objects that represent the facts
     *              against which the business rules will be evaluated.
     *              These could be Customer, Offer, Campaign entities, or DTOs.
     * @return A {@link List} of objects that were asserted into the KieSession
     *         by the executed rules. This can include validation results,
     *         deduplication outcomes, or modified versions of input facts
     *         if rules explicitly assert them. Returns an empty list if no
     *         objects were asserted or if an error occurs.
     * @throws RuntimeException if there is an issue obtaining a KieSession
     *                          or during rule execution.
     */
    public List<Object> executeRules(List<Object> facts) {
        // Default KieSession name, typically defined in src/main/resources/META-INF/kmodule.xml
        return executeRules(facts, "ksession-rules");
    }

    /**
     * Executes business rules against a given list of facts using a specified KieSession name.
     * This method allows for selecting different sets of rules based on the provided
     * KieSession name, which should be configured in `kmodule.xml`.
     *
     * <p>It obtains a new KieSession, inserts all provided facts, fires all applicable rules,
     * and then collects any objects that were asserted into the working memory by the rules.
     * It's crucial to dispose of the KieSession after use to release resources.</p>
     *
     * @param facts          A {@link List} of objects that represent the facts
     *                       against which the business rules will be evaluated.
     *                       These could be Customer, Offer, Campaign entities, or DTOs.
     * @param kieSessionName The name of the KieSession to obtain from the KieContainer.
     *                       This name must correspond to an entry in your `kmodule.xml` file.
     * @return A {@link List} of objects that were asserted into the KieSession
     *         by the executed rules. This can include validation results,
     *         deduplication outcomes, or modified versions of input facts
     *         if rules explicitly assert them. Returns an empty list if no
     *         objects were asserted or if an error occurs.
     * @throws RuntimeException if there is an issue obtaining a KieSession
     *                          or during rule execution.
     */
    public List<Object> executeRules(List<Object> facts, String kieSessionName) {
        KieSession kieSession = null;
        List<Object> assertedResults = new ArrayList<>();

        if (kieSessionName == null || kieSessionName.trim().isEmpty()) {
            log.warn("KieSession name provided is null or empty. Using default KieSession 'ksession-rules'.");
            kieSessionName = "ksession-rules"; // Fallback to default if name is invalid
        }

        try {
            // Obtain a new KieSession from the KieContainer using the specified name.
            kieSession = kieContainer.newKieSession(kieSessionName);
            if (kieSession == null) {
                log.error("Failed to create KieSession with name '{}'. Please ensure this name is correctly configured in kmodule.xml.", kieSessionName);
                throw new RuntimeException("KieSession '" + kieSessionName + "' could not be initialized. Check kmodule.xml configuration.");
            }

            log.info("Starting rule execution for {} facts using KieSession '{}'.", facts != null ? facts.size() : 0, kieSessionName);

            // Insert all facts into the working memory of the KieSession.
            if (facts != null) {
                for (Object fact : facts) {
                    if (fact != null) {
                        kieSession.insert(fact);
                        log.debug("Inserted fact: {}", fact.getClass().getSimpleName());
                    }
                }
            } else {
                log.warn("No facts provided for rule execution in KieSession '{}'.", kieSessionName);
            }

            // Fire all rules that match the inserted facts.
            int rulesFired = kieSession.fireAllRules();
            log.info("Successfully fired {} rules using KieSession '{}'.", rulesFired, kieSessionName);

            // Collect all objects currently in the working memory.
            // This includes original facts (potentially modified) and any new objects
            // asserted by the rules (e.g., validation errors, deduplication flags, result objects).
            assertedResults = kieSession.getObjects().stream()
                    .filter(Objects::nonNull) // Filter out any null objects
                    .collect(Collectors.toList());

            log.info("Collected {} objects from KieSession '{}' after rule execution.", assertedResults.size(), kieSessionName);

        } catch (Exception e) {
            log.error("Error during rule execution with KieSession '{}': {}", kieSessionName, e.getMessage(), e);
            // Re-throw as a runtime exception to be handled by higher layers (e.g., Spring's @ControllerAdvice)
            throw new RuntimeException("Failed to execute business rules with KieSession '" + kieSessionName + "': " + e.getMessage(), e);
        } finally {
            // Always dispose of the KieSession to release resources and prevent memory leaks.
            if (kieSession != null) {
                kieSession.dispose();
                log.debug("KieSession '{}' disposed.", kieSessionName);
            }
        }
        return assertedResults;
    }
}
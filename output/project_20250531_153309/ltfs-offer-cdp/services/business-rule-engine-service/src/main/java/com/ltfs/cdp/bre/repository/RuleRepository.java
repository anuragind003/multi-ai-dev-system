package com.ltfs.cdp.bre.repository;

import com.ltfs.cdp.bre.model.BusinessRule; // Assuming BusinessRule entity exists in com.ltfs.cdp.bre.model package
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.Optional;

/**
 * Repository interface for managing {@link BusinessRule} entities within the LTFS Offer CDP system.
 * This interface extends Spring Data JPA's JpaRepository, providing standard CRUD (Create, Read, Update, Delete)
 * operations and enabling the definition of custom query methods based on entity properties.
 *
 * Business rules are central to the system's functionality, enabling dynamic validation,
 * deduplication logic, and offer finalization. These rules are expected to be stored
 * in the database, potentially as DRL (Drools Rule Language) content or other structured
 * rule definitions.
 *
 * The {@code @Repository} annotation marks this interface as a Spring Data repository,
 * allowing Spring to automatically generate an implementation at runtime.
 */
@Repository
public interface RuleRepository extends JpaRepository<BusinessRule, Long> {

    /**
     * Finds a business rule by its unique name.
     * This method is crucial for retrieving specific rule sets or individual rules
     * that are identified by a human-readable and unique name.
     *
     * @param ruleName The unique name of the business rule to find.
     * @return An {@link Optional} containing the found {@link BusinessRule} if it exists,
     *         or an empty Optional if no rule with the given name is found.
     */
    Optional<BusinessRule> findByRuleName(String ruleName);

    /**
     * Finds all business rules that match a given active status.
     * This is particularly useful for loading only active rules into the rule engine
     * or for managing the lifecycle of rules (e.g., enabling/disabling them).
     * This method assumes the {@link BusinessRule} entity has an 'active' boolean field.
     *
     * @param active A boolean value indicating whether to retrieve active (true) or inactive (false) rules.
     * @return A {@link List} of {@link BusinessRule} entities that match the specified active status.
     */
    List<BusinessRule> findByActive(boolean active);

    /**
     * Finds all business rules belonging to a specific type.
     * Rules can be categorized by type (e.g., "DEDUPLICATION", "VALIDATION", "OFFER_ELIGIBILITY")
     * to facilitate organized retrieval and application within different contexts of the system.
     * This method assumes the {@link BusinessRule} entity has a 'ruleType' String field.
     *
     * @param ruleType The type of the business rules to retrieve.
     * @return A {@link List} of {@link BusinessRule} entities that belong to the specified rule type.
     */
    List<BusinessRule> findByRuleType(String ruleType);

    /**
     * Finds all active business rules of a specific type.
     * This combines the functionality of finding by rule type and by active status,
     * which is a common requirement for efficiently loading relevant and currently
     * applicable rules into the rule engine for processing.
     *
     * @param ruleType The type of the business rules to retrieve.
     * @param active A boolean value indicating whether to retrieve active (true) or inactive (false) rules.
     * @return A {@link List} of active {@link BusinessRule} entities that belong to the specified rule type.
     */
    List<BusinessRule> findByRuleTypeAndActive(String ruleType, boolean active);
}
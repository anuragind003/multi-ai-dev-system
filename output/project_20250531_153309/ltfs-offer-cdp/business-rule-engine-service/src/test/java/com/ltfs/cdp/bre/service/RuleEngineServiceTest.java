package com.ltfs.cdp.bre.service;

import com.ltfs.cdp.bre.exception.RuleEngineException;
import com.ltfs.cdp.bre.model.Fact;
import com.ltfs.cdp.bre.model.Rule;
import com.ltfs.cdp.bre.repository.RuleRepository;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

import java.util.Arrays;
import java.util.Collections;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.*;

/**
 * Unit tests for {@link RuleEngineService}.
 * This class focuses on testing the rule execution and fact evaluation capabilities
 * of the Business Rule Engine service. It uses Mockito to mock dependencies
 * like {@link RuleRepository} to isolate the service logic.
 */
@ExtendWith(MockitoExtension.class)
class RuleEngineServiceTest {

    @Mock
    private RuleRepository ruleRepository; // Mock the repository that provides rules

    @InjectMocks
    private RuleEngineService ruleEngineService; // Inject the service under test

    // Sample rule IDs for clarity in tests
    private static final String DEDUPE_CL_PRODUCT_RULE_ID = "DEDUPE_CL_PRODUCT";
    private static final String VALIDATE_OFFER_DATA_RULE_ID = "VALIDATE_OFFER_DATA";
    private static final String DEDUPE_TOPUP_LOAN_RULE_ID = "DEDUPE_TOPUP_LOAN";
    private static final String FAST_TRACK_ELIGIBILITY_RULE_ID = "FAST_TRACK_ELIGIBILITY";

    /**
     * Sets up the test environment before each test method.
     * Currently, no specific setup is needed as MockitoExtension handles mock initialization.
     */
    @BeforeEach
    void setUp() {
        // No specific setup required for this test class as mocks are handled by @ExtendWith(MockitoExtension.class)
    }

    /**
     * Helper method to create a mock {@link Rule} object.
     * In a real scenario, rules would likely be more complex (e.g., defined in DRL, JSON, or XML).
     * For unit testing, we simplify the representation to focus on conditions and actions.
     *
     * @param ruleId The unique identifier of the rule.
     * @param conditions A map representing the conditions that must be met for the rule to fire.
     *                   Keys are fact attributes, values are expected values (can include operators like ">=X").
     * @param actions A map representing the actions to be performed if the rule fires.
     *                Keys are action names, values are results or commands.
     * @return A configured {@link Rule} object.
     */
    private Rule createMockRule(String ruleId, Map<String, Object> conditions, Map<String, Object> actions) {
        Rule rule = new Rule();
        rule.setRuleId(ruleId);
        rule.setRuleName("Test Rule: " + ruleId);
        rule.setPriority(1); // Default priority for testing
        rule.setConditions(conditions);
        rule.setActions(actions);
        rule.setActive(true); // Rules are active by default for testing
        return rule;
    }

    /**
     * Helper method to create a {@link Fact} object.
     * Facts represent the input data against which rules are evaluated.
     *
     * @param data A map representing the fact data (e.g., customer attributes, offer details).
     * @return A configured {@link Fact} object.
     */
    private Fact createMockFact(Map<String, Object> data) {
        Fact fact = new Fact();
        fact.setFactData(data);
        return fact;
    }

    /**
     * Tests the scenario where a single rule matches the input fact and executes successfully.
     */
    @Test
    void testExecuteRules_singleMatchingRule() {
        // Arrange
        Map<String, Object> customerData = new HashMap<>();
        customerData.put("customerType", "Existing");
        customerData.put("productType", "CL");
        customerData.put("loanAmount", 50000.0);
        Fact inputFact = createMockFact(customerData);

        Map<String, Object> conditions = new HashMap<>();
        conditions.put("productType", "CL");
        conditions.put("customerType", "Existing");
        Map<String, Object> actions = new HashMap<>();
        actions.put("dedupeStatus", "DEDUPED");
        actions.put("dedupeReason", "Existing Customer CL Product");
        Rule dedupeRule = createMockRule(DEDUPE_CL_PRODUCT_RULE_ID, conditions, actions);

        // Mock the repository to return our single matching rule
        when(ruleRepository.findAllActiveRules()).thenReturn(Collections.singletonList(dedupeRule));

        // Act
        List<Map<String, Object>> results = ruleEngineService.executeRules(inputFact);

        // Assert
        assertNotNull(results, "Results list should not be null");
        assertEquals(1, results.size(), "Expected one rule to match and execute");
        Map<String, Object> result = results.get(0);
        assertEquals("DEDUPED", result.get("dedupeStatus"), "Dedupe status should be DEDUPED");
        assertEquals("Existing Customer CL Product", result.get("dedupeReason"), "Dedupe reason should match");
        verify(ruleRepository, times(1)).findAllActiveRules(); // Verify repository interaction
    }

    /**
     * Tests the scenario where no rules match the input fact.
     */
    @Test
    void testExecuteRules_noMatchingRule() {
        // Arrange
        Map<String, Object> customerData = new HashMap<>();
        customerData.put("customerType", "New"); // Does not match "Existing"
        customerData.put("productType", "Mortgage"); // Does not match "CL"
        Fact inputFact = createMockFact(customerData);

        Map<String, Object> conditions = new HashMap<>();
        conditions.put("productType", "CL");
        conditions.put("customerType", "Existing");
        Map<String, Object> actions = new HashMap<>();
        actions.put("dedupeStatus", "DEDUPED");
        Rule dedupeRule = createMockRule(DEDUPE_CL_PRODUCT_RULE_ID, conditions, actions);

        // Mock the repository to return a rule that won't match
        when(ruleRepository.findAllActiveRules()).thenReturn(Collections.singletonList(dedupeRule));

        // Act
        List<Map<String, Object>> results = ruleEngineService.executeRules(inputFact);

        // Assert
        assertNotNull(results, "Results list should not be null");
        assertTrue(results.isEmpty(), "Expected no rules to match and execute");
        verify(ruleRepository, times(1)).findAllActiveRules(); // Verify repository interaction
    }

    /**
     * Tests the scenario where multiple rules match the input fact and all execute.
     */
    @Test
    void testExecuteRules_multipleMatchingRules() {
        // Arrange
        Map<String, Object> offerData = new HashMap<>();
        offerData.put("offerType", "Top-up Loan");
        offerData.put("status", "Pending");
        offerData.put("loanAmount", 75000.0);
        Fact inputFact = createMockFact(offerData);

        // Rule 1: Top-up dedupe specific rule
        Map<String, Object> conditions1 = new HashMap<>();
        conditions1.put("offerType", "Top-up Loan");
        Map<String, Object> actions1 = new HashMap<>();
        actions1.put("dedupeAction", "Apply Top-up Dedupe Logic");
        Rule topupDedupeRule = createMockRule(DEDUPE_TOPUP_LOAN_RULE_ID, conditions1, actions1);

        // Rule 2: General validation for pending offers with high loan amount
        Map<String, Object> conditions2 = new HashMap<>();
        conditions2.put("status", "Pending");
        conditions2.put("loanAmount", ">=50000"); // Example: loanAmount >= 50000
        Map<String, Object> actions2 = new HashMap<>();
        actions2.put("validationStatus", "Requires Manual Review");
        Rule validationRule = createMockRule(VALIDATE_OFFER_DATA_RULE_ID, conditions2, actions2);

        // Mock the repository to return both rules
        when(ruleRepository.findAllActiveRules()).thenReturn(Arrays.asList(topupDedupeRule, validationRule));

        // Act
        List<Map<String, Object>> results = ruleEngineService.executeRules(inputFact);

        // Assert
        assertNotNull(results, "Results list should not be null");
        assertEquals(2, results.size(), "Expected two rules to match and execute");

        // Verify results from Rule 1
        assertTrue(results.stream().anyMatch(r -> "Apply Top-up Dedupe Logic".equals(r.get("dedupeAction"))),
                "Result from Top-up Dedupe Rule missing");
        // Verify results from Rule 2
        assertTrue(results.stream().anyMatch(r -> "Requires Manual Review".equals(r.get("validationStatus"))),
                "Result from Validation Rule missing");

        verify(ruleRepository, times(1)).findAllActiveRules(); // Verify repository interaction
    }

    /**
     * Tests the scenario where the rule repository returns an empty list of rules.
     */
    @Test
    void testExecuteRules_emptyRuleList() {
        // Arrange
        Fact inputFact = createMockFact(Collections.singletonMap("key", "value"));
        when(ruleRepository.findAllActiveRules()).thenReturn(Collections.emptyList());

        // Act
        List<Map<String, Object>> results = ruleEngineService.executeRules(inputFact);

        // Assert
        assertNotNull(results, "Results list should not be null");
        assertTrue(results.isEmpty(), "Expected an empty list when no rules are configured");
        verify(ruleRepository, times(1)).findAllActiveRules(); // Verify repository interaction
    }

    /**
     * Tests the scenario where the input fact's data is null.
     * The service should gracefully handle this and return no results.
     */
    @Test
    void testExecuteRules_nullFactData() {
        // Arrange
        Fact inputFact = new Fact(); // Fact with null data
        inputFact.setFactData(null);

        Map<String, Object> conditions = new HashMap<>();
        conditions.put("productType", "CL");
        Map<String, Object> actions = new HashMap<>();
        actions.put("dedupeStatus", "DEDUPED");
        Rule dedupeRule = createMockRule(DEDUPE_CL_PRODUCT_RULE_ID, conditions, actions);

        when(ruleRepository.findAllActiveRules()).thenReturn(Collections.singletonList(dedupeRule));

        // Act
        List<Map<String, Object>> results = ruleEngineService.executeRules(inputFact);

        // Assert
        assertNotNull(results, "Results list should not be null");
        assertTrue(results.isEmpty(), "Expected no rules to match if fact data is null");
        verify(ruleRepository, times(1)).findAllActiveRules(); // Verify repository interaction
    }

    /**
     * Tests a rule with complex conditions involving numerical comparisons (e.g., greater than or equal).
     */
    @Test
    void testExecuteRules_ruleWithComplexConditions_match() {
        // Arrange
        Map<String, Object> customerData = new HashMap<>();
        customerData.put("customerSegment", "Premium");
        customerData.put("loanProduct", "Personal Loan");
        customerData.put("creditScore", 750); // Matches >=700
        Fact inputFact = createMockFact(customerData);

        Map<String, Object> conditions = new HashMap<>();
        conditions.put("customerSegment", "Premium");
        conditions.put("loanProduct", "Personal Loan");
        conditions.put("creditScore", ">=700"); // Complex condition: greater than or equal
        Map<String, Object> actions = new HashMap<>();
        actions.put("eligibility", "Eligible for Fast Track");
        Rule complexRule = createMockRule(FAST_TRACK_ELIGIBILITY_RULE_ID, conditions, actions);

        when(ruleRepository.findAllActiveRules()).thenReturn(Collections.singletonList(complexRule));

        // Act
        List<Map<String, Object>> results = ruleEngineService.executeRules(inputFact);

        // Assert
        assertNotNull(results, "Results list should not be null");
        assertEquals(1, results.size(), "Expected one rule to match");
        assertEquals("Eligible for Fast Track", results.get(0).get("eligibility"), "Eligibility should be 'Eligible for Fast Track'");
        verify(ruleRepository, times(1)).findAllActiveRules();
    }

    /**
     * Tests a rule with complex conditions where the fact does not meet the criteria.
     */
    @Test
    void testExecuteRules_ruleWithComplexConditions_noMatch() {
        // Arrange
        Map<String, Object> customerData = new HashMap<>();
        customerData.put("customerSegment", "Standard"); // Mismatch
        customerData.put("loanProduct", "Personal Loan");
        customerData.put("creditScore", 650); // Mismatch (not >=700)
        Fact inputFact = createMockFact(customerData);

        Map<String, Object> conditions = new HashMap<>();
        conditions.put("customerSegment", "Premium");
        conditions.put("loanProduct", "Personal Loan");
        conditions.put("creditScore", ">=700");
        Map<String, Object> actions = new HashMap<>();
        actions.put("eligibility", "Eligible for Fast Track");
        Rule complexRule = createMockRule(FAST_TRACK_ELIGIBILITY_RULE_ID, conditions, actions);

        when(ruleRepository.findAllActiveRules()).thenReturn(Collections.singletonList(complexRule));

        // Act
        List<Map<String, Object>> results = ruleEngineService.executeRules(inputFact);

        // Assert
        assertNotNull(results, "Results list should not be null");
        assertTrue(results.isEmpty(), "Expected no rules to match due to condition mismatch");
        verify(ruleRepository, times(1)).findAllActiveRules();
    }

    /**
     * Tests the scenario where a rule's condition refers to a fact attribute that is missing from the input fact.
     * The rule should not fire.
     */
    @Test
    void testExecuteRules_ruleWithMissingFactAttribute() {
        // Arrange
        Map<String, Object> customerData = new HashMap<>();
        customerData.put("customerSegment", "Premium");
        // Missing "loanProduct" which is a condition for the rule
        customerData.put("creditScore", 750);
        Fact inputFact = createMockFact(customerData);

        Map<String, Object> conditions = new HashMap<>();
        conditions.put("customerSegment", "Premium");
        conditions.put("loanProduct", "Personal Loan"); // This condition cannot be evaluated
        conditions.put("creditScore", ">=700");
        Map<String, Object> actions = new HashMap<>();
        actions.put("eligibility", "Eligible for Fast Track");
        Rule complexRule = createMockRule(FAST_TRACK_ELIGIBILITY_RULE_ID, conditions, actions);

        when(ruleRepository.findAllActiveRules()).thenReturn(Collections.singletonList(complexRule));

        // Act
        List<Map<String, Object>> results = ruleEngineService.executeRules(inputFact);

        // Assert
        assertNotNull(results, "Results list should not be null");
        assertTrue(results.isEmpty(), "Expected no rule to match if a required fact attribute is missing");
        verify(ruleRepository, times(1)).findAllActiveRules();
    }

    /**
     * Tests that inactive rules are not executed. The {@code findAllActiveRules()} method
     * of the repository is expected to filter out inactive rules.
     */
    @Test
    void testExecuteRules_ruleWithInactiveStatus() {
        // Arrange
        Map<String, Object> customerData = new HashMap<>();
        customerData.put("productType", "CL");
        Fact inputFact = createMockFact(customerData);

        Map<String, Object> conditions = new HashMap<>();
        conditions.put("productType", "CL");
        Map<String, Object> actions = new HashMap<>();
        actions.put("dedupeStatus", "DEDUPED");
        Rule inactiveRule = createMockRule(DEDUPE_CL_PRODUCT_RULE_ID, conditions, actions);
        inactiveRule.setActive(false); // Explicitly set rule to inactive

        // Mock the repository to return an empty list, simulating that inactive rules are filtered out
        when(ruleRepository.findAllActiveRules()).thenReturn(Collections.emptyList());

        // Act
        List<Map<String, Object>> results = ruleEngineService.executeRules(inputFact);

        // Assert
        assertNotNull(results, "Results list should not be null");
        assertTrue(results.isEmpty(), "Inactive rule should not be executed, thus no results");
        verify(ruleRepository, times(1)).findAllActiveRules();
    }

    /**
     * Tests error handling when the {@link RuleRepository} throws an exception during rule retrieval.
     * The service should wrap this into a {@link RuleEngineException}.
     */
    @Test
    void testExecuteRules_repositoryThrowsException() {
        // Arrange
        Fact inputFact = createMockFact(Collections.singletonMap("key", "value"));
        when(ruleRepository.findAllActiveRules()).thenThrow(new RuntimeException("Database connection failed"));

        // Act & Assert
        RuleEngineException thrown = assertThrows(RuleEngineException.class, () -> {
            ruleEngineService.executeRules(inputFact);
        }, "Expected RuleEngineException to be thrown");

        assertTrue(thrown.getMessage().contains("Failed to retrieve rules"), "Exception message should indicate rule retrieval failure");
        assertTrue(thrown.getCause() instanceof RuntimeException, "Cause should be the original RuntimeException");
        verify(ruleRepository, times(1)).findAllActiveRules(); // Verify repository interaction
    }

    /**
     * Tests the specific functional requirement: "Top-up loan offers must be deduped only within other Top-up offers".
     * This implies that a general deduplication rule should not apply to Top-up loans if a specific Top-up rule exists.
     */
    @Test
    void testExecuteRules_topUpLoanDeduplicationScenario() {
        // Arrange
        Map<String, Object> offerData = new HashMap<>();
        offerData.put("offerType", "Top-up Loan");
        offerData.put("customerSegment", "Existing");
        offerData.put("loanId", "LOAN123"); // Example identifier for deduplication
        Fact inputFact = createMockFact(offerData);

        // Rule for Top-up loan specific deduplication
        Map<String, Object> conditions = new HashMap<>();
        conditions.put("offerType", "Top-up Loan");
        conditions.put("customerSegment", "Existing");
        Map<String, Object> actions = new HashMap<>();
        actions.put("dedupeAction", "Perform Top-up Specific Deduplication");
        actions.put("dedupeScope", "Top-up Offers Only");
        Rule topupDedupeRule = createMockRule(DEDUPE_TOPUP_LOAN_RULE_ID, conditions, actions);

        // Another general dedupe rule that should NOT apply to Top-up loans
        // This rule's conditions are designed not to match the "Top-up Loan" offerType
        Map<String, Object> generalConditions = new HashMap<>();
        generalConditions.put("offerType", "Consumer Loan"); // Mismatch for "Top-up Loan"
        Map<String, Object> generalActions = new HashMap<>();
        generalActions.put("dedupeAction", "Perform General Deduplication");
        Rule generalDedupeRule = createMockRule(DEDUPE_CL_PRODUCT_RULE_ID, generalConditions, generalActions);

        // Mock the repository to return both rules. Only the top-up rule should match.
        when(ruleRepository.findAllActiveRules()).thenReturn(Arrays.asList(topupDedupeRule, generalDedupeRule));

        // Act
        List<Map<String, Object>> results = ruleEngineService.executeRules(inputFact);

        // Assert
        assertNotNull(results, "Results list should not be null");
        assertEquals(1, results.size(), "Only the Top-up specific rule should match and execute");

        Map<String, Object> result = results.get(0);
        assertEquals("Perform Top-up Specific Deduplication", result.get("dedupeAction"), "Top-up specific action should be present");
        assertEquals("Top-up Offers Only", result.get("dedupeScope"), "Dedupe scope should be 'Top-up Offers Only'");
        assertFalse(results.stream().anyMatch(r -> "Perform General Deduplication".equals(r.get("dedupeAction"))),
                "General deduplication action should not be present");

        verify(ruleRepository, times(1)).findAllActiveRules(); // Verify repository interaction
    }
}
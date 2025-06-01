package com.ltfs.cdp.bre.drools;

import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.kie.api.KieServices;
import org.kie.api.runtime.KieContainer;
import org.kie.api.runtime.KieSession;
import org.kie.api.runtime.rule.FactHandle;

import java.util.ArrayList;
import java.util.List;
import java.util.UUID;

import static org.junit.jupiter.api.Assertions.*;

/**
 * Tests specifically for the Drools rule execution and rule logic.
 * This class loads Drools rules from the classpath and executes them against
 * various test scenarios to ensure the business logic is correctly applied.
 */
class DroolsRuleTest {

    private KieSession kieSession;

    /**
     * Represents a Customer entity for testing Drools rules.
     * This class is a simplified model for rule evaluation.
     */
    public static class Customer {
        private String customerId;
        private int age;
        private String status;
        private boolean isEligible; // Used for basic rule testing

        public Customer(String customerId, int age, String status) {
            this.customerId = customerId;
            this.age = age;
            this.status = status;
            this.isEligible = false;
        }

        public String getCustomerId() {
            return customerId;
        }

        public void setCustomerId(String customerId) {
            this.customerId = customerId;
        }

        public int getAge() {
            return age;
        }

        public void setAge(int age) {
            this.age = age;
        }

        public String getStatus() {
            return status;
        }

        public void setStatus(String status) {
            this.status = status;
        }

        public boolean isEligible() {
            return isEligible;
        }

        public void setEligible(boolean eligible) {
            isEligible = eligible;
        }

        @Override
        public String toString() {
            return "Customer{" +
                    "customerId='" + customerId + '\'' +
                    ", age=" + age +
                    ", status='" + status + '\'' +
                    ", isEligible=" + isEligible +
                    '}';
        }
    }

    /**
     * Represents an Offer entity for testing Drools rules.
     * This class includes fields relevant for validation and deduplication.
     */
    public static class Offer {
        private String offerId;
        private String customerId;
        private String productType; // e.g., "Loyalty", "Preapproved", "Top-up"
        private double amount;
        private boolean isValid;
        private boolean isDuplicate;
        private String dedupeReason;

        public Offer(String offerId, String customerId, String productType, double amount) {
            this.offerId = offerId;
            this.customerId = customerId;
            this.productType = productType;
            this.amount = amount;
            this.isValid = true; // Default to valid
            this.isDuplicate = false; // Default to not duplicate
            this.dedupeReason = null;
        }

        public String getOfferId() {
            return offerId;
        }

        public void setOfferId(String offerId) {
            this.offerId = offerId;
        }

        public String getCustomerId() {
            return customerId;
        }

        public void setCustomerId(String customerId) {
            this.customerId = customerId;
        }

        public String getProductType() {
            return productType;
        }

        public void setProductType(String productType) {
            this.productType = productType;
        }

        public double getAmount() {
            return amount;
        }

        public void setAmount(double amount) {
            this.amount = amount;
        }

        public boolean isValid() {
            return isValid;
        }

        public void setValid(boolean valid) {
            isValid = valid;
        }

        public boolean isDuplicate() {
            return isDuplicate;
        }

        public void setDuplicate(boolean duplicate) {
            isDuplicate = duplicate;
        }

        public String getDedupeReason() {
            return dedupeReason;
        }

        public void setDedupeReason(String dedupeReason) {
            this.dedupeReason = dedupeReason;
        }

        @Override
        public String toString() {
            return "Offer{" +
                    "offerId='" + offerId + '\'' +
                    ", customerId='" + customerId + '\'' +
                    ", productType='" + productType + '\'' +
                    ", amount=" + amount +
                    ", isValid=" + isValid +
                    ", isDuplicate=" + isDuplicate +
                    ", dedupeReason='" + dedupeReason + '\'' +
                    '}';
        }
    }

    /**
     * Sets up the KieSession before each test.
     * It initializes KieServices and retrieves the KieContainer and KieSession
     * based on the kmodule.xml configuration.
     * Assumes kmodule.xml is located in src/main/resources/META-INF/kmodule.xml
     * and defines a kbase named "cdp-rules" and a ksession named "cdp-session".
     */
    @BeforeEach
    void setUp() {
        KieServices ks = KieServices.Factory.get();
        // Load the KieContainer from the classpath, which includes kmodule.xml
        // and all DRL files specified within it.
        KieContainer kc = ks.getKieClasspathContainer();
        // Get a new KieSession from the KieContainer.
        // The session name "cdp-session" should be defined in kmodule.xml.
        kieSession = kc.newKieSession("cdp-session");
        assertNotNull(kieSession, "KieSession should not be null.");
    }

    /**
     * Disposes of the KieSession after each test to release resources.
     */
    @AfterEach
    void tearDown() {
        if (kieSession != null) {
            kieSession.dispose();
        }
    }

    /**
     * Test case for a basic rule: "Mark Customer as Eligible if Age > 18".
     * This verifies that a simple rule can be loaded and executed,
     * modifying a fact inserted into the session.
     */
    @Test
    @DisplayName("Should mark customer as eligible if age is greater than 18")
    void testCustomerEligibilityRule() {
        Customer customer = new Customer("CUST001", 25, "Active");
        kieSession.insert(customer); // Insert the fact into the working memory
        kieSession.fireAllRules();   // Fire all activated rules

        assertTrue(customer.isEligible(), "Customer should be marked as eligible.");

        Customer youngCustomer = new Customer("CUST002", 16, "Active");
        kieSession.insert(youngCustomer);
        kieSession.fireAllRules();
        assertFalse(youngCustomer.isEligible(), "Young customer should not be marked as eligible.");
    }

    /**
     * Test case for column-level validation rule: "Invalidate Offer if Amount is Zero".
     * This checks if an offer is correctly marked as invalid based on its amount.
     */
    @Test
    @DisplayName("Should invalidate offer if amount is zero or less")
    void testOfferAmountValidationRule() {
        Offer validOffer = new Offer("OFFER001", "CUST001", "Loyalty", 1000.00);
        Offer invalidOfferZero = new Offer("OFFER002", "CUST002", "Preapproved", 0.00);
        Offer invalidOfferNegative = new Offer("OFFER003", "CUST003", "E-aggregator", -500.00);

        kieSession.insert(validOffer);
        kieSession.insert(invalidOfferZero);
        kieSession.insert(invalidOfferNegative);

        kieSession.fireAllRules();

        assertTrue(validOffer.isValid(), "Valid offer should remain valid.");
        assertFalse(invalidOfferZero.isValid(), "Offer with zero amount should be invalid.");
        assertFalse(invalidOfferNegative.isValid(), "Offer with negative amount should be invalid.");
    }

    /**
     * Test case for cross-product deduplication rule:
     * "Mark subsequent offers for the same customer and product type as duplicate."
     * This simulates a scenario where multiple offers for the same customer and product
     * are processed, and only the first one should be considered unique.
     */
    @Test
    @DisplayName("Should deduplicate offers for the same customer and product type")
    void testCrossProductDeduplicationRule() {
        String customerId = "CUST_DEDUP_001";
        String productType = "Loyalty";

        Offer offer1 = new Offer(UUID.randomUUID().toString(), customerId, productType, 5000.00);
        Offer offer2 = new Offer(UUID.randomUUID().toString(), customerId, productType, 5500.00);
        Offer offer3 = new Offer(UUID.randomUUID().toString(), customerId, productType, 6000.00);
        Offer offerDifferentProduct = new Offer(UUID.randomUUID().toString(), customerId, "Preapproved", 4000.00);
        Offer offerDifferentCustomer = new Offer(UUID.randomUUID().toString(), "CUST_DEDUP_002", productType, 5000.00);

        // Insert offers into the session. Order of insertion can matter for some rules,
        // but for simple deduplication, all facts are available before rules fire.
        kieSession.insert(offer1);
        kieSession.insert(offer2);
        kieSession.insert(offer3);
        kieSession.insert(offerDifferentProduct);
        kieSession.insert(offerDifferentCustomer);

        kieSession.fireAllRules();

        // Only one offer for CUST_DEDUP_001 and "Loyalty" should be non-duplicate.
        // The rule should mark subsequent ones as duplicates.
        // The exact one that remains non-duplicate depends on the rule's logic (e.g., first inserted, highest amount).
        // For this test, we assume a rule that marks all but one as duplicate.
        long nonDuplicateLoyaltyOffers = List.of(offer1, offer2, offer3).stream()
                .filter(offer -> !offer.isDuplicate())
                .count();

        assertEquals(1, nonDuplicateLoyaltyOffers, "Only one Loyalty offer for CUST_DEDUP_001 should be non-duplicate.");

        // Verify that the other two Loyalty offers are marked as duplicates
        long duplicateLoyaltyOffers = List.of(offer1, offer2, offer3).stream()
                .filter(Offer::isDuplicate)
                .count();
        assertEquals(2, duplicateLoyaltyOffers, "Two Loyalty offers for CUST_DEDUP_001 should be duplicates.");

        // Verify offers with different product types or customers are not affected by this specific dedupe rule
        assertFalse(offerDifferentProduct.isDuplicate(), "Offer with different product type should not be duplicated by this rule.");
        assertFalse(offerDifferentCustomer.isDuplicate(), "Offer from different customer should not be duplicated by this rule.");

        // Check dedupe reason
        List.of(offer1, offer2, offer3).stream()
                .filter(Offer::isDuplicate)
                .forEach(offer -> assertNotNull(offer.getDedupeReason(), "Duplicate offer should have a dedupe reason."));
    }

    /**
     * Test case for Top-up loan specific deduplication rule:
     * "Top-up loan offers must be deduped only within other Top-up offers."
     * This ensures that a Top-up offer is only marked as duplicate if another
     * Top-up offer for the same customer exists, and not if a different product type exists.
     */
    @Test
    @DisplayName("Should deduplicate Top-up offers only among other Top-up offers for the same customer")
    void testTopUpLoanDeduplicationRule() {
        String customerId = "CUST_TOPUP_001";

        Offer topUpOffer1 = new Offer(UUID.randomUUID().toString(), customerId, "Top-up", 10000.00);
        Offer topUpOffer2 = new Offer(UUID.randomUUID().toString(), customerId, "Top-up", 11000.00);
        Offer topUpOffer3 = new Offer(UUID.randomUUID().toString(), customerId, "Top-up", 12000.00);
        Offer loyaltyOffer = new Offer(UUID.randomUUID().toString(), customerId, "Loyalty", 5000.00); // Different product type
        Offer topUpOfferDifferentCustomer = new Offer(UUID.randomUUID().toString(), "CUST_TOPUP_002", "Top-up", 9000.00);

        kieSession.insert(topUpOffer1);
        kieSession.insert(topUpOffer2);
        kieSession.insert(topUpOffer3);
        kieSession.insert(loyaltyOffer);
        kieSession.insert(topUpOfferDifferentCustomer);

        kieSession.fireAllRules();

        // For CUST_TOPUP_001, only one Top-up offer should be non-duplicate.
        long nonDuplicateTopUpOffers = List.of(topUpOffer1, topUpOffer2, topUpOffer3).stream()
                .filter(offer -> !offer.isDuplicate())
                .count();

        assertEquals(1, nonDuplicateTopUpOffers, "Only one Top-up offer for CUST_TOPUP_001 should be non-duplicate.");

        // Verify that the other two Top-up offers are marked as duplicates
        long duplicateTopUpOffers = List.of(topUpOffer1, topUpOffer2, topUpOffer3).stream()
                .filter(Offer::isDuplicate)
                .count();
        assertEquals(2, duplicateTopUpOffers, "Two Top-up offers for CUST_TOPUP_001 should be duplicates.");

        // Verify that the Loyalty offer for the same customer is NOT marked as duplicate by the Top-up rule
        assertFalse(loyaltyOffer.isDuplicate(), "Loyalty offer for the same customer should not be duplicated by Top-up rule.");

        // Verify Top-up offer for a different customer is not affected
        assertFalse(topUpOfferDifferentCustomer.isDuplicate(), "Top-up offer for different customer should not be duplicated.");

        // Check dedupe reason for Top-up duplicates
        List.of(topUpOffer1, topUpOffer2, topUpOffer3).stream()
                .filter(Offer::isDuplicate)
                .forEach(offer -> assertEquals("Top-up loan offer duplicate", offer.getDedupeReason(), "Top-up duplicate should have specific reason."));
    }

    /**
     * Test case for a complex scenario involving multiple rules:
     * - Validation (e.g., amount)
     * - Cross-product deduplication
     * - Top-up specific deduplication
     * This ensures rules interact correctly and in the expected order (if salience is used).
     */
    @Test
    @DisplayName("Should apply multiple rules correctly: validation and different deduplication types")
    void testMultipleRuleApplication() {
        String customerId1 = "CUST_MULTI_001";
        String customerId2 = "CUST_MULTI_002";

        // Scenario 1: Valid Loyalty offers, one duplicate
        Offer offer1_1 = new Offer(UUID.randomUUID().toString(), customerId1, "Loyalty", 7000.00);
        Offer offer1_2 = new Offer(UUID.randomUUID().toString(), customerId1, "Loyalty", 7500.00); // Duplicate of 1_1
        Offer offer1_3 = new Offer(UUID.randomUUID().toString(), customerId1, "Preapproved", 8000.00); // Different product, should be unique

        // Scenario 2: Top-up offers, one invalid, one duplicate
        Offer offer2_1 = new Offer(UUID.randomUUID().toString(), customerId2, "Top-up", 15000.00);
        Offer offer2_2 = new Offer(UUID.randomUUID().toString(), customerId2, "Top-up", 0.00); // Invalid amount, also potentially duplicate
        Offer offer2_3 = new Offer(UUID.randomUUID().toString(), customerId2, "Top-up", 16000.00); // Duplicate of 2_1 (if 2_2 is invalid)

        // Insert all facts
        kieSession.insert(offer1_1);
        kieSession.insert(offer1_2);
        kieSession.insert(offer1_3);
        kieSession.insert(offer2_1);
        kieSession.insert(offer2_2);
        kieSession.insert(offer2_3);

        kieSession.fireAllRules();

        // Assertions for Scenario 1 (CUST_MULTI_001)
        assertTrue(offer1_1.isValid(), "Offer 1_1 should be valid.");
        assertFalse(offer1_1.isDuplicate(), "Offer 1_1 should not be duplicate.");

        assertTrue(offer1_2.isValid(), "Offer 1_2 should be valid.");
        assertTrue(offer1_2.isDuplicate(), "Offer 1_2 should be duplicate due to cross-product rule.");
        assertNotNull(offer1_2.getDedupeReason(), "Offer 1_2 should have a dedupe reason.");

        assertTrue(offer1_3.isValid(), "Offer 1_3 should be valid.");
        assertFalse(offer1_3.isDuplicate(), "Offer 1_3 should not be duplicate (different product type).");

        // Assertions for Scenario 2 (CUST_MULTI_002)
        assertTrue(offer2_1.isValid(), "Offer 2_1 should be valid.");
        assertFalse(offer2_1.isDuplicate(), "Offer 2_1 should not be duplicate.");

        assertFalse(offer2_2.isValid(), "Offer 2_2 should be invalid due to zero amount.");
        // An invalid offer might still be marked as duplicate if the rule fires before validation,
        // or if the rule doesn't check validity. For robust systems, invalid offers should ideally
        // not participate in deduplication or be removed from consideration.
        // Assuming validation happens first or invalid offers are still considered for dedupe.
        // If the rule is "mark as duplicate if valid and same customer/product", then it wouldn't be.
        // For this test, let's assume it *can* be marked duplicate even if invalid.
        assertTrue(offer2_2.isDuplicate(), "Offer 2_2 should be duplicate (even if invalid) due to Top-up rule.");
        assertNotNull(offer2_2.getDedupeReason(), "Offer 2_2 should have a dedupe reason.");

        assertTrue(offer2_3.isValid(), "Offer 2_3 should be valid.");
        assertTrue(offer2_3.isDuplicate(), "Offer 2_3 should be duplicate due to Top-up rule.");
        assertNotNull(offer2_3.getDedupeReason(), "Offer 2_3 should have a dedupe reason.");

        // Verify total non-duplicates for CUST_MULTI_001
        long nonDuplicatesC1 = List.of(offer1_1, offer1_2, offer1_3).stream()
                .filter(offer -> !offer.isDuplicate())
                .count();
        assertEquals(2, nonDuplicatesC1, "CUST_MULTI_001 should have 2 non-duplicate offers (Loyalty, Preapproved).");

        // Verify total non-duplicates for CUST_MULTI_002
        long nonDuplicatesC2 = List.of(offer2_1, offer2_2, offer2_3).stream()
                .filter(offer -> !offer.isDuplicate())
                .count();
        assertEquals(1, nonDuplicatesC2, "CUST_MULTI_002 should have 1 non-duplicate offer (Top-up).");
    }

    /**
     * Test case to ensure no rules fire when no matching facts are present.
     */
    @Test
    @DisplayName("Should not fire any rules if no matching facts are present")
    void testNoRulesFired() {
        // Insert a fact that doesn't match any known rules
        Object irrelevantFact = new Object();
        kieSession.insert(irrelevantFact);
        int rulesFired = kieSession.fireAllRules();
        assertEquals(0, rulesFired, "No rules should have fired for an irrelevant fact.");
    }

    /**
     * Test case for updating facts in the KieSession.
     * This demonstrates how rules can react to changes in facts.
     */
    @Test
    @DisplayName("Should re-evaluate rules when a fact is updated")
    void testFactUpdate() {
        Customer customer = new Customer("CUST_UPDATE_001", 17, "Active");
        FactHandle handle = kieSession.insert(customer);
        kieSession.fireAllRules();
        assertFalse(customer.isEligible(), "Customer should not be eligible initially.");

        // Update the customer's age and inform the session
        customer.setAge(20);
        kieSession.update(handle, customer); // Update the fact in the working memory
        kieSession.fireAllRules(); // Fire rules again

        assertTrue(customer.isEligible(), "Customer should become eligible after age update.");
    }
}